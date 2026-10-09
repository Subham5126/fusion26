import { useHealthConnection } from '../../hooks/useHealthConnection';
import { Icon } from '../ui/Icon';

export function BackendConnection() {
  const { connection, refresh } = useHealthConnection();
  return <div className={`backend-connection backend-connection--compact connection-${connection.status}`}>
    <div role="status" aria-live="polite" className={`connection-${connection.status}`}><Icon name="activity" />
      <span>{connection.status === 'loading' ? 'Checking backend…' : connection.status === 'connected' ? 'Backend connected' : 'Backend unavailable'}
        <small>{connection.status === 'connected' ? `Schema ${connection.health.schema_version} · ${connection.health.capabilities.analysis_api ? 'Analysis API advertised' : 'Analysis API unavailable'}` : connection.status === 'failed' ? connection.message : 'Reading service health'}</small></span>
    </div>
    <button type="button" className="button button--quiet button--small connection-check" aria-label={connection.status === 'loading' ? 'Checking backend connection' : 'Check connection'} title="Check backend connection" disabled={connection.status === 'loading'} onClick={refresh}><Icon name="restart" /><span className="connection-check-label">{connection.status === 'loading' ? 'Checking…' : 'Check connection'}</span></button>
  </div>;
}
