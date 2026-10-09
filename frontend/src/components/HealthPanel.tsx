import { useHealthConnection } from '../hooks/useHealthConnection';

export function HealthPanel() {
  const { connection, refresh } = useHealthConnection();
  const health = connection.status === 'connected' ? connection.health : null;
  return <section className="panel" aria-labelledby="health-heading">
    <div className="panel-heading"><h2 id="health-heading">Local service</h2>
      <button onClick={refresh} disabled={connection.status === 'loading'}>Refresh health</button></div>
    <div role="status" aria-live="polite">
      {connection.status === 'failed' ? <p className="error">Backend unavailable. Start the local backend, then refresh. {connection.message}</p>
        : health ? <p className="connected">Connected · schema {health.schema_version} · bootstrap only</p>
        : <p>Checking backend…</p>}
    </div>
    {health && <ul className="capabilities">{Object.entries(health.capabilities).map(([name, available]) =>
      <li key={name}><span>{name.replaceAll('_', ' ')}</span>
        <span className={available ? 'ready' : 'pending'}>{available ? 'Available' : 'Pending'}</span></li>)}</ul>}
  </section>;
}
