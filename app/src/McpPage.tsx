import { useState } from "react";

const TOOLS = [
  ["search_messages", "Поиск по вымышленным сообщениям и авторам."],
  ["search_resources", "Поиск по демонстрационным ресурсам и темам."],
  ["get_resource", "Карточка вымышленного ресурса и его упоминания."],
  ["list_topics", "Список тем демонстрационного каталога."],
  ["top_resources", "Чаще всего обсуждаемые демо-ресурсы."],
] as const;

export default function McpPage() {
  const [platform, setPlatform] = useState<"unix" | "windows">(
    navigator.userAgent.includes("Windows") ? "windows" : "unix",
  );
  const [copyStatus, setCopyStatus] = useState<Record<string, "copied" | "error">>({});
  const endpoint = `${window.location.origin}/mcp`;
  const codexCommand = platform === "windows"
    ? `$env:GEMESIS_DEMO_ACCESS="demo-readonly"\ncodex mcp add gemesis-demo --url ${endpoint} --bearer-token-env-var GEMESIS_DEMO_ACCESS`
    : `export GEMESIS_DEMO_ACCESS="demo-readonly"\ncodex mcp add gemesis-demo --url ${endpoint} --bearer-token-env-var GEMESIS_DEMO_ACCESS`;
  const setups = [
    {
      id: "claude", name: "Claude Code",
      command: `claude mcp add --transport http gemesis-demo ${endpoint} --header "Authorization: Bearer demo-readonly"`,
    },
    { id: "codex", name: "Codex CLI", command: codexCommand },
    {
      id: "cursor", name: "Cursor",
      command: JSON.stringify({ mcpServers: { "gemesis-demo": {
        url: endpoint, headers: { Authorization: "Bearer demo-readonly" },
      } } }, null, 2),
    },
  ];
  const copyCommand = async (id: string, command: string) => {
    try {
      await navigator.clipboard.writeText(command);
      setCopyStatus((current) => ({ ...current, [id]: "copied" }));
    } catch {
      setCopyStatus((current) => ({ ...current, [id]: "error" }));
    }
  };

  return (
    <main className="mcp-page">
      <section className="mcp-hero" aria-labelledby="mcp-title">
        <h1 id="mcp-title">Попробуйте Gemesis через MCP</h1>
        <p>Это отдельное демо: вымышленные данные, пять инструментов только для чтения. Админки и доступа к настоящему проекту здесь нет.</p>
        <div className="mcp-endpoint">
          <span className="endpoint-node" aria-hidden="true" />
          <div><span>Адрес демонстрационного MCP</span><code>{endpoint}</code></div>
          <strong>DEMO</strong>
        </div>
        <p className="mcp-key-note">Ключ <code>demo-readonly</code> публичный и подходит только для вымышленных данных. Не вводите здесь личные или рабочие ключи.</p>
      </section>

      <section className="mcp-tools" aria-labelledby="mcp-tools-title">
        <div className="mcp-section-head"><h2 id="mcp-tools-title">Что можно проверить</h2><span className="tool-count">05</span></div>
        <ul>{TOOLS.map(([name, description], index) => (
          <li key={name}>
            <span className="tool-index">{String(index + 1).padStart(2, "0")}</span>
            <span className="tool-node" aria-hidden="true" />
            <div><h3><code>{name}</code></h3><p>{description}</p></div>
          </li>
        ))}</ul>
      </section>

      <section className="mcp-setup" aria-labelledby="mcp-setup-title">
        <div className="mcp-section-head"><h2 id="mcp-setup-title">Подключение к демо</h2></div>
        <p className="mcp-demo-note">Выберите свою систему и скопируйте готовую команду. Бесплатный сервер после простоя может просыпаться до минуты.</p>
        <div className="platform-choice" role="group" aria-label="Операционная система">
          <button type="button" aria-pressed={platform === "windows"} onClick={() => setPlatform("windows")}>Windows</button>
          <button type="button" aria-pressed={platform === "unix"} onClick={() => setPlatform("unix")}>macOS / Linux</button>
        </div>
        <div className="mcp-setup-grid">
          {setups.map(({ id, name, command }) => (
            <article key={id} className="mcp-setup-card">
              <header>
                <div><h3>{name}</h3><p>Поиск только по вымышленным сообщениям и ресурсам.</p></div>
                <button type="button" className="copy-command" aria-label={`Копировать команду для ${name}`}
                  onClick={() => void copyCommand(id, command)}>
                  {copyStatus[id] === "copied" ? "Скопировано" : "Копировать"}
                </button>
              </header>
              <pre tabIndex={0} aria-label={`Конфигурация для ${name}`}><code>{command}</code></pre>
              <span className="copy-status" role="status" aria-live="polite">
                {copyStatus[id] === "error" ? "Буфер обмена недоступен — выделите и скопируйте команду вручную." : ""}
              </span>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
