import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import type { Universe } from '@/lib/api/universes';

type Props = {
  universes: Universe[];
  isLoading: boolean;
  error: Error | null;
};

function Skeleton() {
  return (
    <div className="space-y-2">
      {[0, 1, 2].map((i) => (
        <div key={i} className="h-10 animate-pulse rounded bg-muted" />
      ))}
    </div>
  );
}

export function UniverseList({ universes, isLoading, error }: Props) {
  if (isLoading) return <Skeleton />;

  if (error) {
    return (
      <p className="text-sm text-destructive">
        Fehler beim Laden: {error.message}
      </p>
    );
  }

  if (universes.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Noch keine Universen.{' '}
        <Link href="/universes/new" className="underline">
          Erstelle ein neues.
        </Link>
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Region</TableHead>
          <TableHead>Ticker</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {universes.map((u) => (
          <TableRow key={u.id}>
            <TableCell className="font-medium">{u.name}</TableCell>
            <TableCell>{u.region}</TableCell>
            <TableCell>{u.tickers.length}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
