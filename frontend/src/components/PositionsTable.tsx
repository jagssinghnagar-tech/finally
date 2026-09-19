import type { Position } from '@/lib/types';
import { money, num, pct, pnlClass, signed } from '@/lib/format';

export function PositionsTable({ positions }: { positions: Position[] }) {
  return (
    <section className="panel flex h-full flex-col" aria-label="Positions">
      <h2 className="panel-title">Positions</h2>
      <div className="flex-1 overflow-auto">
        <table className="w-full text-sm" data-testid="positions-table">
          <thead className="sticky top-0 bg-panel text-left text-xs text-dim">
            <tr>{['Ticker', 'Qty', 'Avg cost', 'Price', 'Unrealized P&L', 'Change'].map((h, i) => <th key={h} className={`px-3 py-1 font-normal ${i ? 'text-right' : ''}`}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {positions.length === 0 && <tr><td colSpan={6} className="px-3 py-3 text-dim">No open positions.</td></tr>}
            {positions.map((p) => (
              <tr key={p.ticker} data-testid={`position-row-${p.ticker}`} className="border-t border-line/60">
                <td className="px-3 py-1 font-semibold text-accent">{p.ticker}</td>
                <td data-testid={`position-qty-${p.ticker}`} className="px-3 text-right tabular-nums">{num(p.quantity, p.quantity % 1 ? 4 : 0)}</td>
                <td className="px-3 text-right tabular-nums">{money(p.avg_cost)}</td>
                <td className="px-3 text-right tabular-nums">{money(p.current_price)}</td>
                <td className={`px-3 text-right tabular-nums ${pnlClass(p.unrealized_pnl)}`}>{signed(p.unrealized_pnl)}</td>
                <td className={`px-3 text-right tabular-nums ${pnlClass(p.pnl_percent)}`}>{pct(p.pnl_percent)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
