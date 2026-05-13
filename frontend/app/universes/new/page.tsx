'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { UniverseForm } from '@/components/universe-form';
import { createUniverse } from '@/lib/api/universes';
import { ApiError } from '@/lib/api/client';

export default function NewUniversePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: createUniverse,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['universes'] });
      router.push('/universes');
    },
    onError: (err) => {
      setErrorMsg(err instanceof ApiError ? err.message : 'Unbekannter Fehler');
    },
  });

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <h1 className="text-2xl font-bold">Neues Universum</h1>
      <UniverseForm
        onSubmit={(data) => mutation.mutateAsync(data)}
        isSubmitting={mutation.isPending}
        error={errorMsg}
      />
    </div>
  );
}
