'use client';
import { useState } from 'react';

export function TradeBar({ onTrade, defaultTicker }: { onTrade: (t: string, q: number, s: 'buy' | 'sell') => Promise<void>; defaultTicker?: string | null }) {
  const [ticker, setTicker] = useState('');
  const [qty, setQty] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const go = async (side: 'buy' | 'sell') => {
    const t = (ticker || defaultTicker || '').trim().toUpperCase();
    const q = parseFloat(qty);
    if (!t || !(q > 0)) { setErr('Enter a ticker and a quantity greater than zero.'); return; }
    setBusy(true); setErr('');
    try { await onTrade(t, q, side); setQty(''); }
    catch (e) { setErr(e instanceof Error ? e.message : 'Trade failed'); }
    finally { setBusy(false); }
  };
  return (
    <div className="border-t border-line bg-panel px-3 py-2" aria-label="Trade">
      <div className="flex flex-wrap items-center gap-2">
        <input data-testid="trade-ticker" aria-label="Ticker" placeholder={defaultTicker ?? 'Ticker'} value={ticker} onChange={(e) => setTicker(e.target.value)} className="field w-24 uppercase" />
        <input data-testid="trade-quantity" aria-label="Quantity" type="number" min="0" step="any" placeholder="Qty" value={qty} onChange={(e) => setQty(e.target.value)} className="field w-24" />
        <button data-testid="trade-buy" disabled={busy} onClick={() => go('buy')} className="btn bg-purple text-white">Buy</button>
        <button data-testid="trade-sell" disabled={busy} onClick={() => go('sell')} className="btn border border-purple text-white">Sell</button>
        {err && <span data-testid="trade-error" role="alert" className="text-sm text-down">{err}</span>}
      </div>
    </div>
  );
}
