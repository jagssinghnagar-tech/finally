'use client';
import { useEffect, useRef, useState } from 'react';
import { money } from '@/lib/format';

/** Price text that flashes green/red briefly when the value changes. */
export function PriceCell({ ticker, price }: { ticker: string; price: number | undefined }) {
  const prev = useRef<number | undefined>(price);
  const [flash, setFlash] = useState<'up' | 'down' | null>(null);
  useEffect(() => {
    if (price === undefined || prev.current === undefined || price === prev.current) { prev.current = price; return; }
    setFlash(price > prev.current ? 'up' : 'down');
    prev.current = price;
    const t = setTimeout(() => setFlash(null), 500);
    return () => clearTimeout(t);
  }, [price]);
  return (
    <span
      data-testid={`price-${ticker}`}
      data-flash={flash ?? ''}
      className={`price-cell tabular-nums ${flash === 'up' ? 'flash-up' : flash === 'down' ? 'flash-down' : ''}`}
    >
      {price === undefined ? '--' : money(price)}
    </span>
  );
}
