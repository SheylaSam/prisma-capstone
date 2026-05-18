'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { createRun, getRankings, type RankingItem } from '@/lib/api/runs';

function RankingsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const universeId = searchParams.get('universe_id') ?? '';
  const [rankings, setRankings] = useState<RankingItem[]>([]);
  const [runId, setRunId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startRun = async () => {
    if (!universeId) {
      setError('Kein Universum ausgewählt.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const run = await createRun(universeId);
      setRunId(run.id);
      const results = await getRankings(run.id);
      setRankings(results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ranking-Fehler');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Rankings</CardTitle>
        <div className="flex gap-2">
          <Button
            onClick={startRun}
            disabled={loading || !universeId}
            data-testid="start-ranking-btn"
          >
            {loading ? 'Läuft…' : 'Ranking starten'}
          </Button>
          {runId && (
            <Button
              variant="outline"
              onClick={() => router.push(`/backtest?run_id=${runId}`)}
              data-testid="go-to-backtest-btn"
            >
              Backtest
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {error && <p className="mb-4 text-sm text-destructive">{error}</p>}
        {rankings.length === 0 && !loading && (
          <p className="text-muted-foreground">
            {universeId
              ? 'Noch kein Ranking. Klicke "Ranking starten".'
              : 'Kein Universum ausgewählt. Gehe zurück zu Universen.'}
          </p>
        )}
        {rankings.length > 0 && (
          <Table data-testid="rankings-table">
            <TableHeader>
              <TableRow>
                <TableHead>Rang</TableHead>
                <TableHead>Ticker</TableHead>
                <TableHead>Sweet Spot</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rankings.map((item) => (
                <TableRow
                  key={item.ticker}
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() => router.push(`/stocks/${item.ticker}?run_id=${runId}`)}
                  data-testid={`ranking-row-${item.ticker}`}
                >
                  <TableCell>{item.total_rank}</TableCell>
                  <TableCell className="font-mono font-bold">{item.ticker}</TableCell>
                  <TableCell>
                    {item.is_sweet_spot && <Badge variant="default">Sweet Spot</Badge>}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

export default function RankingsPage() {
  return (
    <Suspense>
      <RankingsContent />
    </Suspense>
  );
}
