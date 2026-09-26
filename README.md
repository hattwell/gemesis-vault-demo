# Gemesis Vault · публичное демо / public demo

**RU.** Изолированное интерактивное демо каталога знаний: 20 вымышленных ресурсов, 100 вымышленных сообщений, полнотекстовый поиск, граф связей, сводка и пять MCP-инструментов только для чтения. Сценарный чат возвращает заранее написанные ответы **без ИИ**; неизвестный вопрос получает явно обозначенный ответ-заготовку. Это **не** рабочая база и не доступ к закрытому проекту. Авторов, сообщений, медиа и секретов реальных людей здесь нет. Админки, записи и ссылок на настоящие сообщения нет. Адреса ресурсов оканчиваются на `.example` и не ведут на реальные сайты.

**EN.** Isolated, interactive knowledge-catalogue demo: 20 fictional resources, 100 fictional messages, full-text search, relationship graph, digest, and five read-only MCP tools. Chat returns **scripted answers, not AI**; unrecognized questions receive a clearly labeled fallback. This is not connected to the private project or real data. There is no admin/write access, real user content, working external resource links, or production infrastructure.

## Попробовать локально / Run locally

```sh
# Python 3.12+, Node 22+, pnpm 11.24.0
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-demo.txt
cd app && pnpm install --frozen-lockfile && pnpm build && cd ..
PORT=8000 .venv/bin/python -m demo.launch
# visit http://127.0.0.1:8000/
```

The launcher creates a fresh, deterministic SQLite database in a temporary directory and opens it read-only during requests. Nothing is imported from the private repository at runtime. Set `PORT` to change the listening port. For the container: `docker build -t gemesis-demo . && docker run --rm -p 8000:10000 -e PORT=10000 gemesis-demo`.

## MCP: only fictional data

Endpoint: `http://127.0.0.1:8000/mcp` locally (the MCP tab shows the live host). The public demo-only bearer is **`demo-readonly`**; it is not an owner token or a secret. Tools: `search_messages`, `search_resources`, `get_resource`, `list_topics`, `top_resources`. HTTP POST to MCP requires `Authorization: Bearer demo-readonly`. There are per-client and global request limits. Please do not submit private questions or credentials to a public service.

## Проверки / Checks

```sh
.venv/bin/python -m unittest discover -s tests -q
.venv/bin/python -m scripts.check_public_artifact
cd app && pnpm exec tsc --noEmit && pnpm build && pnpm exec playwright test
```

The public-artifact scanner rejects unknown files, forbidden production hostnames, private file names and symlinks. The Docker build context is deny-by-default. Render configuration declares exactly one **Free** web service with ephemeral storage; a sleeping instance can take about a minute to wake. There is no persistent database, paid AI provider, production VPS connection or external synchronization. Report security issues privately to the repository owner, not by posting credentials or real data in issues.
