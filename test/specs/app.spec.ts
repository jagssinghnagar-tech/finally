import { test, expect, Page } from '@playwright/test';

const DEFAULTS = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META', 'JPM', 'V', 'NFLX'];
const num = (s: string | null) => parseFloat((s ?? '').replace(/[^0-9.\-]/g, ''));

// Restore a known state through the API: sell all positions, drop non-default tickers.
test.beforeEach(async ({ request, page }) => {
  const pf = await (await request.get('/api/portfolio')).json();
  for (const p of pf.positions ?? []) {
    await request.post('/api/portfolio/trade', { data: { ticker: p.ticker, quantity: p.quantity, side: 'sell' } });
  }
  const wl = await (await request.get('/api/watchlist')).json();
  const items = Array.isArray(wl) ? wl : wl.watchlist ?? wl.tickers ?? [];
  for (const it of items) {
    const t = typeof it === 'string' ? it : it.ticker;
    if (!DEFAULTS.includes(t)) await request.delete(`/api/watchlist/${t}`);
  }
  await page.goto('/');
});

const cash = (page: Page) => page.getByTestId('cash-balance');

test('fresh start: watchlist, cash, streaming, connection', async ({ page }) => {
  for (const t of DEFAULTS) await expect(page.getByTestId(`watchlist-row-${t}`)).toBeVisible();
  await expect(page.getByTestId('connection-status')).toHaveAttribute('data-status', 'connected');
  await expect(page.getByTestId('price-AAPL')).toHaveText(/\d/);
  const first = await page.getByTestId('price-AAPL').textContent();
  await expect.poll(async () => page.getByTestId('price-AAPL').textContent(), { timeout: 15_000 }).not.toBe(first);
  await expect(page.getByTestId('total-value')).toContainText('$');
});

test('fresh start cash is $10,000 (only on pristine DB)', async ({ page, request }) => {
  const pf = await (await request.get('/api/portfolio')).json();
  test.skip(Math.abs(pf.cash_balance - 10000) > 500, 'DB not pristine (prior trades drifted cash)');
  await expect(cash(page)).toContainText('10,000');
});

test('add and remove a ticker', async ({ page }) => {
  await page.getByTestId('watchlist-add-input').fill('PYPL');
  await page.getByTestId('watchlist-add-button').click();
  await expect(page.getByTestId('watchlist-row-PYPL')).toBeVisible();
  await expect(page.getByTestId('price-PYPL')).toHaveText(/\d/);
  await page.getByTestId('watchlist-remove-PYPL').click();
  await expect(page.getByTestId('watchlist-row-PYPL')).toHaveCount(0);
});

test('buy shares: cash down, position appears; sell removes it', async ({ page }) => {
  await expect(page.getByTestId('price-AAPL')).toHaveText(/\d/);
  const before = num(await cash(page).textContent());
  await page.getByTestId('trade-ticker').fill('AAPL');
  await page.getByTestId('trade-quantity').fill('5');
  await page.getByTestId('trade-buy').click();
  await expect(page.getByTestId('position-row-AAPL')).toBeVisible();
  await expect.poll(async () => num(await cash(page).textContent())).toBeLessThan(before - 100);
  const mid = num(await cash(page).textContent());

  await page.getByTestId('trade-quantity').fill('2');
  await page.getByTestId('trade-sell').click();
  await expect.poll(async () => num(await cash(page).textContent())).toBeGreaterThan(mid);
  await expect(page.getByTestId('position-row-AAPL')).toBeVisible();

  await page.getByTestId('trade-quantity').fill('3');
  await page.getByTestId('trade-sell').click();
  await expect(page.getByTestId('position-row-AAPL')).toHaveCount(0);
});

test('portfolio visualisation: heatmap cell and P&L chart points', async ({ page }) => {
  await page.getByTestId('trade-ticker').fill('MSFT');
  await page.getByTestId('trade-quantity').fill('2');
  await page.getByTestId('trade-buy').click();
  await expect(page.getByTestId('heatmap-cell-MSFT')).toBeVisible();
  await expect.poll(async () => Number(await page.getByTestId('pnl-chart').getAttribute('data-points'))).toBeGreaterThan(0);
});

test('mocked AI chat: buy shows inline trade', async ({ page }) => {
  await page.getByTestId('chat-input').fill('please buy some AAPL');
  await page.getByTestId('chat-send').click();
  await expect(page.getByTestId('chat-message-assistant').last()).toContainText(/AAPL/);
  await expect(page.getByTestId('chat-trade').first()).toBeVisible();
  await expect(page.getByTestId('position-row-AAPL')).toBeVisible();
});

test('trade error: insufficient cash shows inline error', async ({ page }) => {
  await page.getByTestId('trade-ticker').fill('AAPL');
  await page.getByTestId('trade-quantity').fill('1000000');
  await page.getByTestId('trade-buy').click();
  await expect(page.getByTestId('trade-error')).toBeVisible();
  await expect(page.getByTestId('trade-error')).toContainText(/cash|insufficient|available/i);
});

test('trade error: selling shares not owned', async ({ page }) => {
  await page.getByTestId('trade-ticker').fill('NFLX');
  await page.getByTestId('trade-quantity').fill('1');
  await page.getByTestId('trade-sell').click();
  await expect(page.getByTestId('trade-error')).toBeVisible();
});
