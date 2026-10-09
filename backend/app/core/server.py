"""Container entry point: one worker, platform-provided port, no working-directory dependency."""
import os
import sys
from collections.abc import Mapping


def server_command(environment: Mapping[str, str]) -> list[str]:
    value = environment.get('PORT', '8000')
    if not value.isascii() or not value.isdecimal() or not 1 <= int(value) <= 65535:
        raise ValueError('PORT must be an integer between 1 and 65535')
    return [sys.executable, '-I', '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0',
            '--port', str(int(value)), '--workers', '1', '--no-access-log']


def main() -> None:
    command = server_command(os.environ)
    os.execv(sys.executable, command)


if __name__ == '__main__':
    main()
