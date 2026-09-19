'use client';
import { useCallback, useEffect, useState } from 'react';
import * as api from '@/lib/api';
import { usePrices } from '@/lib/usePrices';
import type { ChatMessage, Portfolio, Snapshot } from '@/lib/types';
import { Header } from '@/components/Header';
import { Watchlist } from '@/components/Watchlist';
import { PriceChart } from '@/components/PriceChart';
import { PnlChart } from '@/components/PnlChart';
import { Heatmap } from '@/components/Heatmap';
import { PositionsTable } from '@/components/PositionsTable';
import { TradeBar } from '@/components/TradeBar';
import { ChatPanel } from '@/components/ChatPanel';

const empty: Portfolio = { cash_balance: 10000, total_value: 10000, unrealized_pnl: 0, positions: [] };

export default function Home() {
  const { prices, status, history, tick } = usePrices();
  const [tickers, setTickers] = useState<string[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [portfolio, setPortfolio] = useState<Portfolio>(empty);
  const [snaps, setSnaps] = useState<Snapshot[]>([]);
  const [chatOpen, setChatOpen] = useState(true);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);

  const refreshPortfolio = useCallback(async () => {
    try { setPortfolio(await api.getPortfolio()); } catch { /* keep last */ }
  }, []);
  const refreshHistory = useCallback(async () => {
    try { setSnaps(await api.getHistory()); } catch { /* keep last */ }
  }, []);
  const refreshWatchlist = useCallback(async () => {
    try { const l = await api.getWatchlist(); setTickers(l); setSelected((s) => s ?? l[0] ?? null); } catch { /* keep last */ }
  }, []);

  useEffect(() => {
    refreshWatchlist(); refreshPortfolio(); refreshHistory();
    const a = setInterval(refreshPortfolio, 5000);
    const b = setInterval(refreshHistory, 30000);
    return () => { clearInterval(a); clearInterval(b); };
  }, [refreshWatchlist, refreshPortfolio, refreshHistory]);

  // Live-value the portfolio from streamed prices between server refreshes.
  const positions = portfolio.positions.map((p) => {
    const cur = prices[p.ticker]?.price ?? p.current_price;
    const pnl = (cur - p.avg_cost) * p.quantity;
    return { ...p, current_price: cur, unrealized_pnl: pnl, pnl_percent: p.avg_cost ? ((cur - p.avg_cost) / p.avg_cost) * 100 : 0 };
  });
  const mv = positions.reduce((s, p) => s + p.quantity * p.current_price, 0);
  const totalValue = portfolio.cash_balance + mv;
  const totalPnl = positions.reduce((s, p) => s + p.unrealized_pnl, 0);

  const doTrade = async (t: string, q: number, s: 'buy' | 'sell') => {
    await api.trade(t, q, s);
    await Promise.all([refreshPortfolio(), refreshHistory()]);
  };

  const send = async (text: string) => {
    setMessages((m) => [...m, { id: `u${Date.now()}`, role: 'user', content: text }]);
    setLoading(true);
    try {
      const r = await api.sendChat(text);
      setMessages((m) => [...m, { id: `a${Date.now()}`, role: 'assistant', content: r.message, trades: r.trades, watchlist_changes: r.watchlist_changes }]);
      await Promise.all([refreshPortfolio(), refreshHistory(), refreshWatchlist()]);
    } catch (e: any) {
      setMessages((m) => [...m, { id: `e${Date.now()}`, role: 'assistant', content: e?.message ?? 'The assistant is unavailable. Try again.' }]);
    } finally { setLoading(false); }
  };

  return (
    <div className="flex h-screen flex-col">
      <Header total={totalValue} cash={portfolio.cash_balance} pnl={totalPnl} status={status} onToggleChat={() => setChatOpen((o) => !o)} />
      <div className="flex min-h-0 flex-1">
        <main className="grid min-w-0 flex-1 grid-cols-[minmax(17rem,22rem)_1fr] grid-rows-[minmax(0,1.3fr)_minmax(0,1fr)_auto] gap-px bg-line">
          <div className="row-span-2 min-h-0"><Watchlist tickers={tickers} prices={prices} history={history} selected={selected}
            onSelect={setSelected}
            onAdd={async (t) => { await api.addTicker(t); await refreshWatchlist(); }}
            onRemove={async (t) => { await api.removeTicker(t); await refreshWatchlist(); }} /></div>
          <div className="grid min-h-0 grid-cols-2 gap-px">
            <div className="min-h-0"><PriceChart ticker={selected} data={selected ? history[selected] ?? [] : []} tick={tick} /></div>
            <div className="min-h-0"><PnlChart snapshots={snaps} /></div>
          </div>
          <div className="grid min-h-0 grid-cols-[1fr_1.4fr] gap-px">
            <div className="min-h-0"><Heatmap positions={positions} /></div>
            <div className="min-h-0"><PositionsTable positions={positions} /></div>
          </div>
          <div className="col-span-2"><TradeBar onTrade={doTrade} defaultTicker={selected} /></div>
        </main>
        {chatOpen && <div className="w-80 shrink-0 lg:w-96"><ChatPanel messages={messages} loading={loading} onSend={send} /></div>}
      </div>
    </div>
  );
}
