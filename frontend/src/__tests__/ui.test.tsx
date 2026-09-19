import { act, render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PriceCell } from '@/components/PriceCell';
import { Watchlist } from '@/components/Watchlist';
import { PositionsTable } from '@/components/PositionsTable';
import { Heatmap, layout } from '@/components/Heatmap';
import { ChatPanel } from '@/components/ChatPanel';
import { TradeBar } from '@/components/TradeBar';
import { ApiError, normalizePortfolio } from '@/lib/api';

describe('PriceCell flash', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());
  it('flashes up then down then clears after 500ms', () => {
    const { rerender } = render(<PriceCell ticker="AAPL" price={100} />);
    const el = screen.getByTestId('price-AAPL');
    expect(el.dataset.flash).toBe('');
    rerender(<PriceCell ticker="AAPL" price={101} />);
    expect(el.dataset.flash).toBe('up');
    rerender(<PriceCell ticker="AAPL" price={99} />);
    expect(el.dataset.flash).toBe('down');
    act(() => { vi.advanceTimersByTime(500); });
    expect(el.dataset.flash).toBe('');
  });
});

describe('Watchlist', () => {
  const prices: any = { AAPL: { ticker: 'AAPL', price: 190, previous_price: 189, timestamp: 1, direction: 'up', day_change_percent: 1.2 } };
  it('renders rows, selects, adds and removes', async () => {
    const onAdd = vi.fn().mockResolvedValue(undefined), onRemove = vi.fn(), onSelect = vi.fn();
    render(<Watchlist tickers={['AAPL', 'MSFT']} prices={prices} history={{}} selected="AAPL" onSelect={onSelect} onAdd={onAdd} onRemove={onRemove} />);
    expect(screen.getByTestId('watchlist-row-AAPL')).toBeInTheDocument();
    expect(screen.getByTestId('price-AAPL')).toHaveTextContent('$190.00');
    expect(screen.getByTestId('price-MSFT')).toHaveTextContent('--');
    fireEvent.click(screen.getByTestId('watchlist-row-MSFT'));
    expect(onSelect).toHaveBeenCalledWith('MSFT');
    fireEvent.click(screen.getByTestId('watchlist-remove-MSFT'));
    expect(onRemove).toHaveBeenCalledWith('MSFT');
    expect(onSelect).toHaveBeenCalledTimes(1);
    fireEvent.change(screen.getByTestId('watchlist-add-input'), { target: { value: 'pypl' } });
    fireEvent.click(screen.getByTestId('watchlist-add-button'));
    await waitFor(() => expect(onAdd).toHaveBeenCalledWith('PYPL'));
  });
});

describe('Portfolio display', () => {
  const pf = normalizePortfolio({ cash: 5000, positions: [{ ticker: 'AAPL', quantity: 10, avg_cost: 100, current_price: 110 }, { ticker: 'TSLA', quantity: 5, avg_cost: 200, current_price: 180 }] });
  it('computes pnl when missing', () => {
    expect(pf.positions[0].unrealized_pnl).toBe(100);
    expect(pf.positions[1].pnl_percent).toBeCloseTo(-10);
  });
  it('renders positions and heatmap colors', () => {
    render(<><PositionsTable positions={pf.positions} /><Heatmap positions={pf.positions} /></>);
    expect(screen.getByTestId('position-row-AAPL')).toHaveTextContent('+$100.00');
    expect(screen.getByTestId('heatmap-cell-AAPL').dataset.pnl).toBe('profit');
    expect(screen.getByTestId('heatmap-cell-TSLA').dataset.pnl).toBe('loss');
  });
  it('treemap areas sum to 100%', () => {
    const r = layout(pf.positions.map((p) => ({ p, v: p.quantity * p.current_price })), 0, 0, 100, 100);
    expect(r.reduce((s, x) => s + x.w * x.h, 0)).toBeCloseTo(10000);
  });
});

describe('Chat', () => {
  it('renders messages, actions and loading', () => {
    const msgs: any = [
      { id: '1', role: 'user', content: 'buy aapl' },
      { id: '2', role: 'assistant', content: 'Done', trades: [{ ticker: 'AAPL', side: 'buy', quantity: 2, price: 190 }], watchlist_changes: [{ ticker: 'PYPL', action: 'add' }] },
    ];
    render(<ChatPanel messages={msgs} loading={true} onSend={vi.fn()} />);
    expect(screen.getByTestId('chat-trade')).toHaveTextContent('Executed: buy 2 AAPL');
    expect(screen.getByTestId('chat-watchlist-change')).toHaveTextContent('added PYPL');
    expect(screen.getByTestId('chat-loading')).toBeInTheDocument();
  });
  it('sends input', () => {
    const onSend = vi.fn();
    render(<ChatPanel messages={[]} loading={false} onSend={onSend} />);
    fireEvent.change(screen.getByTestId('chat-input'), { target: { value: 'hi' } });
    fireEvent.click(screen.getByTestId('chat-send'));
    expect(onSend).toHaveBeenCalledWith('hi');
  });
});

describe('TradeBar', () => {
  it('shows inline error from a rejected trade', async () => {
    const onTrade = vi.fn().mockRejectedValue(new ApiError(400, 'insufficient_cash', 'Not enough cash'));
    render(<TradeBar onTrade={onTrade} />);
    fireEvent.change(screen.getByTestId('trade-ticker'), { target: { value: 'aapl' } });
    fireEvent.change(screen.getByTestId('trade-quantity'), { target: { value: '5' } });
    fireEvent.click(screen.getByTestId('trade-buy'));
    expect(await screen.findByTestId('trade-error')).toHaveTextContent('Not enough cash');
    expect(onTrade).toHaveBeenCalledWith('AAPL', 5, 'buy');
  });
});
