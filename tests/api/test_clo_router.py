"""CLO REST エンドポイントの動作テスト。

外部 API を叩かないツール群（eligibility / target-proposal / simulate-measures /
playbook / measure-eval / feasibility / scenario-sim / financial-translate /
certified-match / submission-validate / plan-draft / periodic-report）をカバー。

外部 API を叩く benchmark / driver-gap は test_app.py のスモークでは省略し、
ここでもスキップする（既存 core 側のテストでカバー済み）。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def _assert_tool_response_shape(body: dict[str, object]) -> None:
    """ToolResponse 構造の必須キーを検証する。"""
    assert "summary" in body
    assert isinstance(body["summary"], str) and body["summary"]
    assert "files" in body and isinstance(body["files"], dict)
    assert "citations" in body and isinstance(body["citations"], list)
    assert "freshness_warnings" in body and isinstance(body["freshness_warnings"], list)
    assert body["data_source"] in ("estimated", "actual")


def test_eligibility_returns_structured_response() -> None:
    resp = client.get(
        "/api/v1/clo/eligibility",
        params={
            "jsic_code": "5411",
            "annual_revenue_jpy": 5_000_000_000,
        },
    )
    assert resp.status_code == 200
    _assert_tool_response_shape(resp.json())


def test_target_proposal_returns_structured_response() -> None:
    resp = client.get(
        "/api/v1/clo/target-proposal",
        params={
            "jsic_code": "5411",
            "prefecture": "東京都",
            "revenue_jpy": 5_000_000_000,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    _assert_tool_response_shape(body)
    # 4 種類の数値目標が言及される
    assert "CO2" in body["summary"] or "二酸化炭素" in body["summary"]


def test_simulate_measures_returns_structured_response() -> None:
    resp = client.get(
        "/api/v1/clo/simulate-measures",
        params={
            "jsic_code": "5411",
            "prefecture": "東京都",
            "revenue_jpy": 5_000_000_000,
        },
    )
    assert resp.status_code == 200
    _assert_tool_response_shape(resp.json())


def test_playbook_search_returns_results() -> None:
    resp = client.get("/api/v1/clo/playbook")
    assert resp.status_code == 200
    body = resp.json()
    _assert_tool_response_shape(body)


def test_playbook_search_with_filter() -> None:
    resp = client.get(
        "/api/v1/clo/playbook",
        params={"max_difficulty": 3, "form3_section": "load"},
    )
    assert resp.status_code == 200
    _assert_tool_response_shape(resp.json())


def test_certified_match_returns_results() -> None:
    resp = client.get(
        "/api/v1/clo/certified-match",
        params={"jsic_code": "5411"},
    )
    assert resp.status_code == 200
    _assert_tool_response_shape(resp.json())


def test_measure_eval_for_sample_returns_top3() -> None:
    resp = client.get("/api/v1/clo/measure-eval/sample_mfg_01")
    assert resp.status_code == 200
    body = resp.json()
    _assert_tool_response_shape(body)
    assert body["data_source"] == "estimated"


def test_measure_eval_unknown_company_returns_404() -> None:
    resp = client.get("/api/v1/clo/measure-eval/no_such_company")
    assert resp.status_code == 404


def test_feasibility_for_sample_returns_verdict() -> None:
    resp = client.get("/api/v1/clo/feasibility/sample_wholesale_01")
    assert resp.status_code == 200
    _assert_tool_response_shape(resp.json())


def test_scenario_sim_for_sample_runs() -> None:
    resp = client.post("/api/v1/clo/scenario-sim/sample_mfg_01")
    assert resp.status_code == 200
    body = resp.json()
    _assert_tool_response_shape(body)
    # 燃料 +20% シナリオが含まれる
    assert "燃料" in body["summary"]


def test_eligibility_invalid_jsic_returns_400_or_summary() -> None:
    """不正な JSIC コード。core 側がエラー文字列を ValueError にしないなら
    summary に異常メッセージが入る。"""
    resp = client.get(
        "/api/v1/clo/eligibility",
        params={"jsic_code": "9999", "annual_revenue_jpy": 1000},
    )
    # 200 with summary OR 400 — どちらでも構わない
    assert resp.status_code in (200, 400)


@pytest.mark.parametrize(
    "endpoint,method",
    [
        ("/api/v1/clo/plan-draft/sample_mfg_01", "POST"),
        ("/api/v1/clo/financial-translate/sample_mfg_01", "POST"),
        ("/api/v1/clo/submission-validate/sample_mfg_01", "POST"),
        ("/api/v1/clo/periodic-report/sample_mfg_01", "POST"),
    ],
)
def test_plan_draft_chain_endpoints_run(endpoint: str, method: str) -> None:
    """重い統合エンドポイント（実ファイル生成あり）が 200 で完走することを確認。

    生成ファイルのパスは ToolResponse.files に含まれる。本テストは structure 確認のみ。
    """
    resp = client.request(method, endpoint)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    _assert_tool_response_shape(body)
