"""Verify platform port use and one-process/one-worker command semantics."""
import sys
import pytest
from app.core.server import server_command


def test_platform_port_is_used_without_local_path_dependency():
    command = server_command({'PORT': '18765'})
    assert command[:5] == [sys.executable, '-I', '-m', 'uvicorn', 'app.main:app']
    assert command[command.index('--port') + 1] == '18765'
    assert command[command.index('--host') + 1] == '0.0.0.0'
    assert command[command.index('--workers') + 1] == '1'


def test_default_port_preserves_existing_container_behavior():
    command = server_command({})
    assert command[command.index('--port') + 1] == '8000'


@pytest.mark.parametrize('port', ['', '0', '65536', '-1', '12.5', '80;echo secret', ' 8000 ', '８０００'])
def test_invalid_platform_ports_fail_before_server_start(port):
    with pytest.raises(ValueError, match='PORT must be an integer'):
        server_command({'PORT': port})
