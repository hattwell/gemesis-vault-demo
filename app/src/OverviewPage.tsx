type DigestMention = {
  msg_id: number;
  date: string;
  sender: string;
};

type DigestResource = {
  key: string;
  name: string;
  group: string;
  kind: string;
  description?: string | null;
  topics: string[];
  mentions: number;
  total_mentions: number;
  latest_mention: DigestMention;
};

export type WeeklyDigest = {
  period: { start: string | null; end: string | null };
  stats: { messages: number; contributors: number; new_resources: number };
  topics: { name: string; mentions: number }[];
  new_resources: DigestResource[];
  active_resources: DigestResource[];
};

type Props = {
  digest: WeeklyDigest | null;
  error: string | null;
  onOpenCatalog: () => void;
  onOpenResource: (key: string) => void;
};

const dateFormatter = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "long",
});

function formatDate(value: string | null) {
  if (!value) return "";
  return dateFormatter.format(new Date(`${value}T12:00:00`));
}

export default function OverviewPage({ digest, error, onOpenCatalog, onOpenResource }: Props) {
  if (error) {
    return (
      <main className="overview-page">
        <div className="overview-empty" role="alert">
          <h1>Обзор временно недоступен</h1>
          <p>{error}</p>
          <button type="button" onClick={onOpenCatalog}>Перейти в каталог</button>
        </div>
      </main>
    );
  }

  if (!digest) {
    return (
      <main className="overview-page" aria-busy="true">
        <div className="overview-loading">Собираю сигналы недели</div>
      </main>
    );
  }

  if (!digest.period.start || !digest.period.end) {
    return (
      <main className="overview-page">
        <div className="overview-empty">
          <h1>За неделю пока нет сообщений</h1>
          <p>В этой демонстрации пока нет сообщений за выбранный период.</p>
          <button type="button" onClick={onOpenCatalog}>Открыть каталог</button>
        </div>
      </main>
    );
  }

  return (
    <main className="overview-page">
      <header className="overview-hero">
        <div>
          <div className="overview-kicker">Обзор за 7 дней</div>
          <h1>Что нового в Gemesis</h1>
        </div>
        <div className="overview-period mono">
          <span>{formatDate(digest.period.start)}</span>
          <span aria-hidden="true">—</span>
          <span>{formatDate(digest.period.end)}</span>
        </div>
      </header>

      <dl className="overview-stats">
        <div>
          <dt>Сообщений</dt>
          <dd>{digest.stats.messages}</dd>
        </div>
        <div>
          <dt title="Написали хотя бы одно сообщение за период обзора">Активных участников</dt>
          <dd>{digest.stats.contributors}</dd>
        </div>
        <div>
          <dt>Новых ресурсов</dt>
          <dd>{digest.stats.new_resources}</dd>
        </div>
      </dl>

      <div className="overview-grid">
        <section className="digest-new" aria-labelledby="digest-new-title">
          <div className="digest-section-head">
            <div>
              <span>Появились впервые</span>
              <h2 id="digest-new-title">Новые находки</h2>
            </div>
            <button type="button" onClick={onOpenCatalog}>Весь каталог</button>
          </div>
          {digest.new_resources.length > 0 ? (
            <ul className="digest-resource-list">
              {digest.new_resources.map((resource) => (
                <li key={resource.key}>
                  <article className="digest-resource-card">
                    <button
                      type="button"
                      className="digest-resource-open"
                      onClick={() => onOpenResource(resource.key)}
                    >
                      <span className="digest-resource-kind">{resource.kind}</span>
                      <h3>{resource.name}</h3>
                      {resource.description ? <p>{resource.description}</p> : null}
                    </button>
                    <footer>
                      <span className="mono">{resource.latest_mention.date}</span>
                      <span>{resource.latest_mention.sender}</span>
                    </footer>
                  </article>
                </li>
              ))}
            </ul>
          ) : (
            <div className="digest-empty-section">Новых ссылок за этот период не появилось.</div>
          )}
        </section>

        <aside className="digest-pulse" aria-labelledby="digest-pulse-title">
          <div className="digest-section-head">
            <div>
              <span>Частота упоминаний</span>
              <h2 id="digest-pulse-title">Обсуждали чаще всего</h2>
            </div>
          </div>
          {digest.active_resources.length > 0 ? (
            <ol className="digest-active-list">
              {digest.active_resources.map((resource, index) => (
                <li key={resource.key}>
                  <span className="digest-rank mono">{String(index + 1).padStart(2, "0")}</span>
                  <button type="button" onClick={() => onOpenResource(resource.key)}>
                    <strong>{resource.name}</strong>
                    <span>{resource.mentions} упоминаний за неделю</span>
                  </button>
                </li>
              ))}
            </ol>
          ) : (
            <div className="digest-empty-section">Повторных упоминаний ресурсов за этот период нет.</div>
          )}

          <div className="digest-topics">
            <h3>Темы недели</h3>
            {digest.topics.length > 0 ? (
              <ul>
                {digest.topics.map((topic) => (
                  <li key={topic.name}>
                    <span>{topic.name}</span>
                    <strong className="mono">{topic.mentions}</strong>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="digest-empty-section">Темы появятся после разметки новых ресурсов.</div>
            )}
          </div>
        </aside>
      </div>
    </main>
  );
}
