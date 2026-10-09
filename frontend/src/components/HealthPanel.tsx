import { useEffect, useState } from 'react';
import { getHealth } from '../api/client';
import type { HealthResponse } from '../types/contracts';

export function HealthPanel() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setHealth(null); setError(null);
    getHealth(controller.signal).then(setHealth).catch((cause: unknown) => {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Health request failed');
    });
    return () => controller.abort();
  }, [attempt]);
  return <section className="panel" aria-labelledby="health-heading">
    <div className="panel-heading"><h2 id="health-heading">Local service</h2>
      <button onClick={() => setAttempt(value => value + 1)}>Refresh health</button></div>
    <div role="status" aria-live="polite">
      {error ? <p className="error">Backend unavailable. Start the local backend, then refresh. {error}</p>
        : health ? <p className="connected">Connected · schema {health.schema_version} · bootstrap only</p>
        : <p>Checking backend…</p>}
    </div>
    {health && <ul className="capabilities">{Object.entries(health.capabilities).map(([name, available]) =>
      <li key={name}><span>{name.replaceAll('_', ' ')}</span>
        <span className={available ? 'ready' : 'pending'}>{available ? 'Available' : 'Pending'}</span></li>)}</ul>}
  </section>;
}
