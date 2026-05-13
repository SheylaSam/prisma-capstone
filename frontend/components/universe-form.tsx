'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { CreateUniverseInput } from '@/lib/api/universes';

type Props = {
  onSubmit: (data: CreateUniverseInput) => Promise<void>;
  isSubmitting?: boolean;
  error?: string | null;
};

export function UniverseForm({ onSubmit, isSubmitting = false, error }: Props) {
  const [name, setName] = useState('');
  const [region, setRegion] = useState('CH');
  const [tickersRaw, setTickersRaw] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const tickers = tickersRaw
      .split(',')
      .map((t) => t.trim().toUpperCase())
      .filter(Boolean);
    await onSubmit({ name, region, tickers });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1">
        <label htmlFor="universe-name" className="text-sm font-medium">
          Name
        </label>
        <Input
          id="universe-name"
          placeholder="z.B. Swiss Blue Chips"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          disabled={isSubmitting}
        />
      </div>

      <div className="space-y-1">
        <label htmlFor="universe-region" className="text-sm font-medium">
          Region
        </label>
        <Input
          id="universe-region"
          placeholder="z.B. CH oder US"
          value={region}
          onChange={(e) => setRegion(e.target.value)}
          required
          disabled={isSubmitting}
        />
      </div>

      <div className="space-y-1">
        <label htmlFor="universe-tickers" className="text-sm font-medium">
          Ticker (kommagetrennt)
        </label>
        <textarea
          id="universe-tickers"
          className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          placeholder="z.B. NESN, NOVN, ROG"
          value={tickersRaw}
          onChange={(e) => setTickersRaw(e.target.value)}
          required
          disabled={isSubmitting}
        />
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Wird gespeichert…' : 'Universum erstellen'}
      </Button>
    </form>
  );
}
