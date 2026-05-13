import { apiFetch } from './client';

export type Universe = {
  id: string;
  name: string;
  tickers: string[];
  region: string;
};

export type CreateUniverseInput = {
  name: string;
  tickers: string[];
  region: string;
};

export function listUniverses(): Promise<Universe[]> {
  return apiFetch<Universe[]>('/api/v1/universes');
}

export function createUniverse(input: CreateUniverseInput): Promise<Universe> {
  return apiFetch<Universe>('/api/v1/universes', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}
