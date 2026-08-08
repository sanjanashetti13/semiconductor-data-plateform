import type { VisualizationSpec } from "@/types";
import { cn } from "@/lib/utils";

interface ResultChartProps {
  visualization: VisualizationSpec;
  className?: string;
}

/** Lightweight SVG chart — no extra chart library dependency. */
export function ResultChart({ visualization, className }: ResultChartProps) {
  const data = (visualization.data ?? []).filter(
    (d) => typeof d.value === "number" && Number.isFinite(d.value),
  );
  if (data.length < 2) return null;

  const width = 560;
  const height = 220;
  const pad = { top: 28, right: 16, bottom: 48, left: 48 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const maxVal = Math.max(...data.map((d) => Math.abs(d.value)), 1e-9);
  const minVal = Math.min(0, ...data.map((d) => d.value));
  const span = maxVal - minVal || 1;

  const isLine = visualization.type === "line";

  return (
    <div
      className={cn(
        "mt-3 overflow-hidden rounded-xl border border-cyan-500/25 bg-[#020617]/70 p-3",
        className,
      )}
    >
      {visualization.title && (
        <p className="mb-2 text-xs font-medium text-zinc-300">{visualization.title}</p>
      )}
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-auto w-full max-w-full"
        role="img"
        aria-label={visualization.title || "Chart"}
      >
        <line
          x1={pad.left}
          y1={pad.top + innerH}
          x2={pad.left + innerW}
          y2={pad.top + innerH}
          stroke="rgba(148,163,184,0.35)"
          strokeWidth={1}
        />
        <line
          x1={pad.left}
          y1={pad.top}
          x2={pad.left}
          y2={pad.top + innerH}
          stroke="rgba(148,163,184,0.35)"
          strokeWidth={1}
        />
        {isLine ? (
          <polyline
            fill="none"
            stroke="rgb(34,211,238)"
            strokeWidth={2.5}
            points={data
              .map((d, i) => {
                const x =
                  pad.left +
                  (data.length === 1 ? innerW / 2 : (i / (data.length - 1)) * innerW);
                const y = pad.top + innerH - ((d.value - minVal) / span) * innerH;
                return `${x},${y}`;
              })
              .join(" ")}
          />
        ) : (
          data.map((d, i) => {
            const gap = 4;
            const barW = Math.max(6, innerW / data.length - gap);
            const x = pad.left + i * (innerW / data.length) + gap / 2;
            const h = ((d.value - minVal) / span) * innerH;
            const y = pad.top + innerH - h;
            return (
              <rect
                key={`${d.label}-${i}`}
                x={x}
                y={y}
                width={barW}
                height={Math.max(h, 1)}
                rx={3}
                fill="rgba(34,211,238,0.75)"
              />
            );
          })
        )}
        {data.map((d, i) => {
          const x =
            pad.left +
            (isLine
              ? data.length === 1
                ? innerW / 2
                : (i / (data.length - 1)) * innerW
              : i * (innerW / data.length) + innerW / data.length / 2);
          const label =
            d.label.length > 10 ? `${d.label.slice(0, 9)}…` : d.label;
          return (
            <text
              key={`lbl-${i}`}
              x={x}
              y={height - 12}
              textAnchor="middle"
              fill="rgba(161,161,170,0.95)"
              fontSize={10}
            >
              {label}
            </text>
          );
        })}
      </svg>
      {(visualization.xAxis || visualization.yAxis) && (
        <p className="mt-1 text-[10px] text-zinc-500">
          {[visualization.xAxis, visualization.yAxis].filter(Boolean).join(" · ")}
        </p>
      )}
    </div>
  );
}
