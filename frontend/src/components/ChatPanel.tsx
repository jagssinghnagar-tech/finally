'use client';
import { useEffect, useRef, useState } from 'react';
import type { ChatMessage } from '@/lib/types';

export function ChatMessageView({ m }: { m: ChatMessage }) {
  return (
    <div data-testid={`chat-message-${m.role}`} className={`mb-3 ${m.role === 'user' ? 'text-right' : ''}`}>
      <div className={`inline-block max-w-[92%] whitespace-pre-wrap rounded px-3 py-2 text-left text-sm ${m.role === 'user' ? 'bg-purple/40' : 'bg-raised'}`}>{m.content}</div>
      {m.trades?.map((t, i) => (
        <div key={i} data-testid="chat-trade" className={`mt-1 text-xs ${t.error ? 'text-down' : 'text-up'}`}>
          {t.error ? `Trade failed: ${t.side} ${t.quantity} ${t.ticker} - ${t.error}` : `Executed: ${t.side} ${t.quantity} ${t.ticker}${t.price ? ` @ $${t.price}` : ''}`}
        </div>
      ))}
      {m.watchlist_changes?.map((w, i) => (
        <div key={i} data-testid="chat-watchlist-change" className={`mt-1 text-xs ${w.error ? 'text-down' : 'text-blue'}`}>
          {w.error ? `Watchlist failed: ${w.action} ${w.ticker} - ${w.error}` : `Watchlist: ${w.action === 'add' ? 'added' : 'removed'} ${w.ticker}`}
        </div>
      ))}
    </div>
  );
}

export function ChatPanel({ messages, loading, onSend }: { messages: ChatMessage[]; loading: boolean; onSend: (t: string) => void }) {
  const [text, setText] = useState('');
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView?.({ block: 'end' }); }, [messages, loading]);
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const t = text.trim();
    if (!t || loading) return;
    setText(''); onSend(t);
  };
  return (
    <aside data-testid="chat-panel" className="flex h-full w-full flex-col border-l border-line bg-panel">
      <h2 className="panel-title">FinAlly assistant</h2>
      <div className="flex-1 overflow-y-auto p-3" data-testid="chat-messages">
        {messages.length === 0 && <p className="text-sm text-dim">Ask about your portfolio, or tell me to buy, sell, or watch a ticker.</p>}
        {messages.map((m) => <ChatMessageView key={m.id} m={m} />)}
        {loading && <div data-testid="chat-loading" className="text-sm text-dim" role="status">Thinking<span className="dots" /></div>}
        <div ref={end} />
      </div>
      <form onSubmit={submit} className="flex gap-1 border-t border-line p-2">
        <input data-testid="chat-input" aria-label="Message" value={text} onChange={(e) => setText(e.target.value)} placeholder="Message FinAlly" className="field min-w-0 flex-1" />
        <button data-testid="chat-send" type="submit" disabled={loading} className="btn bg-purple text-white">Send</button>
      </form>
    </aside>
  );
}
