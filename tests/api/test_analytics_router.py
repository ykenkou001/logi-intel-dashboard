"""GA4 Measurement Protocol プロキシのスモークテスト。

GA4 を実際に叩かないことを保証する（httpx.AsyncClient.post を monkeypatch）。
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers import analytics

client = TestClient(app)


@pytest.fixture
def clear_ga_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv("GA4_MEASUREMENT_ID", raising=False)
    monkeypatch.delenv("GA4_API_SECRET", raising=False)
    yield


def test_collect_returns_204_when_ga_disabled(clear_ga_env: None) -> None:
    """GA4 環境変数が未設定の場合は 204 を返し、外部呼び出しもしない。"""
    resp = client.post(
        "/api/v1/analytics/collect",
        json={
            "client_id": "abc-123",
            "events": [{"name": "page_view", "params": {"page_location": "https://x.test/"}}],
        },
    )
    assert resp.status_code == 204
    assert resp.content == b""


def test_collect_rejects_invalid_payload() -> None:
    """client_id 欠落・events 空などは 422 を返す。"""
    resp = client.post("/api/v1/analytics/collect", json={"client_id": "abc"})
    assert resp.status_code == 422


def test_collect_strips_query_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """page_location の query string は GA4 へ渡る前に除去される。"""
    monkeypatch.setenv("GA4_MEASUREMENT_ID", "G-TEST")
    monkeypatch.setenv("GA4_API_SECRET", "secret")

    captured: dict[str, Any] = {}

    class _FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "_FakeClient":
            return self

        async def __aexit__(self, *args: Any) -> None:
            return None

        async def post(self, url: str, *, params: dict[str, Any], json: dict[str, Any]) -> Any:
            captured["url"] = url
            captured["params"] = params
            captured["json"] = json

            class _Resp:
                status_code = 204
                text = ""

            return _Resp()

    monkeypatch.setattr(analytics.httpx, "AsyncClient", _FakeClient)

    resp = client.post(
        "/api/v1/analytics/collect",
        json={
            "client_id": "abc-123",
            "events": [
                {
                    "name": "page_view",
                    "params": {
                        "page_location": "https://x.test/check?company=sensitive&token=secret",
                        "page_title": "対象判定",
                    },
                }
            ],
        },
    )
    assert resp.status_code == 204
    assert captured["params"] == {"measurement_id": "G-TEST", "api_secret": "secret"}
    sent_loc = captured["json"]["events"][0]["params"]["page_location"]
    assert sent_loc == "https://x.test/check"
    assert "company" not in sent_loc
    assert "token" not in sent_loc
