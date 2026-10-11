from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import requests

from backend.deployment.network_api.internet import has_internet_access


@pytest.mark.parametrize("results, expected, attempts", [
    ([200], True, 1),
    ([requests.ConnectionError("offline"), 401], True, 2),
    ([requests.Timeout("timed out"), requests.ConnectionError("offline")], False, 2),
    ([302, 503], False, 2),
    ([503, 401], True, 2),
])
def test_internet_probe_is_bounded_and_requires_expected_https_response(
    monkeypatch: pytest.MonkeyPatch, results: list[int | Exception], expected: bool,
    attempts: int,
) -> None:
    urls: list[str] = []
    responses: list[MagicMock] = []

    def head(url: str, *, timeout: tuple[int, int], allow_redirects: bool) -> MagicMock:
        assert url.startswith("https://")
        assert timeout == (2, 3)
        assert allow_redirects is False
        result = results[len(urls)]
        urls.append(url)
        if isinstance(result, Exception):
            raise result
        response = MagicMock()
        response.__enter__.return_value = SimpleNamespace(status_code=result)
        responses.append(response)
        return response

    monkeypatch.setattr("backend.deployment.network_api.internet.requests.head", head)

    assert has_internet_access() is expected
    assert len(urls) == attempts
    for response in responses:
        response.__exit__.assert_called_once()
