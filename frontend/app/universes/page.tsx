'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { createUniverse } from '@/lib/api/universes';

const DEFAULT_TICKERS = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA'];

export default function UniversesPage() {
  const router = useRouter();
  const [name, setName] = useState('Mein Universum');
  const [tickers, setTickers] = useState<string[]>(DEFAULT_TICKERS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateTicker = (index: number, value: string) => {
    setTickers((prev) => prev.map((t, i) => (i === index ? value.toUpperCase() : t)));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const universe = await createUniverse(name, tickers.filter(Boolean));
      router.push(`/rankings?universe_id=${universe.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Erstellen');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-lg">
      <Card>
        <CardHeader>
          <CardTitle>Universum erstellen</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4" data-testid="universe-form">
            <div>
              <label className="mb-1 block text-sm font-medium">Name</label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Universum-Name"
                data-testid="universe-name"
              />
            </div>
            <div className="space-y-2">
              <label className="block text-sm font-medium">Ticker-Symbole (5)</label>
              {tickers.map((ticker, i) => (
                <Input
                  key={i}
                  value={ticker}
                  onChange={(e) => updateTicker(i, e.target.value)}
                  placeholder={`Ticker ${i + 1}`}
                  data-testid={`ticker-input-${i}`}
                />
              ))}
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button
              type="submit"
              className="w-full"
              disabled={loading}
              data-testid="create-universe-btn"
            >
              {loading ? 'Wird erstellt…' : 'Universum erstellen'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
