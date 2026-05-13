'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import type { Metadata } from 'next';
import { Button } from '@/components/ui/button';
import { UniverseList } from '@/components/universe-list';
import { listUniverses } from '@/lib/api/universes';

export default function UniversesPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['universes'],
    queryFn: listUniverses,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Universen</h1>
        <Button asChild>
          <Link href="/universes/new">Neues Universum</Link>
        </Button>
      </div>

      <UniverseList
        universes={data ?? []}
        isLoading={isLoading}
        error={error}
      />
    </div>
  );
}
