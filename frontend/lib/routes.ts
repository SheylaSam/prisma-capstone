export const ROUTES = {
  dashboard: '/',
  universes: '/universes',
  rankings: '/rankings',
  factsheet: (runId: string, ticker: string) =>
    `/rankings/${runId}/stock/${ticker}` as const,
} as const;

export type Route = (typeof ROUTES)[keyof typeof ROUTES];
