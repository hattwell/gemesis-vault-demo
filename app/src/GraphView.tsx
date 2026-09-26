import { useMemo } from "react";

type Resource = { id: string; name: string; group: string; topics: string[]; val: number };
type Link = { source: string | { id: string }; target: string | { id: string }; kind: string };
type Point = { x: number; y: number };
const idOf = (value: Link["source"]) => typeof value === "string" ? value : value.id;

function layout(nodes: Resource[]) {
  const topics = [...new Set(nodes.flatMap((node) => node.topics))].sort();
  const centers: Point[] = topics.length === 1
    ? [{ x: 480, y: 315 }]
    : topics.length === 2
      ? [{ x: 230, y: 315 }, { x: 730, y: 315 }]
      : [{ x: 230, y: 180 }, { x: 730, y: 180 }, { x: 230, y: 470 }, { x: 730, y: 470 }];
  const positions = new Map<string, Point>();
  topics.forEach((topic, index) => {
    const center = centers[index] ?? { x: 480, y: 315 };
    positions.set(`topic:${topic}`, center);
    const resources = nodes.filter((node) => node.topics[0] === topic)
      .sort((left, right) => left.id.localeCompare(right.id));
    resources.forEach((resource, slot) => {
      const angle = (Math.PI * 2 * slot) / resources.length - Math.PI / 2;
      positions.set(resource.id, {
        x: center.x + Math.cos(angle) * (resources.length === 1 ? 0 : 164),
        y: center.y + Math.sin(angle) * (resources.length === 1 ? -90 : 104),
      });
    });
  });
  return { topics, positions };
}

export default function GraphView({ nodes, links, selectedId, onOpen }: {
  nodes: Resource[]; links: Link[]; selectedId?: string; onOpen: (id: string) => void;
}) {
  const { topics, positions } = useMemo(() => layout(nodes), [nodes]);
  const visibleLinks = useMemo(() => links.filter((link) =>
    (link.kind === "topic" || link.kind === "cooccur") &&
    positions.has(idOf(link.source)) && positions.has(idOf(link.target))), [links, positions]);
  if (nodes.length === 0) return <p className="graph-empty">Нет связанных ресурсов для выбранного фильтра.</p>;

  return (
    <section className="graph-shell" aria-label="Граф связей вымышленных ресурсов">
      <p className="graph-caption">Темы <span className="graph-legend-hub" aria-hidden="true" /> · ресурсы <span className="graph-legend-resource" aria-hidden="true" /> · пунктиром отмечено совместное упоминание. Нажмите на ресурс, чтобы открыть карточку; на телефоне листайте граф по горизонтали.</p>
      <div className="graph-scroll" tabIndex={0} aria-label="Прокручиваемый граф связей">
        <svg className="resource-graph" viewBox="0 0 960 650" aria-label="Граф тем и ресурсов" xmlns="http://www.w3.org/2000/svg">
          <g aria-hidden="true">
            {visibleLinks.map((link) => {
              const source = idOf(link.source);
              const target = idOf(link.target);
              const start = positions.get(source)!;
              const end = positions.get(target)!;
              return <line key={`${link.kind}:${source}:${target}`} className={`graph-link-${link.kind}`}
                x1={start.x} y1={start.y} x2={end.x} y2={end.y} />;
            })}
          </g>
          {topics.map((topic) => {
            const point = positions.get(`topic:${topic}`)!;
            return <g className="graph-topic" key={topic} transform={`translate(${point.x} ${point.y})`}>
              <circle r="46" /><text textAnchor="middle" dominantBaseline="central">{topic}</text>
            </g>;
          })}
          {nodes.map((node) => {
            const point = positions.get(node.id);
            if (!point) return null;
            const open = () => onOpen(node.id);
            return <g key={node.id} data-resource-node="" className={`graph-resource${selectedId === node.id ? " active" : ""}`}
              role="button" tabIndex={0} aria-label={`Открыть ${node.name}`}
              transform={`translate(${point.x} ${point.y})`} onClick={open}
              onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); open(); } }}>
              <circle r="12" /><text textAnchor="middle" y="27">{node.name}</text>
              <title>{node.name}: {node.val} упоминаний</title>
            </g>;
          })}
        </svg>
      </div>
      <p className="graph-footnote">{nodes.length} вымышленных ресурсов · {topics.length} тем · связи построены из демонстрационных сообщений</p>
    </section>
  );
}
