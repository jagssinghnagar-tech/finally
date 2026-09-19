export function Sparkline({ points, up }: { points: number[]; up: boolean }) {
  const w = 72, h = 22;
  if (points.length < 2) return <svg width={w} height={h} aria-hidden />;
  const min = Math.min(...points), max = Math.max(...points), r = max - min || 1;
  const d = points.map((p, i) => `${((i / (points.length - 1)) * w).toFixed(1)},${(h - 2 - ((p - min) / r) * (h - 4)).toFixed(1)}`).join(' ');
  return (
    <svg width={w} height={h} data-testid="sparkline" aria-hidden>
      <polyline points={d} fill="none" stroke={up ? '#2ecc71' : '#f0483e'} strokeWidth="1.3" />
    </svg>
  );
}
