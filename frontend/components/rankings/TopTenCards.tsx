import Link from 'next/link';
import { Star } from 'lucide-react';

import { ROUTES } from '@/lib/routes';
import type { RankingItem } from '@/lib/api/runs';

interface Props {
  items: RankingItem[];
  runId: string;
}

export function TopTenCards({ items, runId }: Props) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {items.map((item) => {
        const sweetSpotClasses = item.is_sweet_spot
          ? 'border-pink-500 bg-pink-50/60 dark:border-pink-600 dark:bg-pink-950/30'
          : 'border-border bg-card';
        return (
          <Link
            key={item.ticker}
            href={ROUTES.factsheet(runId, item.ticker)}
            className={`block rounded-lg border p-3 transition-colors hover:bg-muted/50 ${sweetSpotClasses}`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground">
                #{item.total_rank ?? '—'}
              </span>
              {item.is_sweet_spot && (
                <Star
                  className="h-3.5 w-3.5 fill-pink-600 text-pink-600"
                  aria-label="Sweet-Spot"
                />
              )}
            </div>
            <div className="mt-1 font-mono text-xl font-bold">{item.ticker}</div>
          </Link>
        );
      })}
    </div>
  );
}
