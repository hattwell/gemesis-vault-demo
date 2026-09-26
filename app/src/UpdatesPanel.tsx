import { useEffect, useId, useRef } from "react";

export type UpdateEntry = {
  version: string;
  date: string;
  title: string;
  changes: string[];
};

type Props = {
  entries: UpdateEntry[];
  open: boolean;
  onClose: () => void;
  triggerRef: React.RefObject<HTMLButtonElement>;
};

const dateFormatter = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "long",
  year: "numeric",
});

function formatDate(value: string) {
  return dateFormatter.format(new Date(`${value}T12:00:00`));
}

const FOCUSABLE = 'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])';

export default function UpdatesPanel({ entries, open, onClose, triggerRef }: Props) {
  const panelRef = useRef<HTMLDivElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const titleId = useId();

  // Открытие: фокус на заголовок. Закрытие (или размонтирование): фокус обратно на бейдж версии.
  useEffect(() => {
    if (!open) return;
    headingRef.current?.focus();
    return () => triggerRef.current?.focus();
  }, [open, triggerRef]);

  // Пока панель открыта: Escape закрывает, Tab/Shift+Tab ходят по кругу только внутри неё.
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        onClose();
        return;
      }
      if (event.key !== "Tab") return;
      const panel = panelRef.current;
      if (!panel) return;
      const items = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (el) => !el.hasAttribute("disabled") && el.tabIndex >= 0
      );
      const first = items[0];
      const last = items[items.length - 1];
      if (!first || !last) { event.preventDefault(); return; }
      const active = document.activeElement;
      // фокус вне items (заголовок, либо утечка за пределы) — считаем границей в обе стороны
      const idx = active instanceof HTMLElement ? items.indexOf(active) : -1;
      if (event.shiftKey ? idx <= 0 : idx === -1 || idx === items.length - 1) {
        event.preventDefault();
        (event.shiftKey ? last : first).focus();
      }
    };
    document.addEventListener("keydown", onKeyDown, true);
    return () => document.removeEventListener("keydown", onKeyDown, true);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="updates-overlay" onClick={onClose}>
      <div
        className="updates-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        ref={panelRef}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="updates-head">
          <h2 id={titleId} className="updates-title" ref={headingRef} tabIndex={-1}>
            История обновлений
          </h2>
          <button
            type="button"
            className="close updates-close"
            aria-label="Закрыть панель обновлений"
            onClick={onClose}
          >
            ✕
          </button>
        </div>
        <div className="updates-list">
          {entries.map((entry) => (
            <article key={entry.version} className="update-entry">
              <header>
                <span className="update-version">версия {entry.version}</span>
                <time dateTime={entry.date}>{formatDate(entry.date)}</time>
              </header>
              <h3>{entry.title}</h3>
              <ul>
                {entry.changes.map((change, i) => (
                  <li key={i}>{change}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}
