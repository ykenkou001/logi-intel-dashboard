"""company ルーターのテンプレート生成・サンプル一覧テスト。

ファイルアップロード（POST /api/v1/company/load）は MCP ツール側の
test_io_company_loader でカバー済みのため、ここでは REST 経路のスモークのみ。
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_samples_returns_three_entries() -> None:
    resp = client.get("/api/v1/company/samples")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 3
    ids = {item["company_id"] for item in body}
    assert ids == {"sample_mfg_01", "sample_wholesale_01", "sample_chain_01"}


def test_template_generation_writes_xlsx() -> None:
    resp = client.post("/api/v1/company/template")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_source"] == "actual"
    assert "template_xlsx" in body["files"]
    # 生成パスが outputs/templates/ 配下を指している
    assert "templates" in body["files"]["template_xlsx"]


def test_load_rejects_non_xlsx() -> None:
    resp = client.post(
        "/api/v1/company/load",
        files={"file": ("foo.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400
    assert ".xlsx" in resp.json()["detail"]
