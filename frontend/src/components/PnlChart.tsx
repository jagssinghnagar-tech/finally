'use client';
import { useEffect, useRef } from 'react';
import { createChart, type IChartApi, type ISeriesApi, type UTCTimestamp } from 'lightweight-charts';
import type { Snapshot } from '@/lib/types';
import { chartOpts } from './PriceChart';

export function PnlChart({ snapshots }: { snapshots: Snapshot[] }) {
  const el = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);
  const series = useRef<ISeriesApi<'Line'> | null>(null);
  useEffect(() => {
    if (!el.current) return;
    chart.current = createChart(el.current, chartOpts as any);
    series.current = chart.current.addLineSeries({ color: '#ecad0a', lineWidth: 2 });
    return () => { chart.current?.remove(); chart.current = null; };
  }, []);
  useEffect(() => {
    let last = 0;
    const pts = snapshots.flatMap((s) => {
      let t = Math.floor(new Date(s.recorded_at).getTime() / 1000);
      if (Number.isNaN(t)) return [];
      if (t <= last) t = last + 1;
      last = t;
      return [{ time: t as UTCTimestamp, value: s.total_value }];
    });
    series.current?.setData(pts);
    chart.current?.timeScale().fitContent();
  }, [snapshots]);
  return (
    <section className="panel flex h-full flex-col" aria-label="Portfolio value">
      <h2 className="panel-title">Portfolio value</h2>
      <div ref={el} data-testid="pnl-chart" data-points={snapshots.length} className="min-h-0 flex-1" />
    </section>
  );
}
