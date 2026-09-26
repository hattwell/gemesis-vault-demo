FROM node:22-bookworm-slim AS frontend
WORKDIR /build/app
RUN corepack enable && corepack prepare pnpm@11.24.0 --activate
COPY app/package.json app/pnpm-lock.yaml app/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY app/index.html app/tsconfig.json app/vite.config.ts ./
COPY app/src/ ./src/
COPY app/public/gemesislogo.jpg ./public/gemesislogo.jpg
RUN pnpm build

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/tmp
WORKDIR /srv/demo
COPY requirements-demo.txt ./
RUN pip install --no-cache-dir -r requirements-demo.txt && \
    useradd --uid 10001 --create-home --shell /usr/sbin/nologin demo
COPY common.py fts_index.py rate_limit.py tools_search.py mcp_server.py ./
COPY demo/ ./demo/
COPY --from=frontend /build/app/dist/ ./app/dist/
USER 10001
EXPOSE 10000
CMD ["python", "-m", "demo.launch"]
