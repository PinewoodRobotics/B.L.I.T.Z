from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('user', ['ubuntu', 'robot'])
def test_watchdog_service_uses_selected_user(tmp_path: Path, user: str) -> None:
    commands = tmp_path / 'bin'
    commands.mkdir()
    for name, code in [('sudo', '#!/bin/bash\nexec "$@"\n'), ('systemctl', '#!/bin/bash\nexit 0\n')]:
        command = commands / name
        command.write_text(code)
        command.chmod(0o755)
    unit = tmp_path / 'watchdog.service'
    environment = dict(os.environ, PATH=f'{commands}:{os.environ["PATH"]}',
        SERVICE_USER=user, SERVICE_UNIT_SOURCE=str(ROOT / 'ops/systemd/watchdog.service'),
        SERVICE_UNIT_PATH=str(unit))
    subprocess.run(['bash', str(ROOT / 'scripts/bootstrap/install_service.sh')], env=environment, check=True)
    assert f'User={user}\n' in unit.read_text()
    assert 'EnvironmentFile=/etc/default/blitz' in unit.read_text()


def test_service_rejects_invalid_user_before_install(tmp_path: Path) -> None:
    result = subprocess.run(['bash', str(ROOT / 'scripts/bootstrap/install_service.sh')],
        env=dict(os.environ, SERVICE_USER='bad/user', SERVICE_UNIT_SOURCE='unused'),
        capture_output=True, text=True)
    assert result.returncode != 0
    assert 'Invalid SERVICE_USER' in result.stderr
