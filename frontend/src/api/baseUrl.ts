/** API origin is embedded by Vite at build time; an empty value retains the local proxy. */
export function resolveApiUrl(endpoint: string, base = ''): string {
  if (!/^\/api\/[A-Za-z0-9_/-]+$/.test(endpoint) || endpoint.includes('..') || endpoint.includes('//')) {
    throw new Error('Invalid OrbitTrace API path');
  }
  if (!base.trim()) return endpoint;
  const origin = new URL(base.trim());
  const loopback = ['localhost', '127.0.0.1', '[::1]'].includes(origin.hostname);
  if ((origin.protocol !== 'https:' && !(origin.protocol === 'http:' && loopback)) || origin.username || origin.password ||
      origin.pathname !== '/' || origin.search || origin.hash) {
    throw new Error('VITE_API_BASE_URL must be an HTTPS origin (HTTP is allowed only for loopback testing)');
  }
  return `${origin.origin}${endpoint}`;
}

export const apiUrl = (endpoint: string) => resolveApiUrl(endpoint, import.meta.env?.VITE_API_BASE_URL ?? '');
