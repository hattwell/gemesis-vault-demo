import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import McpPage from "./McpPage";
import OverviewPage, { type WeeklyDigest } from "./OverviewPage";
import UpdatesPanel, { type UpdateEntry } from "./UpdatesPanel";

const COLORS: Record<string, string> = {
  GitHub: "#3fe081",
  Twitter: "#4da3ff",
  "Видео": "#ff6b5e",
  "Веб": "#aab1c9",
  "Человек": "#ffb84d",
  "Тема": "#b78aff",
};

const FACET_LABELS: Record<string, string> = {
  "claude-code": "Claude Code",
  codex: "Codex",
  cursor: "Cursor",
  gemini: "Gemini",
  openai: "OpenAI",
  anthropic: "Anthropic",
  hermes: "Hermes",
  browser: "Браузер",
  skill: "Скилл",
  prompt: "Промпт",
  mcp: "MCP",
  agent: "AI-агент",
  subagent: "Субагент",
  workflow: "Воркфлоу",
  template: "Шаблон",
  plugin: "Плагин",
  extension: "Расширение",
  repo: "Репозиторий",
  docs: "Документация",
  video: "Видео",
  "call-recording": "Запись созвона",
  "x-thread": "Пост или тред в X",
  article: "Статья",
  course: "Курс",
  guide: "Гайд",
  catalog: "Каталог или подборка",
  marketplace: "Маркетплейс",
  "digital-goods": "Цифровые товары",
  accounts: "Аккаунты",
  subscriptions: "Подписки",
  "llm-access": "Доступ к LLM",
  coupons: "Купоны",
  payments: "Платежи",
  frontend: "Фронтенд",
  backend: "Бэкенд",
  ui: "UI",
  ux: "UX",
  "design-system": "Дизайн-система",
  research: "Исследования",
  automation: "Автоматизация",
  scraping: "Парсинг",
  "browser-automation": "Автоматизация браузера",
  seo: "SEO",
  marketing: "Маркетинг",
  "content-generation": "Генерация контента",
  "crypto-defi": "Crypto и DeFi",
  trading: "Трейдинг",
  infrastructure: "Инфраструктура",
  hosting: "Хостинг",
  database: "Базы данных",
  productivity: "Продуктивность",
  finance: "Финансы",
  presentations: "Презентации",
};

const facetLabel = (facet: string) => FACET_LABELS[facet] ?? facet;

type GNode = {
  id: string; name: string; group: string; val: number;
  url: string | null; description: string | null; topics: string[]; facets?: string[]; useless: boolean; kind?: string;
  cat?: boolean; alt?: string | null;
  x?: number; y?: number;
};
type GLink = { source: any; target: any; kind: string };
type PdfInfo = {
  status: "verified" | "partial" | "encrypted" | "invalid" | "unreachable" | "error";
  size_bytes: number | null;
  page_count: number | null;
  sha256: string | null;
  checked_at: string;
  encrypted: boolean;
  active_content: boolean;
  embedded_files: boolean;
};
type MediaItem = { kind: "photo" | "video" | "file"; path: string; pdf?: PdfInfo };
type Mention = {
  msg_id: number;
  date: string;
  sender: string;
  text: string;
  media?: MediaItem[];
};
type ResourceDetail = { mentions: Mention[]; pdf?: PdfInfo };
type ChatSource = { msg_id: number; date: string; from: string; url: string };
type ChatMsg = {
  role: "user" | "assistant";
  content: string;
  refs?: string[];
  sources?: ChatSource[];
  hasMore?: boolean;
  error?: boolean;
};
type Collection =
  | { type: "all" }
  | { type: "topic"; name: string }
  | { type: "kind"; name: string }
  | { type: "facet"; name: string }
  | { type: "source"; name: string }
  | { type: "person"; name: string };

const PDF_STATUS_LABELS: Record<PdfInfo["status"], string> = {
  verified: "проверен",
  partial: "проверен частично",
  encrypted: "зашифрован",
  invalid: "повреждён",
  unreachable: "недоступен",
  error: "ошибка проверки",
};

const formatBytes = (value: number | null) => {
  if (value === null) return null;
  if (value < 1024) return `${value} Б`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} КБ`;
  return `${(value / (1024 * 1024)).toFixed(1)} МБ`;
};

function PdfFacts({ info, compact = false }: { info: PdfInfo; compact?: boolean }) {
  const [copied, setCopied] = useState(false);
  const copyHash = async () => {
    if (!info.sha256) return;
    try {
      await navigator.clipboard.writeText(info.sha256);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  };
  const checked = new Date(info.checked_at);
  const checkedLabel = Number.isNaN(checked.getTime())
    ? info.checked_at
    : checked.toLocaleDateString("ru-RU");
  return (
    <section className={`pdf-facts${compact ? " compact" : ""}`} aria-label="Проверка PDF">
      <div className="pdf-facts-row">
        <span className={`pdf-state status-${info.status}`}>PDF · {PDF_STATUS_LABELS[info.status]}</span>
        {formatBytes(info.size_bytes) && <span className="pdf-fact">{formatBytes(info.size_bytes)}</span>}
        {info.page_count !== null && <span className="pdf-fact">{info.page_count} стр.</span>}
        <span className="pdf-fact">проверен {checkedLabel}</span>
      </div>
      {(info.encrypted || info.active_content || info.embedded_files) && (
        <div className="pdf-warnings">
          {info.encrypted && <span className="pdf-warning">Зашифрован: содержимое не читалось</span>}
          {info.active_content && <span className="pdf-warning">Есть активные действия</span>}
          {info.embedded_files && <span className="pdf-warning">Есть вложенные файлы</span>}
        </div>
      )}
      {info.sha256 && !compact && (
        <div className="pdf-hash">
          <code title={info.sha256}>{info.sha256}</code>
          <button type="button" className="pdf-copy" onClick={() => void copyHash()}>
            {copied ? "скопировано" : "копировать SHA-256"}
          </button>
        </div>
      )}
    </section>
  );
}

const linkId = (e: any) => (typeof e === "object" ? e.id : e);
const isWordChar = (c: string | undefined) => !!c && /[a-zа-яё0-9_-]/i.test(c);

const boundedChatHistory = (messages: ChatMsg[]) => {
  const result: { role: "user" | "assistant"; content: string }[] = [];
  let remaining = 2400;
  for (const message of messages.slice(-8).reverse()) {
    if (remaining <= 0) break;
    const content = message.content.slice(0, Math.min(300, remaining));
    if (!content) continue;
    result.unshift({ role: message.role, content });
    remaining -= content.length;
  }
  return result;
};

/** Запись истории обновлений: отбрасываем битые элементы ответа /api/updates. */
const isUpdateEntry = (e: unknown): e is UpdateEntry => {
  if (typeof e !== "object" || e === null) return false;
  const u = e as UpdateEntry;
  return typeof u.version === "string" && typeof u.date === "string" && typeof u.title === "string"
    && Array.isArray(u.changes) && u.changes.every((c) => typeof c === "string");
};

/** Ответ ассистента: ссылки, **выделение**, `код` и имена ресурсов из refs — кликабельны. */
function RichText({
  text, refs, nodeById, onSelect,
}: {
  text: string; refs: string[]; nodeById: Map<string, GNode>; onSelect: (n: GNode) => void;
}) {
  const patterns = useMemo(() => {
    const out: { pat: string; node: GNode }[] = [];
    for (const k of refs) {
      const n = nodeById.get(k);
      if (!n) continue;
      for (const nm of [n.name, n.alt ?? ""]) {
        if (!nm) continue;
        out.push({ pat: nm.toLowerCase(), node: n });
        const short = nm.split("/").pop();
        if (short && short.length >= 4 && short !== nm)
          out.push({ pat: short.toLowerCase(), node: n });
      }
    }
    return out.sort((a, b) => b.pat.length - a.pat.length);
  }, [text, refs, nodeById]);

  const exactRef = (s: string) => patterns.find((p) => p.pat === s.trim().toLowerCase());
  const parts: React.ReactNode[] = [];
  let key = 0;

  const renderPlain = (seg: string): React.ReactNode[] => {
    const rendered: React.ReactNode[] = [];
    let rest = seg;
    while (rest) {
      let bestIdx = -1;
      let best: { pat: string; node: GNode } | null = null;
      const lower = rest.toLowerCase();
      for (const p of patterns) {
        const idx = lower.indexOf(p.pat);
        if (idx === -1) continue;
        if (isWordChar(rest[idx - 1]) || isWordChar(rest[idx + p.pat.length])) continue;
        if (bestIdx === -1 || idx < bestIdx) { bestIdx = idx; best = p; }
      }
      if (!best) { rendered.push(rest); break; }
      if (bestIdx > 0) rendered.push(rest.slice(0, bestIdx));
      const shown = rest.slice(bestIdx, bestIdx + best.pat.length);
      const node = best.node;
      rendered.push(
        <button
          key={`p${key++}`}
          className="ref-inline"
          title={shown}
          onClick={() => onSelect(node)}
        >
          {shown}
        </button>
      );
      rest = rest.slice(bestIdx + best.pat.length);
    }
    return rendered;
  };

  const re = /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)|\*\*([^*\n]+)\*\*|__([^_\n]+)__|`([^`\n]+)`|(https?:\/\/[^\s)\]]+)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    if (m.index > last) parts.push(...renderPlain(text.slice(last, m.index)));
    if (m[1]) {
      parts.push(
        <a
          key={`a${key++}`}
          className="md-link"
          href={m[2]}
          target="_blank"
          rel="noreferrer"
        >
          {m[1]}
        </a>
      );
    } else if (m[3] || m[4]) {
      parts.push(<strong key={`b${key++}`}>{renderPlain(m[3] ?? m[4])}</strong>);
    } else if (m[5]) {
      const r = exactRef(m[5]);
      const node = r?.node;
      parts.push(
        node
          ? <button
              key={`c${key++}`}
              className="ref-inline mono-ref"
              title={m[5]}
              onClick={() => onSelect(node)}
            >
              {m[5]}
            </button>
          : <code key={`c${key++}`} className="ic">{m[5]}</code>
      );
    } else if (m[6]) {
      parts.push(<a key={`u${key++}`} className="md-link" href={m[6]} target="_blank" rel="noreferrer">{m[6]}</a>);
    }
    last = re.lastIndex;
  }
  if (last < text.length) parts.push(...renderPlain(text.slice(last)));
  return <>{parts}</>;
}

export default function App() {
  const [data, setData] = useState<{ nodes: GNode[]; links: GLink[] } | null>(null);
  const [collection, setCollection] = useState<Collection>({ type: "all" });
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<GNode | null>(null);
  const [resourceDetail, setResourceDetail] = useState<ResourceDetail | null>(null);
  const [expandedM, setExpandedM] = useState<Set<number>>(new Set());
  const [peopleOpen, setPeopleOpen] = useState(false);
  const [facetsOpen, setFacetsOpen] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [view, setView] = useState<"overview" | "catalog" | "mcp">("overview");
  const [digest, setDigest] = useState<WeeklyDigest | null>(null);
  const [digestError, setDigestError] = useState<string | null>(null);
  const [pendingDigestResource, setPendingDigestResource] = useState<string | null>(null);
  const [updates, setUpdates] = useState<UpdateEntry[] | null>(null);
  const [updatesOpen, setUpdatesOpen] = useState(false);
  const versionBadgeRef = useRef<HTMLButtonElement>(null);

  const [features, setFeatures] = useState({ chat: false });
  const [chatOpen, setChatOpen] = useState(false);
  const [chatLog, setChatLog] = useState<ChatMsg[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);
  const detailHeadingRef = useRef<HTMLHeadingElement>(null);
  const detailRequestRef = useRef(0);

  useEffect(() => {
    fetch("/api/catalog").then((r) => r.json()).then(setData);
  }, []);
  useEffect(() => {
    fetch("/api/features")
      .then((response) => response.ok ? response.json() : Promise.reject())
      .then((value) => setFeatures({ chat: value.chat === true }))
      .catch(() => setFeatures({ chat: false }));
  }, []);
  useEffect(() => {
    fetch("/api/digest")
      .then((response) => {
        if (!response.ok) throw new Error("Не удалось загрузить недельную сводку.");
        return response.json();
      })
      .then(setDigest)
      .catch((error: Error) => setDigestError(error.message));
  }, []);
  useEffect(() => {
    const abort = new AbortController();
    fetch("/api/updates", { signal: abort.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`/api/updates: HTTP ${response.status}`);
        return response.json();
      })
      .then((list: unknown) => {
        if (!Array.isArray(list)) throw new Error("/api/updates: неожиданный формат ответа");
        setUpdates(list.filter(isUpdateEntry));
      })
      .catch((error: Error) => {
        if (error.name === "AbortError") return;
        console.error("Не удалось загрузить историю обновлений", error);
      });
    return () => abort.abort();
  }, []);
  useEffect(() => {
    document.title =
      view === "overview" ? "Обзор | Gemesis Vault"
      : view === "mcp" ? "MCP | Gemesis Vault"
      : "Каталог | Gemesis Vault";
  }, [view]);

  const nodeById = useMemo(() => {
    const m = new Map<string, GNode>();
    data?.nodes.forEach((n) => m.set(n.id, n));
    return m;
  }, [data]);

  const adjacency = useMemo(() => {
    const m = new Map<string, Set<string>>();
    if (!data) return m;
    for (const l of data.links) {
      const a = linkId(l.source), b = linkId(l.target);
      if (!m.has(a)) m.set(a, new Set());
      if (!m.has(b)) m.set(b, new Set());
      m.get(a)!.add(b);
      m.get(b)!.add(a);
    }
    return m;
  }, [data]);

  const resources = useMemo(
    () => (data?.nodes ?? []).filter((n) => !n.cat && !["Человек", "Тема"].includes(n.group)),
    [data]
  );
  const topics = useMemo(
    () => (data?.nodes ?? []).filter((n) => n.group === "Тема").sort((a, b) => b.val - a.val),
    [data]
  );
  const sources = useMemo(
    () => (data?.nodes ?? []).filter((n) => n.cat).sort((a, b) => b.val - a.val),
    [data]
  );
  const kinds = useMemo(() => {
    const counts = new Map<string, number>();
    resources.forEach((resource) => {
      const kind = resource.kind ?? resource.group;
      counts.set(kind, (counts.get(kind) ?? 0) + 1);
    });
    return [...counts].map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count);
  }, [resources]);
  const facets = useMemo(() => {
    const counts = new Map<string, number>();
    resources.forEach((resource) =>
      (resource.facets ?? []).forEach((facet) => counts.set(facet, (counts.get(facet) ?? 0) + 1))
    );
    return [...counts].map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count);
  }, [resources]);
  const people = useMemo(
    () => (data?.nodes ?? []).filter((n) => n.group === "Человек").sort((a, b) => b.val - a.val),
    [data]
  );

  // карточки: коллекция + поисковый фильтр, сортировка по упоминаниям
  const cards = useMemo(() => {
    let list = resources;
    if (collection.type === "topic") list = list.filter((n) => n.topics.includes(collection.name));
    if (collection.type === "kind") list = list.filter((n) => (n.kind ?? n.group) === collection.name);
    if (collection.type === "facet") list = list.filter((n) => (n.facets ?? []).includes(collection.name));
    if (collection.type === "source") list = list.filter((n) => n.group === collection.name);
    if (collection.type === "person") {
      const shared = adjacency.get(`person:${collection.name}`) ?? new Set();
      list = list.filter((n) => shared.has(n.id));
    }
    const q = query.trim().toLowerCase();
    if (q) {
      list = list.filter(
        (n) =>
          n.name.toLowerCase().includes(q) ||
          (n.alt ?? "").toLowerCase().includes(q) ||
          (n.description ?? "").toLowerCase().includes(q) ||
          (n.url ?? "").toLowerCase().includes(q) ||
          (n.kind ?? n.group).toLowerCase().includes(q) ||
          n.topics.some((topic) => topic.toLowerCase().includes(q)) ||
          (n.facets ?? []).some(
            (facet) => facet.includes(q) || facetLabel(facet).toLowerCase().includes(q)
          )
      );
    }
    return [...list].sort((a, b) => b.val - a.val);
  }, [resources, collection, query, adjacency]);

  const sharersOf = useCallback(
    (n: GNode) =>
      [...(adjacency.get(n.id) ?? [])]
        .filter((id) => id.startsWith("person:"))
        .map((id) => id.slice(7)),
    [adjacency]
  );

  const selectNode = useCallback((node: GNode | null) => {
    const requestId = detailRequestRef.current + 1;
    detailRequestRef.current = requestId;
    setSelected(node);
    setResourceDetail(null);
    setExpandedM(new Set());
    if (!node) return;
    if (node.group === "Тема") { setCollection({ type: "topic", name: node.name }); setSelected(null); return; }
    if (node.group === "Человек") { setCollection({ type: "person", name: node.name }); setSelected(null); return; }
    if (node.cat) { setCollection({ type: "source", name: node.group }); setSelected(null); return; }
    fetch(`/api/resource?key=${encodeURIComponent(node.id)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((detail: ResourceDetail | null) => {
        if (detailRequestRef.current !== requestId) return;
        setResourceDetail(detail ?? { mentions: [] });
      });
  }, []);

  const mentions = resourceDetail?.mentions ?? null;

  const openChatResource = useCallback((node: GNode) => {
    setView("catalog");
    selectNode(node);
    setChatOpen(false);
  }, [selectNode]);

  const openDigestResource = useCallback((key: string) => {
    setView("catalog");
    const node = nodeById.get(key);
    if (node) {
      selectNode(node);
      return;
    }
    setPendingDigestResource(key);
  }, [nodeById, selectNode]);

  useEffect(() => {
    if (!data || !pendingDigestResource) return;
    const node = nodeById.get(pendingDigestResource);
    setPendingDigestResource(null);
    if (node) selectNode(node);
  }, [data, nodeById, pendingDigestResource, selectNode]);

  useEffect(() => {
    if (view === "catalog" && selected) detailHeadingRef.current?.focus();
  }, [selected, view]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { setSelected(null); setQuery(""); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const submitChat = async (text: string) => {
    const question = text.trim();
    if (!question || thinking) return;
    const next: ChatMsg[] = [...chatLog, { role: "user", content: question }];
    setChatLog(next);
    setChatInput("");
    setThinking(true);
    try {
      const r = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: boundedChatHistory(next) }),
      });
      const d = await r.json();
      if (!r.ok) {
        setChatLog((l) => [...l, { role: "assistant", content: d.error ?? "Ошибка", error: true }]);
      } else {
        setChatLog((l) => [...l, {
          role: "assistant",
          content: d.reply,
          refs: d.refs,
          sources: Array.isArray(d.sources) ? d.sources : [],
          hasMore: d.has_more === true,
        }]);
      }
    } catch {
      setChatLog((l) => [...l, { role: "assistant", content: "Сервер недоступен", error: true }]);
    } finally {
      setThinking(false);
      setTimeout(() => logRef.current?.scrollTo({ top: 1e9 }), 50);
    }
  };

  const sendChat = (event: React.FormEvent) => {
    event.preventDefault();
    void submitChat(chatInput);
  };

  const closeUpdates = useCallback(() => setUpdatesOpen(false), []);

  const collTitle =
    collection.type === "all" ? "Все ресурсы"
    : collection.type === "facet" ? facetLabel(collection.name)
    : collection.name;

  return (
    <div className="layout">
      <header className="topbar">
        <button
          type="button"
          className="brand"
          aria-label="Вернуться к обзору"
          onClick={() => setView("overview")}
        >
          <img className="logo" src="/gemesislogo.jpg" alt="" />
          gemesis <em>vault</em>
        </button>
        {updates && updates.length > 0 && (
          <button
            type="button"
            className="version-badge"
            ref={versionBadgeRef}
            aria-label="История обновлений"
            aria-haspopup="dialog"
            aria-expanded={updatesOpen}
            onClick={() => setUpdatesOpen(true)}
          >
            <span className="version-badge-num">версия {updates[0].version}</span>
          </button>
        )}
        <nav className="view-nav" aria-label="Разделы Vault">
          <button
            type="button"
            aria-pressed={view === "overview"}
            className={view === "overview" ? "active" : ""}
            onClick={() => setView("overview")}
          >
            Обзор
          </button>
          <button
            type="button"
            aria-pressed={view === "catalog"}
            className={view === "catalog" ? "active" : ""}
            onClick={() => setView("catalog")}
          >
            Каталог
          </button>
          <button
            type="button"
            aria-pressed={view === "mcp"}
            className={view === "mcp" ? "active" : ""}
            onClick={() => setView("mcp")}
          >
            MCP
          </button>
        </nav>
        {view === "catalog" ? (
          <>
            <input
              className="search"
              aria-label="Поиск по каталогу"
              placeholder="Название, описание, тема или фильтр…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div className="stats">
              {data ? `${resources.length} ресурсов · ${topics.length} тем · ${facets.length} фильтров` : "загрузка…"}
            </div>
          </>
        ) : view === "overview" ? (
          <div className="mcp-top-status">
            <span aria-hidden="true" />
            {digest?.period.start && digest.period.end
              ? `${digest.period.start} — ${digest.period.end}`
              : "сводка за 7 дней"}
          </div>
        ) : (
          <div className="mcp-top-status"><span aria-hidden="true" /> 5 инструментов · вымышленные данные</div>
        )}
      </header>
      <div className="demo-disclosure" role="note">
        <strong>Демо · вымышленные данные</strong>
        <span>Сценарный чат без генерации ИИ. Здесь нет сообщений реальных людей.</span>
      </div>

      {view === "overview" ? (
        <OverviewPage
          digest={digest}
          error={digestError}
          onOpenCatalog={() => setView("catalog")}
          onOpenResource={openDigestResource}
        />
      ) : view === "catalog" ? (
      <div className={`columns${selected ? " detail-open" : ""}`}>
        {/* ---------- сайдбар ---------- */}
        <nav className="sidebar" aria-label="Фильтры каталога">
          <button
            type="button"
            className={`nav-item${collection.type === "all" ? " active" : ""}`}
            onClick={() => setCollection({ type: "all" })}
          >
            <span className="dot" style={{ background: "#dbe6e1" }} />
            Все ресурсы
            <span className="n">{resources.length}</span>
          </button>

          <div className="nav-head">Темы</div>
          {topics.map((t) => (
            <button
              type="button"
              key={t.id}
              className={`nav-item${collection.type === "topic" && collection.name === t.name ? " active" : ""}`}
              onClick={() => setCollection({ type: "topic", name: t.name })}
            >
              <span className="dot" style={{ background: COLORS["Тема"] }} />
              {t.name}
              <span className="n">{t.val}</span>
            </button>
          ))}

          <div className="nav-head">Типы ресурсов</div>
          {kinds.map((kind) => (
            <button
              type="button"
              key={kind.name}
              className={`nav-item${collection.type === "kind" && collection.name === kind.name ? " active" : ""}`}
              onClick={() => setCollection({ type: "kind", name: kind.name })}
            >
              <span className="dot kind-dot" />
              {kind.name}
              <span className="n">{kind.count}</span>
            </button>
          ))}

          <button
            type="button"
            className="nav-head toggle"
            aria-expanded={facetsOpen}
            onClick={() => setFacetsOpen((value) => !value)}
          >
            Фильтры {facetsOpen ? "▾" : "▸"}
          </button>
          {facetsOpen && facets.map((facet) => (
            <button
              type="button"
              key={facet.name}
              className={`nav-item${collection.type === "facet" && collection.name === facet.name ? " active" : ""}`}
              onClick={() => setCollection({ type: "facet", name: facet.name })}
            >
              <span className="dot facet-dot" />
              {facetLabel(facet.name)}
              <span className="n">{facet.count}</span>
            </button>
          ))}

          <button
            type="button"
            className="nav-head toggle"
            aria-expanded={sourcesOpen}
            onClick={() => setSourcesOpen((value) => !value)}
          >
            Источники {sourcesOpen ? "▾" : "▸"}
          </button>
          {sourcesOpen && sources.map((source) => (
            <button
              type="button"
              key={source.id}
              className={`nav-item${collection.type === "source" && collection.name === source.group ? " active" : ""}`}
              onClick={() => setCollection({ type: "source", name: source.group })}
            >
              <span className="dot" style={{ background: COLORS[source.group] }} />
              {source.group}
              <span className="n">{resources.filter((resource) => resource.group === source.group).length}</span>
            </button>
          ))}

          <button
            type="button"
            className="nav-head toggle"
            aria-expanded={peopleOpen}
            onClick={() => setPeopleOpen((value) => !value)}
          >
            Люди {peopleOpen ? "▾" : "▸"}
          </button>
          {peopleOpen && people.map((person) => (
            <button
              type="button"
              key={person.id}
              className={`nav-item${collection.type === "person" && collection.name === person.name ? " active" : ""}`}
              onClick={() => setCollection({ type: "person", name: person.name })}
            >
              <span className="dot" style={{ background: COLORS["Человек"] }} />
              {person.name}
              <span className="n">{person.val}</span>
            </button>
          ))}
        </nav>

        {/* ---------- карточки ---------- */}
        <main className="cards-col">
          <div className="cards-head">
            <h1>{collTitle}</h1>
            <span className="count">{cards.length}</span>
          </div>
          <div className="catalog-examples" aria-label="Примеры поиска">
            <span>Попробуйте поиск:</span>
            {["Сигналяр", "Навигация", "Нитесвод"].map((example) => (
              <button key={example} type="button" aria-label={`Пример: ${example}`} onClick={() => setQuery(example)}>{example}</button>
            ))}
          </div>
          <div className="cards">
            {cards.map((n) => (
              <article
                key={n.id}
                className={`card${selected?.id === n.id ? " active" : ""}`}
              >
                <button type="button" className="card-open" onClick={() => selectNode(n)}>
                  <span className="card-title">
                    <span className="dot" style={{ background: COLORS[n.group] }} />
                    {n.name}
                  </span>
                  {n.description && <span className="card-desc">{n.description}</span>}
                </button>
                <div className="card-meta">
                  <span>{n.val} упом.</span>
                  {sharersOf(n).slice(0, 2).map((sharer) => (
                    <button
                      type="button"
                      key={sharer}
                      className="sharer"
                      onClick={() => setCollection({ type: "person", name: sharer })}
                    >
                      {sharer}
                    </button>
                  ))}
                  <button
                    type="button"
                    className="kchip"
                    onClick={() => setCollection({ type: "kind", name: n.kind ?? n.group })}
                  >
                    {n.kind ?? n.group}
                  </button>
                  {n.topics.slice(0, 2).map((topic) => (
                    <button
                      type="button"
                      key={topic}
                      className="tchip"
                      onClick={() => setCollection({ type: "topic", name: topic })}
                    >
                      {topic}
                    </button>
                  ))}
                  {(n.facets ?? []).slice(0, 1).map((facet) => (
                    <button
                      type="button"
                      key={facet}
                      className="fchip"
                      onClick={() => setCollection({ type: "facet", name: facet })}
                    >
                      {facetLabel(facet)}
                    </button>
                  ))}
                </div>
              </article>
            ))}
            {cards.length === 0 && <div className="empty">Ничего не найдено</div>}
          </div>
        </main>

        {/* ---------- правая колонка: детали ресурса ---------- */}
        {selected && (
          <aside className="rightcol" aria-labelledby="resource-detail-title">
            <div className="detail">
              <button type="button" className="close" aria-label="Закрыть детали" onClick={() => selectNode(null)}>✕</button>
              <h2 id="resource-detail-title" ref={detailHeadingRef} tabIndex={-1}>{selected.name}</h2>
              {selected.alt && <div className="alt-name mono">{selected.alt}</div>}
              <div className="chips">
                <button
                  type="button"
                  className="chip kind"
                  onClick={() => setCollection({ type: "kind", name: selected.kind ?? selected.group })}
                >
                  {selected.kind ?? selected.group}
                </button>
                <span className="chip">{selected.val} упоминаний</span>
                {selected.topics.map((topic) => (
                  <button type="button" key={topic} className="chip topic" onClick={() => setCollection({ type: "topic", name: topic })}>
                    {topic}
                  </button>
                ))}
                {(selected.facets ?? []).map((facet) => (
                  <button type="button" key={facet} className="chip facet" onClick={() => setCollection({ type: "facet", name: facet })}>
                    {facetLabel(facet)}
                  </button>
                ))}
              </div>
              {selected.description && <p className="desc">{selected.description}</p>}
              {selected.url && <p className="demo-resource-note">Адрес {selected.url} — вымышленный пример, а не внешний сайт.</p>}
              {resourceDetail?.pdf && <PdfFacts info={resourceDetail.pdf} />}
              <div className="mentions">
                {mentions === null ? (
                  <div className="thinking">загрузка контекста</div>
                ) : (
                  mentions.map((m, i) => {
                    const long = m.text.length > 300;
                    const open = expandedM.has(i);
                    return (
                      <article key={m.msg_id} className="mention">
                        <div className="meta">
                          <button
                            type="button"
                            className="mention-sender"
                            onClick={() => setCollection({ type: "person", name: m.sender })}
                          >
                            {m.sender}
                          </button>
                          {" · "}
                          <span className="mono">{m.date}</span>
                        </div>
                        <p>{!long || open ? m.text : m.text.slice(0, 300) + "…"}</p>
                        {long && (
                          <button
                            className="expand"
                            onClick={() =>
                              setExpandedM((s) => {
                                const n2 = new Set(s);
                                n2.has(i) ? n2.delete(i) : n2.add(i);
                                return n2;
                              })
                            }
                          >
                            {open ? "свернуть" : "показать полностью"}
                          </button>
                        )}
                      </article>
                    );
                  })
                )}
              </div>
            </div>
          </aside>
        )}
      </div>
      ) : (
        <McpPage />
      )}

      {/* ---------- чат ---------- */}
      {features.chat && (chatOpen ? (
        <div className="chat">
          <header>
            <span className="spark" aria-hidden="true">✦</span> Сценарный чат
            <button type="button" className="close" aria-label="Закрыть чат" onClick={() => setChatOpen(false)}>✕</button>
          </header>
          <div className="log" ref={logRef} aria-live="polite" aria-busy={thinking}>
            {chatLog.length === 0 && (
              <div className="msg assistant">
                <p>Здесь нет генерации ИИ. Попробуйте один из подготовленных вопросов:</p>
                <div className="demo-prompts">
                  {["Аэролит", "Навигация", "Заметки"].map((prompt) => (
                    <button type="button" key={prompt} onClick={() => void submitChat(prompt)} disabled={thinking}>
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {chatLog.map((m, i) => (
              <div key={i} className={`msg ${m.role}${m.error ? " error" : ""}`}>
                {m.role === "assistant" && !m.error ? (
                  <RichText
                    text={m.content}
                    refs={m.refs ?? []}
                    nodeById={nodeById}
                    onSelect={openChatResource}
                  />
                ) : (
                  m.content
                )}
                {m.refs && m.refs.length > 0 && (
                  <div className="refs">
                    {m.refs.map((k) => {
                      const n = nodeById.get(k);
                      return n ? (
                        <span className="chat-ref-item" key={k}>
                          <button onClick={() => openChatResource(n)}>
                            {n.name.slice(0, 30)}
                          </button>
                        </span>
                      ) : null;
                    })}
                  </div>
                )}
              </div>
            ))}
            {thinking && <div className="thinking">Подбираю подготовленный ответ…</div>}
          </div>
          <form onSubmit={sendChat}>
            <input
              aria-label="Вопрос сценарному чату"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Спросите об аэролите, навигации или заметках…"
              maxLength={300}
              autoFocus
            />
            <button type="submit" aria-label="Отправить вопрос" disabled={thinking || !chatInput.trim()}>→</button>
          </form>
        </div>
      ) : (
        <button type="button" className="chat-toggle" onClick={() => setChatOpen(true)}>✦ Демо-чат</button>
      ))}

      <UpdatesPanel
        entries={updates ?? []}
        open={updatesOpen}
        onClose={closeUpdates}
        triggerRef={versionBadgeRef}
      />
    </div>
  );
}
