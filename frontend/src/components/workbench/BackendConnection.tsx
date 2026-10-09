import { useHealthConnection } from '../../hooks/useHealthConnection';
import { Icon } from '../ui/Icon';

export function BackendConnection() {
  const { connection, refresh } = useHealthConnection();
  return <div className="backend-connection">
    <div role="status" aria-live="polite" className={`connection-${connection.status}`}><Icon name="activity" />
      <span>{connection.status === 'loading' ? 'Checking local service…' : connection.status === 'connected' ? `Connected · schema ${connection.health.schema_version}` : 'Local service unavailable'}
        <small>{connection.status === 'connected' ? connection.health.capabilities.analysis_api ? 'Synthetic analysis API advertised by backend' : 'Backend analysis API unavailable' : connection.status === 'failed' ? connection.message : 'Checking backend capabilities'}</small></span>
    </div>
    <button type="button" className="button button--quiet button--small" disabled={connection.status === 'loading'} onClick={refresh}>{connection.status === 'loading' ? 'Checking…' : 'Check connection'}</button>
  </div>;
}
