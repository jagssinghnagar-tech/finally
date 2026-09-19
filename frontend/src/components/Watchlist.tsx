'use client';
import { useState } from 'react';
import type { PriceMap } from '@/lib/types';
import { pct, pnlClass } from '@/lib/format';
import { PriceCell } from './PriceCell';
import { Sparkline } from './Sparkline';

interface Props {
  tickers: string[];
  prices: PriceMap;
  history: Record<string, { value: number }[]>;
  selected: string | null;
  onSelect: (t: string) => void;
  onAdd: (t: string) => Promise<void> | void;
  onRemove: (t: string) => Promise<void> | void;
}

export function Watchlist({ tickers, prices, history, selected, onSelect, onAdd, onRemove }: Props) {
  const [input, setInput] = useState('');
  const [err, setErr] = useState('');
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const t = input.trim().toUpperCase();
    if (!t) return;
    try { setErr(''); await onAdd(t); setInput(''); } catch (x: any) { setErr(x.message ?? 'Could not add ticker'); }
  };
  return (
    <section className="panel flex h-full flex-col" aria-label="Watchlist">
      <h2 className="panel-title">Watchlist</h2>
      <div className="flex-1 overflow-y-auto">
        {tickers.map((t) => {
          const p = prices[t];
          const chg = p?.day_change_percent ?? p?.change_percent;
          return (
            <div
              key={t}
              data-testid={`watchlist-row-${t}`}
              onClick={() => onSelect(t)}
              className={`group grid cursor-pointer grid-cols-[3.6rem_1fr_4.2rem_4.5rem_1rem] items-center gap-2 border-b border-line/60 px-3 py-1.5 text-sm hover:bg-raised ${selected === t ? 'bg-raised shadow-[inset_2px_0_0_#ecad0a]' : ''}`}
            >
              <span className="font-semibold text-accent">{t}</span>
              <Sparkline points={(history[t] ?? []).map((x) => x.value)} up={(p?.direction ?? 'up') !== 'down'} />
              <span className="text-right"><PriceCell ticker={t} price={p?.price} /></span>
              <span data-testid={`change-${t}`} className={`text-right tabular-nums ${pnlClass(chg ?? 0)}`}>{pct(chg)}</span>
              <button
                data-testid={`watchlist-remove-${t}`}
                aria-label={`Remove ${t}`}
                onClick={(e) => { e.stopPropagation(); onRemove(t); }}
                className="text-dim opacity-0 hover:text-down focus:opacity-100 group-hover:opacity-100"
              >&times;</button>
            </div>
          );
        })}
      </div>
      <form onSubmit={submit} className="border-t border-line p-2">
        <div className="flex gap-1">
          <input data-testid="watchlist-add-input" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Add ticker" aria-label="Add ticker" className="field min-w-0 flex-1 uppercase" />
          <button data-testid="watchlist-add-button" type="submit" className="btn bg-blue/90 text-bg">Add</button>
        </div>
        {err && <p data-testid="watchlist-error" role="alert" className="mt-1 text-xs text-down">{err}</p>}
      </form>
    </section>
  );
}
