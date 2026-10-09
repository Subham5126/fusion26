import { useEffect, useState } from 'react';
import { getHealth } from '../api/client';
import type { HealthResponse } from '../types/contracts';

export type HealthConnection = { status: 'loading' } | { status: 'connected'; health: HealthResponse } | { status: 'failed'; message: string };

export function useHealthConnection() {
  const [connection, setConnection] = useState<HealthConnection>({ status: 'loading' });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setConnection({ status: 'loading' });
    getHealth(controller.signal).then(health => {
      if (!controller.signal.aborted) setConnection({ status: 'connected', health });
    }).catch((cause: unknown) => {
      if (!controller.signal.aborted) setConnection({ status: 'failed', message: cause instanceof Error ? cause.message : 'Health request failed' });
    });
    return () => controller.abort();
  }, [attempt]);
  return { connection, refresh: () => setAttempt(value => value + 1) };
}
