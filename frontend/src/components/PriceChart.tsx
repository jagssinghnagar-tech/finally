'use client';
import { useEffect, useRef } from 'react';
import { createChart, type IChartApi, type ISeriesApi, type UTCTimestamp } from 'lightweight-charts';

export const chartOpts = {
  layout: { background: { color: 'transparent' }, textColor: '#7d8b9d', fontFamily: 'IBM Plex Mono, Consolas, monospace' },
  grid: { vertLines: { color: '#1b2430' }, horzLines: { color: '#1b2430' } },
  rightPriceScale: { borderColor: '#252f3d' },
  timeScale: { borderColor: '#252f3d', timeVisible: true, secondsVisible: true },
  autoSize: true,
} as const;

/** Line chart of the selected ticker built from accumulated SSE points. */
export function PriceChart({ ticker, data, tick }: { ticker: string | null; data: { time: number; value: number }[]; tick: number }) {
  const el = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);
  const series = useRef<ISeriesApi<'Area'> | null>(null);
  useEffect(() => {
    if (!el.current) return;
    chart.current = createChart(el.current, chartOpts as any);
    series.current = chart.current.addAreaSeries({ lineColor: '#209dd7', topColor: 'rgba(32,157,215,0.28)', bottomColor: 'rgba(32,157,215,0)', lineWidth: 2 });
    return () => { chart.current?.remove(); chart.current = null; };
  }, []);
  useEffect(() => {
    series.current?.setData(data.map((d) => ({ time: d.time as UTCTimestamp, value: d.value })));
  }, [ticker, tick, data]);
  return (
    <section className="panel flex h-full flex-col" aria-label="Price chart">
      <h2 className="panel-title">{ticker ?? 'Select a ticker'}</h2>
      <div ref={el} data-testid="main-chart" className="min-h-0 flex-1" />
    </section>
  );
}
