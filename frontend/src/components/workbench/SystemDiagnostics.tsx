import { useHealthConnection } from '../../hooks/useHealthConnection';
import { emptyResult } from '../../fixtures/empty-result';
import { Icon } from '../ui/Icon';

interface SystemDiagnosticsProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export function SystemDiagnostics({ isOpen = true, onClose }: SystemDiagnosticsProps) {
  const { connection, refresh } = useHealthConnection();
  const health = connection.status === 'connected' ? connection.health : null;

  if (!isOpen) return null;

  return (
    <section
      id="system-diagnostics"
      className="system-diagnostics-drawer"
      aria-labelledby="system-diagnostics-heading"
    >
      <div className="system-diagnostics-header">
        <div className="system-diagnostics-title-group">
          <p className="eyebrow"><span className="status-dot" />SYSTEM READINESS & DIAGNOSTICS</p>
          <h2 id="system-diagnostics-heading">Telemetry & Subsystem Verification</h2>
          <p className="system-diagnostics-lead">
            Live backend connectivity, schema contracts, and active subsystem boundaries.
          </p>
        </div>
        <div className="system-diagnostics-header-actions">
          <button
            type="button"
            className="button button--quiet button--small"
            onClick={refresh}
            disabled={connection.status === 'loading'}
            aria-label="Refresh service health"
          >
            <Icon name="restart" />
            <span>{connection.status === 'loading' ? 'Checking…' : 'Check connection'}</span>
          </button>
          {onClose && (
            <button
              type="button"
              className="button button--quiet button--small close-diagnostics"
              onClick={onClose}
              aria-label="Close diagnostics panel"
            >
              <Icon name="close" />
              <span>Close</span>
            </button>
          )}
        </div>
      </div>

      <p className="notice">
        Candidate identity and physical orbit remain unverified. Synthetic processing does not establish performance on real observations.
      </p>

      <div className="diagnostics-grid">
        <div className="diagnostics-panel">
          <div className="panel-heading">
            <h3>Backend Health & Capabilities</h3>
            <span className={`status-badge status-badge--${connection.status}`}>
              {connection.status === 'connected' ? 'Connected' : connection.status === 'failed' ? 'Unavailable' : 'Checking'}
            </span>
          </div>

          <div role="status" aria-live="polite" className="connection-readout">
            {connection.status === 'failed' ? (
              <p className="error">Backend unavailable. Start the local backend, then refresh. {connection.message}</p>
            ) : health ? (
              <p className="connected">
                Connected · schema {health.schema_version} · readiness: <code>{health.readiness}</code>
              </p>
            ) : (
              <p>Checking backend…</p>
            )}
          </div>

          {health && (
            <div className="capabilities-group">
              <span className="capabilities-group-title">Advertised backend capabilities</span>
              <ul className="capabilities">
                {Object.entries(health.capabilities).map(([name, available]) => (
                  <li key={name}>
                    <span>{name.replaceAll('_', ' ')}</span>
                    <span className={available ? 'ready' : 'pending'}>
                      {available ? 'Available' : 'Pending'}
                    </span>
                  </li>
                ))}
              </ul>
              <p className="health-context">
                Capabilities reported by backend health response. Availability does not certify performance or scientific calibration.
              </p>
            </div>
          )}
        </div>

        <div className="diagnostics-panel">
          <div className="panel-heading">
            <h3>Application Capabilities</h3>
            <span className="status-badge status-badge--info">Subsystem status</span>
          </div>
          <ul className="application-capabilities">
            <li>
              <div>
                <strong>Local observation viewer</strong>
                <p>Ordered images, playback, zoom, pan and pixel coordinates.</p>
              </div>
              <span className="ready">Implemented</span>
            </li>
            <li>
              <div>
                <strong>Synthetic Analysis</strong>
                <p>Job submission, polling, results, manifests, frames and aligned overlays. Requires the backend.</p>
              </div>
              <span className="ready">Integrated</span>
            </li>
            <li>
              <div>
                <strong>Local image analysis</strong>
                <p>The frontend upload workflow and registration handling are pending.</p>
              </div>
              <span className="pending">Pending</span>
            </li>
            <li>
              <div>
                <strong>Scientific exports</strong>
                <p>JSON and CSV downloads are not connected yet.</p>
              </div>
              <span className="pending">Pending</span>
            </li>
          </ul>
        </div>
      </div>

      <div className="diagnostics-fixture">
        <div className="panel-heading">
          <h3>Illustrative schema fixture (Contract 0.1.0)</h3>
        </div>
        <p className="fixture-explainer">
          This empty example documents the result shape authored for development and testing. It is not a detector output or benchmark.
        </p>
        <details>
          <summary>Inspect example JSON · schema 0.1.0</summary>
          <pre>{JSON.stringify(emptyResult, null, 2)}</pre>
        </details>
      </div>

      <p className="readiness-footnote">
        CPU first · Native image coordinates · Pixels/frame when timestamps are unknown
      </p>
    </section>
  );
}
