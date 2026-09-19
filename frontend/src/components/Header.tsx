import type { ConnStatus } from '@/lib/usePrices';
import { money, signed, pnlClass } from '@/lib/format';

const dot: Record<ConnStatus, string> = { connected: 'bg-up', reconnecting: 'bg-accent', disconnected: 'bg-down' };

export function Header({ total, cash, pnl, status, onToggleChat }: { total: number; cash: number; pnl: number; status: ConnStatus; onToggleChat: () => void }) {
  return (
    <header className="flex items-center justify-between border-b border-line bg-panel px-4 py-2">
      <div className="flex items-baseline gap-2">
        <span className="font-sans text-lg font-semibold tracking-tight text-accent">Fin<span className="text-blue">Ally</span></span>
        <span className="hidden text-xs text-dim sm:inline">simulated trading workstation</span>
      </div>
      <div className="flex items-center gap-6 text-sm">
        <div><span className="mr-2 text-dim">Portfolio</span><b data-testid="total-value" className="tabular-nums text-base">{money(total)}</b>
          <span className={`ml-2 text-xs tabular-nums ${pnlClass(pnl)}`}>{signed(pnl)}</span></div>
        <div><span className="mr-2 text-dim">Cash</span><b data-testid="cash-balance" className="tabular-nums">{money(cash)}</b></div>
        <div className="flex items-center gap-1.5" title={status}>
          <span data-testid="connection-status" data-status={status} className={`h-2.5 w-2.5 rounded-full ${dot[status]}`} />
          <span className="hidden text-xs text-dim md:inline">{status}</span>
        </div>
        <button data-testid="chat-toggle" onClick={onToggleChat} className="btn border border-line text-ink">Assistant</button>
      </div>
    </header>
  );
}
