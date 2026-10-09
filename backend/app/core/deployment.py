"""Deployment settings only; scientific configuration and schemas are unchanged."""
import os
from urllib.parse import urlsplit

LOCAL_ORIGINS = [f'http://{host}:{port}' for port in (5173, 5174, 5190) for host in ('127.0.0.1', 'localhost')]

def frame_retention_bytes() -> int:
    value = os.getenv('ORBITTRACE_FRAME_RETENTION_MIB', '500')
    if not value.isascii() or not value.isdecimal() or not 1 <= int(value) <= 500:
        raise ValueError('ORBITTRACE_FRAME_RETENTION_MIB must be an integer between 1 and 500')
    return int(value) * 1024 * 1024

def public_mode() -> bool:
    return os.getenv('ORBITTRACE_PUBLIC_MODE', '0') == '1'

def cors_origins() -> list[str]:
    configured = os.getenv('ORBITTRACE_CORS_ORIGINS')
    if configured is None:
        if public_mode():
            raise ValueError('Public deployment requires ORBITTRACE_CORS_ORIGINS')
        return LOCAL_ORIGINS.copy()
    origins = []
    for value in configured.split(','):
        origin = value.strip().rstrip('/')
        parsed = urlsplit(origin)
        local = parsed.hostname in ('127.0.0.1', 'localhost', '::1')
        if (not parsed.hostname or '*' in parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment or
            (parsed.scheme != 'https' and not (parsed.scheme == 'http' and local and not public_mode()))):
            raise ValueError('CORS origins must be explicit HTTPS origins; local mode permits HTTP loopback')
        origins.append(origin)
    if not origins:
        raise ValueError('At least one CORS origin is required')
    return list(dict.fromkeys(origins))
