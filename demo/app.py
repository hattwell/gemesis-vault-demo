"""Allowlisted, read-only HTTP interface for the fictional Gemesis demo."""
from __future__ import annotations

from contextlib import asynccontextmanager
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from common import DB_PATH, collect_resources, resource_display_name, row_get
from demo.catalog import build_digest, build_graph, _db
from demo.chat import scripted_answer
from demo.updates import UPDATES
from mcp_server import mcp
from rate_limit import RequestRateLimiter

mcp.settings.streamable_http_path = "/"
mcp_asgi = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.graph = build_graph(DB_PATH)
    if sum(node["id"].startswith("url:") for node in app.state.graph["nodes"]) != 20:
        raise RuntimeError("fictional demo graph is incomplete")
    async with mcp.session_manager.run():
        yield


app = FastAPI(lifespan=lifespan, openapi_url=None, docs_url=None, redoc_url=None)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["testserver", "localhost", "127.0.0.1", os.getenv("RENDER_EXTERNAL_HOSTNAME", "localhost")],
)
app.state.chat_limiter = RequestRateLimiter(limit=12, window_seconds=60)
app.state.chat_global_limiter = RequestRateLimiter(limit=120, window_seconds=60)
app.state.mcp_limiter = RequestRateLimiter(limit=30, window_seconds=60)
app.state.mcp_global_limiter = RequestRateLimiter(limit=300, window_seconds=60)


@app.middleware("http")
async def public_guard(request: Request, call_next):
    path = request.scope["path"]
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        size = request.headers.get("content-length")
        if size is None or not size.isdecimal():
            return JSONResponse({"error": "content length required"}, status_code=411)
        if int(size) > 8_192:
            return JSONResponse({"error": "request too large"}, status_code=413)
    if path.startswith("/mcp"):
        if path not in {"/mcp", "/mcp/"}:
            return JSONResponse({"error": "not found"}, status_code=404)
        if request.headers.get("authorization") != "Bearer demo-readonly":
            return JSONResponse({"error": "demo MCP only"}, status_code=401)
        for limiter, identity in ((app.state.mcp_limiter, request.client.host if request.client else "unknown"),
                                  (app.state.mcp_global_limiter, "all")):
            if retry := limiter.consume(identity):
                return JSONResponse({"error": "rate limited"}, status_code=429,
                                    headers={"Retry-After": str(retry)})
        if path == "/mcp":
            request.scope["path"] = "/mcp/"
    return await call_next(request)


@app.get("/api/catalog")
def api_catalog():
    return app.state.graph


@app.get("/api/digest")
def api_digest():
    return build_digest(DB_PATH)


@app.get("/api/updates")
def api_updates():
    return UPDATES


@app.get("/api/features")
def api_features():
    return {"chat": True, "demo": True, "scripted": True}


@app.get("/api/resource")
def api_resource(key: str = ""):
    if len(key) > 200 or not key.startswith("url:https://"):
        raise HTTPException(404, "demo resource not found")
    con = _db(DB_PATH)
    try:
        resources, _, _ = collect_resources(con)
        resource = resources.get(key)
        if resource is None:
            raise HTTPException(404, "demo resource not found")
        meta = con.execute("SELECT * FROM resources WHERE key=? AND COALESCE(useless,0)=0", (key,)).fetchone()
        if meta is None:
            raise HTTPException(404, "demo resource not found")
        mentions = [dict(item, telegram_url=None, media=[]) for item in resource["mentions"][:30]]
        return {
            "key": key, "folder": resource["folder"], "title": resource_display_name(meta, resource),
            "kind": meta["kind"] or resource["folder"], "url": resource["url"],
            "description": row_get(meta, "description") or row_get(meta, "web_desc"),
            "topics": json.loads(meta["topics"] or "[]"),
            "facets": json.loads(meta["facets"] or "[]"), "mentions": mentions,
        }
    finally:
        con.close()


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=300)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=8)


@app.post("/api/chat")
def api_chat(req: ChatRequest, request: Request):
    if req.messages[-1].role != "user":
        raise HTTPException(422, "a demo question is required")
    for limiter, identity in ((app.state.chat_limiter, request.client.host if request.client else "unknown"),
                              (app.state.chat_global_limiter, "all")):
        if retry := limiter.consume(identity):
            return JSONResponse({"error": "rate limited"}, status_code=429,
                                headers={"Retry-After": str(retry)})
    return scripted_answer(req.messages[-1].content)


DIST = Path(__file__).resolve().parents[1] / "app" / "dist"


@app.get("/")
def landing():
    if not (DIST / "index.html").is_file():
        return HTMLResponse("<h1>Gemesis Vault Demo</h1><p>Frontend build is not installed yet.</p>", status_code=503)
    return FileResponse(DIST / "index.html")


@app.get("/gemesislogo.jpg")
def logo():
    if not (DIST / "gemesislogo.jpg").is_file():
        raise HTTPException(404, "demo asset unavailable")
    return FileResponse(DIST / "gemesislogo.jpg")


if (DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")
app.mount("/mcp", mcp_asgi)
