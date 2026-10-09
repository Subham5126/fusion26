"""Fail closed before Railway upload; list and hash only reviewed application sources."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXACT = {'Dockerfile', '.dockerignore', '.railwayignore', 'pyproject.toml', 'backend/requirements.production.txt'}
PREFIXES = ('backend/app/', 'backend/orbittrace/', 'src/astrotrace/')
REQUIRED = {'backend/app/main.py', 'backend/app/core/server.py', 'backend/app/services/job_manager.py',
    'backend/orbittrace/pipeline.py', 'backend/orbittrace/cv_tracking.py',
    'backend/orbittrace/tracking/tracker.py', 'src/astrotrace/detection/optimized.py'} | EXACT


def main():
    paths = subprocess.check_output(['rg', '--files', '--hidden', '--no-ignore-vcs', '--ignore-file', '.railwayignore'],
        cwd=ROOT, text=True).splitlines()
    ignored = subprocess.run(['git', 'check-ignore', '--no-index', '--stdin'], input='\n'.join(paths) + '\n',
        cwd=ROOT, text=True, capture_output=True)
    if ignored.returncode not in (0, 1):
        raise RuntimeError(ignored.stderr)
    excluded = set(ignored.stdout.splitlines())
    paths = [p for p in paths if p not in excluded]
    tracked = set(subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines())
    records = []
    for name in sorted(paths):
        relative = name.replace('\\', '/')
        path = ROOT / name
        if relative not in EXACT and not (relative.startswith(PREFIXES) and path.suffix == '.py'):
            raise RuntimeError(f'Unexpected upload file: {relative}')
        if path.resolve() != path.absolute():
            raise RuntimeError(f'Symlink/reparse upload path: {relative}')
        data = path.read_bytes()
        if len(data) > 1024 * 1024:
            raise RuntimeError(f'Unexpected large source: {relative}')
        records.append({'path': relative, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'tracked': relative in tracked})
    missing = REQUIRED - {r['path'] for r in records}
    if missing:
        raise RuntimeError(f'Missing required upload files: {sorted(missing)}')
    evidence = {'root': str(ROOT), 'files': records, 'total_bytes': sum(r['bytes'] for r in records),
        'file_count': len(records), 'untracked_count': sum(not r['tracked'] for r in records),
        'note': 'Local audit using ripgrep ignore matching plus Git excludes; actual CLI retains Git ignoring.'}
    output = ROOT / '.cache/railway-v1/upload-manifest.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(f"Approved source audit: {evidence['file_count']} files, {evidence['total_bytes']} bytes, "
        f"{evidence['untracked_count']} untracked sources included; manifest {output}")


if __name__ == '__main__':
    main()
