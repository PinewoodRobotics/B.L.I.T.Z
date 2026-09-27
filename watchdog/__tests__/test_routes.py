from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from pathlib import Path
from typing import cast

import pytest
from flask import Flask
from flask.testing import FlaskClient

from watchdog.monitor import ProcessMonitor
from watchdog.process_starter import OpenedProcess
from watchdog.routes.getters import GETTERS_BP
from watchdog.routes.setters import SETTERS_BP


WatchdogClient = tuple[FlaskClient, ProcessMonitor, Path, list["FakeProcess"]]


class FakeProcess:
    def __init__(self) -> None:
        self.alive = True

    def is_alive(self) -> bool:
        return self.alive

    def stop(self) -> None:
        self.alive = False


class FakeLoop:
    def call_soon_threadsafe(self, _callback: object, coroutine: object) -> None:
        cast(Coroutine[object, object, object], coroutine).close()


@pytest.fixture
def watchdog_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> WatchdogClient:
    config_path = tmp_path / "desired-config.txt"
    monitor = ProcessMonitor(
        str(tmp_path / "processes.json"),
        str(config_path),
        cast(asyncio.AbstractEventLoop, cast(object, FakeLoop())),
    )
    started: list[FakeProcess] = []

    def start_process(_process_type: str) -> OpenedProcess:
        process = FakeProcess()
        started.append(process)
        return cast(OpenedProcess, cast(object, process))

    monkeypatch.setattr(monitor, "start_process", start_process)

    app = Flask(__name__)
    app.register_blueprint(GETTERS_BP)
    app.register_blueprint(SETTERS_BP)
    app.config["SYSTEM_NAME"] = "test-pi"
    app.config["DESIRED_CONFIG_BASE64_FILE"] = str(config_path)
    app.extensions["process_monitor"] = monitor
    return app.test_client(), monitor, config_path, started


def test_config_endpoint_saves_config_and_rejects_invalid_payload(
    watchdog_client: WatchdogClient,
) -> None:
    client, monitor, config_path, _ = watchdog_client

    assert client.post("/set/config", json={"config": "YWJj"}).status_code == 400
    response = client.post("/set/config", json={"config_base64": "Y WJj$"})

    assert response.status_code == 200
    assert response.json == {"status": "success"}
    assert config_path.read_text() == "YWJj"
    assert monitor.is_config_exists


def test_start_process_endpoint_requires_config_and_starts_process(
    watchdog_client: WatchdogClient,
) -> None:
    client, monitor, _, started = watchdog_client

    assert client.post("/start/process", json={"process_types": "camera"}).status_code == 400
    assert client.post("/start/process", json={"process_types": ["camera"]}).status_code == 400
    client.post("/set/config", json={"config_base64": "YWJj"})

    response = client.post("/start/process", json={"process_types": ["camera"]})

    assert response.status_code == 200
    assert monitor.get_active_processes() == ["camera"]
    assert list(monitor.process_mem) == ["camera"]
    assert len(started) == 1


def test_set_processes_endpoint_replaces_process_plan(
    watchdog_client: WatchdogClient,
) -> None:
    client, monitor, _, started = watchdog_client

    assert client.post("/set/processes", json={"process_types": ["camera"]}).status_code == 400
    assert client.post("/set/processes", json={"process_types": [1]}).status_code == 400
    client.post("/set/config", json={"config_base64": "YWJj"})

    assert client.post("/set/processes", json={"process_types": ["camera"]}).status_code == 200
    assert monitor.get_active_processes() == ["camera"]
    assert list(monitor.process_mem) == ["camera"]

    assert client.post("/set/processes", json={"process_types": ["lidar"]}).status_code == 200
    assert monitor.get_active_processes() == ["lidar"]
    assert list(monitor.process_mem) == ["lidar"]
    assert not started[0].alive


def test_stop_process_endpoint_stops_requested_process(
    watchdog_client: WatchdogClient,
) -> None:
    client, monitor, _, started = watchdog_client
    client.post("/set/config", json={"config_base64": "YWJj"})
    client.post("/start/process", json={"process_types": ["camera"]})

    assert client.post("/stop/process", json={"process_types": [1]}).status_code == 400
    response = client.post("/stop/process", json={"process_types": ["camera"]})

    assert response.status_code == 200
    assert monitor.get_active_processes() == []
    assert list(monitor.process_mem) == []
    assert not started[0].alive


def test_stop_all_processes_endpoint_clears_running_processes(
    watchdog_client: WatchdogClient,
) -> None:
    client, monitor, _, started = watchdog_client
    client.post("/set/config", json={"config_base64": "YWJj"})
    client.post("/start/process", json={"process_types": ["camera", "lidar"]})

    response = client.post("/stop/all/processes")

    assert response.status_code == 200
    assert monitor.get_active_processes() == []
    assert list(monitor.process_mem) == []
    assert len(started) == 2
    assert all(not process.alive for process in started)


def test_system_status_endpoint_reports_watchdog_state(
    watchdog_client: WatchdogClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, monitor, _, _ = watchdog_client
    monkeypatch.setattr(monitor, "get_possible_processes", lambda: ["camera", "lidar"])
    client.post("/set/config", json={"config_base64": "YWJj"})
    client.post("/start/process", json={"process_types": ["camera"]})

    response = client.get("/get/system/status")

    assert response.status_code == 200
    assert response.json == {
        "status": "success",
        "system_info": "test-pi",
        "active_processes": ["camera"],
        "possible_processes": ["camera", "lidar"],
        "config_set": True,
    }
