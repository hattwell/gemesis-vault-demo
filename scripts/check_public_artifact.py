"""Fail closed before publishing: report *paths and rule names*, never contents."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import zlib

SCREENSHOTS = {f"screenshots/{name}.png" for name in ("overview", "catalog", "chat")}
EXACT = {
    ".gitignore", ".dockerignore", "Dockerfile", "README.md", "render.yaml",
    "requirements-demo.txt", ".github/workflows/checks.yml",
    "common.py", "tools_search.py", "mcp_server.py",
    "fts_index.py", "rate_limit.py", "app/index.html", "app/package.json",
    "app/pnpm-lock.yaml", "app/pnpm-workspace.yaml", "app/tsconfig.json",
    "app/vite.config.ts", "app/playwright.config.ts", "app/public/gemesislogo.jpg",
} | SCREENSHOTS
PREFIXES = ("app/src/", "app/tests/", "demo/", "scripts/", "tests/")
SKIP_DIRS = {".git", "node_modules", "dist", "test-results", "playwright-report", ".venv", "__pycache__", ".pytest_cache"}
PRIVATE_DIRS = {"media", "backups", "logs"}
# Split sensitive signatures so this scanner itself can be scanned as text.
FORBIDDEN = {
    "former-production-domain": "gemesisvault" + ".duckdns.org",
    "current-production-domain": "gemesis-vault" + ".duckdns.org",
    "old-production-ip": "62.60." + "148.134",
    "production-ip": "89.208." + "113.89",
    "real-telegram-url": "https://t." + "me/",
    "production-env-value": "MCP_TOKEN" + "=",
    "personal-home-path": "/Users/" + "hattwell/",
    "private-server-path": "/opt/" + "gemesis/",
}


def private_name(path: Path) -> bool:
    name = path.name.lower()
    return (
        name.startswith(".env") or name.endswith((".db", ".session", ".pem", ".key"))
        or ".db-" in name or ".session-" in name
        or any(part in PRIVATE_DIRS for part in path.parts)
    )


def valid_screenshot(data: bytes) -> bool:
    """Allow only well-formed PNG pixels, never EXIF or textual ancillary chunks."""
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return False
    offset, types = 8, []
    while offset + 12 <= len(data):
        size = int.from_bytes(data[offset:offset + 4], "big")
        end = offset + 12 + size
        if end > len(data) or size > 2_000_000:
            return False
        kind = data[offset + 4:offset + 8]
        if kind not in {b"IHDR", b"IDAT", b"IEND"}:
            return False
        if zlib.crc32(data[offset + 4:offset + 8 + size]) & 0xffffffff != int.from_bytes(data[offset + 8 + size:end], "big"):
            return False
        if kind == b"IHDR":
            if types or size != 13:
                return False
            width = int.from_bytes(data[offset + 8:offset + 12], "big")
            height = int.from_bytes(data[offset + 12:offset + 16], "big")
            if not (600 <= width <= 2560 and 400 <= height <= 1600):
                return False
        if kind == b"IDAT" and (not types or types[0] != b"IHDR"):
            return False
        if kind == b"IEND":
            return size == 0 and types[0] == b"IHDR" and b"IDAT" in types and end == len(data)
        types.append(kind)
        offset = end
    return False


def check_repo(root: Path) -> dict[str, list[str]]:
    root = root.resolve()
    problems: dict[str, list[str]] = {}

    def record(relative: Path, rule: str) -> None:
        problems.setdefault(relative.as_posix(), []).append(rule)

    for directory, dirs, files in os.walk(root, followlinks=False):
        current = Path(directory)
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        for name in dirs + files:
            path = current / name
            relative = path.relative_to(root)
            if private_name(relative):
                record(relative, "private-name")
            if path.is_symlink():
                record(relative, "symlink")

    candidates = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
    ).decode("utf-8").split("\0")
    for name in filter(None, candidates):
        relative = Path(name)
        path = root / relative
        if name not in EXACT and not name.startswith(PREFIXES):
            record(relative, "not-allowlisted")
        if private_name(relative):
            record(relative, "private-name")
        if not path.is_file() or path.is_symlink():
            record(relative, "not-regular-file")
            continue
        if path.stat().st_size > 2_000_000:
            record(relative, "oversized-file")
            continue
        if name == "app/public/gemesislogo.jpg":
            continue
        if name in SCREENSHOTS:
            if not valid_screenshot(path.read_bytes()):
                record(relative, "screenshot-format-or-metadata")
            continue
        try:
            content = path.read_text("utf-8")
        except UnicodeError:
            record(relative, "binary-file")
            continue
        for rule, signature in FORBIDDEN.items():
            if signature in content:
                record(relative, rule)
    return problems


if __name__ == "__main__":
    issues = check_repo(Path(__file__).resolve().parents[1])
    for path, rules in sorted(issues.items()):
        print(f"{path}: {', '.join(sorted(set(rules)))}")
    if issues:
        raise SystemExit(1)
    print("Public demo artifact: only reviewed paths and fictional references found.")
