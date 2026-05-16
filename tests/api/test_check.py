"""`/api/v1/check` エンドポイントの統合テスト。

ToolResponse 構造と metadata.findings の構造を検証する。
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def _assert_tool_response_shape(body: dict[str, Any]) -> None:
    """ToolResponse 構造の必須キーを検証する。"""
    assert "summary" in body and isinstance(body["summary"], str)
    assert "files" in body and isinstance(body["files"], dict)
    assert "citations" in body and isinstance(body["citations"], list)
    assert "freshness_warnings" in body
    assert body["data_source"] in ("sample", "estimated", "actual")


def _base_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "industry": "other",
        "freight_tons_band": "lt_10k",
        "vehicles_band": "none",
        "warehouse_tons_band": "none",
        "clo_status": "not_considered",
        "is_chain_franchise": False,
    }
    payload.update(overrides)
    return payload


def test_check_endpoint_returns_tool_response_shape() -> None:
    """ベース入力で 200 + ToolResponse 構造を返す。"""
    resp = client.post("/api/v1/check", json=_base_payload())
    assert resp.status_code == 200, resp.text
    body = resp.json()
    _assert_tool_response_shape(body)


def test_check_endpoint_metadata_contains_findings() -> None:
    """metadata.findings が存在し、各 finding が必須キーを持つ。"""
    resp = client.post("/api/v1/check", json=_base_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert "metadata" in body and body["metadata"] is not None
    md = body["metadata"]
    assert "findings" in md
    assert "overall_verdict" in md
    assert "days_until_deadline" in md
    assert "submission_deadline" in md
    assert "enforcement_date" in md
    assert "penalty" in md
    for finding in md["findings"]:
        assert {"category", "verdict", "reason", "legal_article", "threshold_label"} <= set(
            finding.keys()
        )


def test_check_endpoint_shipper_applies_food_90k() -> None:
    """食品業 + 9 万トン以上 → 特定荷主 applies。"""
    resp = client.post(
        "/api/v1/check",
        json=_base_payload(industry="food", freight_tons_band="ge_90k"),
    )
    assert resp.status_code == 200
    md = resp.json()["metadata"]
    shipper = next(f for f in md["findings"] if f["category"] == "shipper")
    assert shipper["verdict"] == "applies"
    assert md["overall_verdict"] == "applies"


def test_check_endpoint_chain_franchise_applies() -> None:
    """連鎖化 + 売上 1,000 億 → 特定連鎖化事業者 applies。"""
    resp = client.post(
        "/api/v1/check",
        json=_base_payload(
            industry="chain_franchise",
            is_chain_franchise=True,
            annual_revenue_jpy=100_000_000_000,
        ),
    )
    assert resp.status_code == 200
    md = resp.json()["metadata"]
    chain = next(f for f in md["findings"] if f["category"] == "chain_franchise")
    assert chain["verdict"] == "applies"


def test_check_endpoint_warehouse_applies() -> None:
    """営業倉庫 70 万トン以上 → 特定倉庫業者 applies。"""
    resp = client.post(
        "/api/v1/check",
        json=_base_payload(warehouse_tons_band="ge_700k"),
    )
    assert resp.status_code == 200
    md = resp.json()["metadata"]
    warehouse = next(f for f in md["findings"] if f["category"] == "warehouse")
    assert warehouse["verdict"] == "applies"


def test_check_endpoint_freight_transport_applies() -> None:
    """保有車両 150 台以上 → 特定貨物自動車運送事業者等 applies。"""
    resp = client.post(
        "/api/v1/check",
        json=_base_payload(vehicles_band="ge_150"),
    )
    assert resp.status_code == 200
    md = resp.json()["metadata"]
    transport = next(
        f for f in md["findings"] if f["category"] == "freight_transport"
    )
    assert transport["verdict"] == "applies"


def test_check_endpoint_gray_zone_when_borderline() -> None:
    """5〜9 万トン帯 → 特定荷主 gray_zone + overall gray_zone。"""
    resp = client.post(
        "/api/v1/check",
        json=_base_payload(industry="food", freight_tons_band="50k_90k"),
    )
    md = resp.json()["metadata"]
    assert md["overall_verdict"] == "gray_zone"
    shipper = next(f for f in md["findings"] if f["category"] == "shipper")
    assert shipper["verdict"] == "gray_zone"


def test_check_endpoint_summary_includes_deadline_and_penalty() -> None:
    """summary に期限カウントダウン + 罰則情報が含まれる。"""
    resp = client.post("/api/v1/check", json=_base_payload())
    body = resp.json()
    assert "2026-10-31" in body["summary"]
    assert "100 万円" in body["summary"]
    # citations に国交省ポータルが含まれる
    urls = [c["url"] for c in body["citations"]]
    assert any("revised-logistics-act-portal.mlit.go.jp" in u for u in urls)


def test_check_endpoint_validation_error_on_invalid_industry() -> None:
    """未定義の industry → 422 バリデーションエラー。"""
    payload = _base_payload(industry="nonexistent")
    resp = client.post("/api/v1/check", json=payload)
    assert resp.status_code == 422


def test_check_endpoint_negative_revenue_rejected() -> None:
    """売上が負数 → 422 バリデーションエラー（ge=0 制約）。"""
    payload = _base_payload(annual_revenue_jpy=-1)
    resp = client.post("/api/v1/check", json=payload)
    assert resp.status_code == 422
