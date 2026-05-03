"""api/main.py の基本動作テスト（メタ・CORS・404）。

外部 API を叩かない範囲のスモークテスト。CLO 系の重い処理は別ファイルに分離。
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "logi-intel-dashboard-api"


def test_root_returns_doc_links() -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["docs"] == "/docs"
    assert body["openapi"] == "/openapi.json"


def test_openapi_schema_includes_clo_endpoints() -> None:
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    # 主要エンドポイントが OpenAPI スキーマに登録されている
    assert "/api/v1/clo/eligibility" in paths
    assert "/api/v1/clo/playbook" in paths
    assert "/api/v1/clo/plan-draft/{company_id}" in paths
    assert "/api/v1/clo/periodic-report/{company_id}" in paths
    assert "/api/v1/macro/overview" in paths
    assert "/api/v1/company/template" in paths
    assert "/api/v1/files/{file_path}" in paths


def test_swagger_ui_is_served() -> None:
    resp = client.get("/docs")
    assert resp.status_code == 200
    assert "swagger" in resp.text.lower()


def test_unknown_route_returns_404() -> None:
    resp = client.get("/api/v1/clo/nonexistent")
    assert resp.status_code == 404
