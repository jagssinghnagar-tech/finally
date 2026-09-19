import type { Position } from '@/lib/types';

interface Rect { p: Position; x: number; y: number; w: number; h: number }
type Item = { p: Position; v: number };

/** Recursive balanced-split treemap layout (values sorted descending). */
export function layout(items: Item[], x: number, y: number, w: number, h: number): Rect[] {
  if (!items.length) return [];
  if (items.length === 1) return [{ p: items[0].p, x, y, w, h }];
  const total = items.reduce((s, i) => s + i.v, 0);
  let acc = 0, k = 0;
  while (k < items.length - 1 && acc + items[k].v <= total / 2) acc += items[k++].v;
  if (k === 0) { acc = items[0].v; k = 1; }
  const a = items.slice(0, k), b = items.slice(k);
  const ratio = acc / total;
  return w >= h
    ? [...layout(a, x, y, w * ratio, h), ...layout(b, x + w * ratio, y, w * (1 - ratio), h)]
    : [...layout(a, x, y, w, h * ratio), ...layout(b, x, y + h * ratio, w, h * (1 - ratio))];
}

export function pnlColor(pct: number) {
  const a = Math.min(Math.abs(pct) / 5, 1) * 0.55 + 0.25;
  return pct >= 0 ? `rgba(46,204,113,${a})` : `rgba(240,72,62,${a})`;
}

export function Heatmap({ positions }: { positions: Position[] }) {
  const items = positions
    .map((p) => ({ p, v: p.quantity * p.current_price }))
    .filter((i) => i.v > 0)
    .sort((a, b) => b.v - a.v);
  const rects = layout(items, 0, 0, 100, 100);
  return (
    <section className="panel flex h-full flex-col" aria-label="Portfolio heatmap">
      <h2 className="panel-title">Heatmap</h2>
      <div data-testid="heatmap" className="relative m-2 min-h-0 flex-1">
        {rects.length === 0 && <p className="p-3 text-sm text-dim">Buy a stock to see your positions here.</p>}
        {rects.map(({ p, x, y, w, h }) => (
          <div
            key={p.ticker}
            data-testid={`heatmap-cell-${p.ticker}`}
            data-pnl={p.pnl_percent >= 0 ? 'profit' : 'loss'}
            style={{ left: `${x}%`, top: `${y}%`, width: `${w}%`, height: `${h}%`, background: pnlColor(p.pnl_percent) }}
            className="absolute overflow-hidden border border-bg p-1.5 text-xs"
          >
            <div className="font-semibold">{p.ticker}</div>
            <div className="tabular-nums">{p.pnl_percent >= 0 ? '+' : ''}{p.pnl_percent.toFixed(2)}%</div>
          </div>
        ))}
      </div>
    </section>
  );
}
