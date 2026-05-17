"""CLO REST エンドポイントの動作テスト。

外部 API を叩かないツール群（eligibility / target-proposal / simulate-measures /
playbook / measure-eval / feasibility / scenario-sim / financial-translate /
certified-match / submission-validate / plan-draft / periodic-report）をカバー。

外部 API を叩く benchmark / driver-gap は test_app.py のスモークでは省略し、
ここでもスキップする（既存 core 側のテストでカバー済み）。
"""
from __future__ import annotations

from pathlib import Path

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
    assert body["data_source"] in ("sample", "estimated", "actual")


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


def test_wait_heatmap_returns_metadata_with_cells() -> None:
    """フェーズ4.1 a.1: 拠点別待機時間ヒートマップ。"""
    resp = client.get(
        "/api/v1/clo/wait-heatmap",
        params={"company_id": "sample_retail_01"},
    )
    assert resp.status_code == 200
    body = resp.json()
    _assert_tool_response_shape(body)
    # metadata に cells / site_names / time_slots が含まれる
    assert "metadata" in body
    md = body["metadata"]
    assert isinstance(md, dict)
    assert "cells" in md and len(md["cells"]) == 12  # 3 拠点 × 4 時間帯
    assert "site_names" in md and len(md["site_names"]) == 3
    assert "time_slots" in md and md["time_slots"] == ["morning", "midday", "evening", "night"]
    assert md["threshold_minutes"] == 120
    assert md["avg_target_minutes"] == 30
    # 関東地域DC・morning は yellow（42分・30分超）
    cell = next(
        c for c in md["cells"]
        if c["site_name"] == "関東地域DC" and c["time_slot"] == "morning"
    )
    assert cell["severity"] == "yellow"
    assert cell["avg_minutes"] == 42.0


def test_wait_heatmap_unknown_company_returns_404() -> None:
    resp = client.get(
        "/api/v1/clo/wait-heatmap",
        params={"company_id": "nonexistent_company_xyz"},
    )
    assert resp.status_code == 404


# ─── Tier S3: 施設マスタ + wait-heatmap?facility_id ───────────


def _facility_payload(
    *,
    facility_id: str = "fac_api_kanto",
    company_id: str = "sample_retail_01",
    site_name: str | None = "関東地域DC",
    is_consigned: bool = False,
) -> dict[str, object]:
    return {
        "facility_id": facility_id,
        "company_id": company_id,
        "name": "API テスト関東 DC",
        "address": "東京都江東区豊洲 1-1-1",
        "prefecture": "東京都",
        "industry_code": "5411",
        "site_name": site_name,
        "measurement_period": {
            "start_on": "2025-04-01",
            "end_on": "2026-03-31",
            "unit_label": "月次",
        },
        "measurement_conditions": ["パレット便のみ"],
        "exclusion_reasons": ["改修工事中除外"],
        "is_consigned_warehouse": is_consigned,
        "notes": None,
    }


def test_facility_round_trip_via_rest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST → GET /facilities の round trip。"""
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))

    payload = _facility_payload(facility_id="fac_rt", company_id="rt_company")
    post = client.post("/api/v1/clo/facilities", json=payload)
    assert post.status_code == 200
    body = post.json()
    _assert_tool_response_shape(body)
    assert body["metadata"]["action"] == "新規登録"

    got = client.get("/api/v1/clo/facilities", params={"company_id": "rt_company"})
    assert got.status_code == 200
    md = got.json()["metadata"]
    assert md["count"] == 1
    assert md["facilities"][0]["facility_id"] == "fac_rt"


def test_wait_heatmap_with_facility_id_filters_to_site(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """facility_id 指定で site_name 一致行のみ集計 + metadata に施設情報が乗る。"""
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))

    client.post(
        "/api/v1/clo/facilities",
        json=_facility_payload(
            facility_id="fac_kanto_only",
            company_id="sample_retail_01",
            site_name="関東地域DC",
        ),
    )

    resp = client.get(
        "/api/v1/clo/wait-heatmap",
        params={
            "company_id": "sample_retail_01",
            "facility_id": "fac_kanto_only",
        },
    )
    assert resp.status_code == 200
    md = resp.json()["metadata"]
    assert md["site_names"] == ["関東地域DC"]
    assert md["facility_id"] == "fac_kanto_only"
    assert "2025-04-01" in (md["measurement_period_label"] or "")
    # 関東のみ 4 時間帯 = 4 セル
    assert len(md["cells"]) == 4


def test_wait_heatmap_unknown_facility_id_returns_404(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    resp = client.get(
        "/api/v1/clo/wait-heatmap",
        params={
            "company_id": "sample_retail_01",
            "facility_id": "fac_never_registered",
        },
    )
    assert resp.status_code == 404


def test_facility_consigned_warehouse_emits_notice_in_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """寄託先フラグ True で consigned_notice が metadata に乗る。"""
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))

    client.post(
        "/api/v1/clo/facilities",
        json=_facility_payload(
            facility_id="fac_consigned",
            company_id="sample_retail_01",
            site_name="関東地域DC",
            is_consigned=True,
        ),
    )
    resp = client.get(
        "/api/v1/clo/wait-heatmap",
        params={
            "company_id": "sample_retail_01",
            "facility_id": "fac_consigned",
        },
    )
    assert resp.status_code == 200
    md = resp.json()["metadata"]
    assert md["is_consigned_warehouse"] is True
    assert "寄託先施設" in (md["consigned_notice"] or "")


def test_executive_brief_generates_three_slide_pptx() -> None:
    """フェーズ4.1 a.3: 3 スライド経営会議要約 PPT を REST で生成。"""
    resp = client.get("/api/v1/clo/executive-brief/sample_mfg_01")
    assert resp.status_code == 200
    body = resp.json()
    _assert_tool_response_shape(body)
    # files に pptx パスが含まれる
    assert "pptx" in body["files"]
    assert body["files"]["pptx"].endswith(".pptx") or "/" in body["files"]["pptx"]
    # summary に「やる」「やらない」セクション
    assert "やる" in body["summary"]
    assert "やらない" in body["summary"]


def test_today_decisions_returns_three_items_with_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """フェーズ4.5 b: デイリーコックピット 3 件 + metadata 構造化データ。"""
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    resp = client.get(
        "/api/v1/clo/today-decisions/sample_wholesale_01",
        params={"persist_snapshot": "false"},
    )
    assert resp.status_code == 200
    body = resp.json()
    _assert_tool_response_shape(body)
    assert "metadata" in body
    md = body["metadata"]
    assert isinstance(md, dict)
    # 3 件返る
    assert len(md["items"]) == 3
    # 各 item に anticipated_objections 3 件（attention_needed カードのみ厳格判定）
    for item in md["items"]:
        if item["card_state"] == "attention_needed":
            assert len(item["anticipated_objections"]) == 3
    # snapshot メタデータも入る
    assert "snapshot" in md
    assert md["snapshot"]["compliance_overall"] in (
        "compliant", "violation", "borderline", "not_measured",
    )
    assert md["overall_health"] in ("green", "yellow", "red")


def test_decisions_post_appends_to_jsonl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """フェーズ4.5 b.8: I2 意思決定ログへ 1 行 append。"""
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    resp = client.post(
        "/api/v1/clo/decisions/sample_wholesale_01",
        json={
            "cockpit_item_id": "compl_wait_max_violation_20260505",
            "decision": "adopt",
            "decided_by": "山田CLO",
            "rationale": "経営会議で承認",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["decision"] == "adopt"
    assert body["company_id"] == "sample_wholesale_01"
    assert "record_id" in body
    # jsonl ファイルに 1 行書き込まれる
    log_path = tmp_path / "decisions" / "sample_wholesale_01.jsonl"
    assert log_path.is_file()
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert "山田CLO" in lines[0]
    assert "adopt" in lines[0]


def test_decisions_post_unknown_company_returns_404(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    resp = client.post(
        "/api/v1/clo/decisions/nonexistent_company_xyz",
        json={
            "cockpit_item_id": "x",
            "decision": "pending",
        },
    )
    assert resp.status_code == 404


def test_executive_brief_unknown_company_returns_404() -> None:
    resp = client.get("/api/v1/clo/executive-brief/nonexistent_xyz")
    assert resp.status_code == 404


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
    assert body["data_source"] == "sample"


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


# ─── フェーズ5.0 c.7: 業種別パッケージ + F2 / J2 スコア REST ───────────


@pytest.mark.parametrize(
    "company_id,expected_industry",
    [
        ("sample_mfg_01", "manufacturing"),
        ("sample_wholesale_01", "wholesale"),
        ("sample_retail_01", "retail"),
        ("sample_chain_01", "chain_franchise"),
    ],
)
def test_industry_package_returns_metadata(
    company_id: str, expected_industry: str,
) -> None:
    """4 業種サンプルでパッケージが解決され metadata が含まれる。"""
    resp = client.get(f"/api/v1/clo/industry-package/{company_id}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    _assert_tool_response_shape(body)
    md = body["metadata"]
    assert md["base_industry"] == expected_industry
    assert "package" in md
    pkg = md["package"]
    assert pkg["category"] == expected_industry
    assert isinstance(pkg["kpis"], list) and len(pkg["kpis"]) >= 1
    assert isinstance(pkg["measure_ids"], list) and len(pkg["measure_ids"]) >= 1
    # サンプル profile は override 未保存なので None
    assert md["override"] is None


def test_industry_package_unknown_company_returns_404() -> None:
    resp = client.get("/api/v1/clo/industry-package/nonexistent_xyz")
    assert resp.status_code == 404


def test_standardization_score_returns_score_metadata() -> None:
    """F2 標準化スコアが score / coverage_pct / missing_* を含むメタデータを返す。"""
    resp = client.get("/api/v1/clo/standardization-score/sample_mfg_01")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    _assert_tool_response_shape(body)
    md = body["metadata"]
    assert md["company_id"] == "sample_mfg_01"
    assert md["base_package_category"] == "manufacturing"
    assert 0.0 <= md["score"] <= 100.0
    assert 0.0 <= md["coverage_pct"] <= 100.0
    assert isinstance(md["missing_kpi_ids"], list)
    assert isinstance(md["missing_measure_ids"], list)
    # サンプル profile は kpi_history 空で coverage 0
    assert md["coverage_pct"] == 0.0


def test_standardization_score_unknown_company_returns_404() -> None:
    resp = client.get("/api/v1/clo/standardization-score/nonexistent_xyz")
    assert resp.status_code == 404


def test_waste_traps_with_empty_body_returns_zero_items() -> None:
    """body 未指定（None）でも 200 で空件数が返る。"""
    resp = client.post(
        "/api/v1/clo/waste-traps/sample_mfg_01",
        json=None,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    _assert_tool_response_shape(body)
    md = body["metadata"]
    assert md["high_count"] == 0
    assert md["medium_count"] == 0
    assert md["low_count"] == 0
    assert md["items"] == []


def test_waste_traps_high_severity_with_freeze_recommendation() -> None:
    """high severity + wrong_kpi root_cause で投資凍結推奨が立つ。"""
    runs = [
        {
            "measure_id": "modal_shift_to_rail",
            "started_on": "2024-01-01",
            "invested_jpy": 100_000_000,
            "expected_effect_jpy": 300_000_000,
            "actual_effect_jpy": 20_000_000,
            "measured_count": 50,
            "data_completeness": 0.8,
            "seasonal_factor_active": False,
            "external_event_active": False,
            "payback_months_estimated": 12,
            "suspected_root_cause": "wrong_kpi",
        },
    ]
    resp = client.post(
        "/api/v1/clo/waste-traps/sample_mfg_01", json=runs,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    _assert_tool_response_shape(body)
    md = body["metadata"]
    assert md["high_count"] == 1
    assert md["investment_freeze_count"] == 1
    item = md["items"][0]
    assert item["trap_severity"] == "high"
    assert item["investment_freeze_recommended"] is True
    assert item["safeguard_triggered"] == []


def test_waste_traps_safeguard_pins_severity_to_low() -> None:
    """actual_effect_jpy=None でセーフガード発火 → low 固定 + freeze=False。"""
    runs = [
        {
            "measure_id": "modal_shift_to_rail",
            "started_on": "2025-10-01",
            "invested_jpy": 100_000_000,
            "expected_effect_jpy": 300_000_000,
            "actual_effect_jpy": None,
            "measured_count": 50,
            "data_completeness": 0.8,
            "payback_months_estimated": 12,
            "suspected_root_cause": "wrong_kpi",
        },
    ]
    resp = client.post(
        "/api/v1/clo/waste-traps/sample_mfg_01", json=runs,
    )
    assert resp.status_code == 200, resp.text
    md = resp.json()["metadata"]
    assert md["high_count"] == 0
    assert md["low_count"] == 1
    item = md["items"][0]
    assert item["trap_severity"] == "low"
    assert item["investment_freeze_recommended"] is False
    assert "actual_not_measured" in item["safeguard_triggered"]


def test_waste_traps_unknown_company_returns_404() -> None:
    resp = client.post(
        "/api/v1/clo/waste-traps/nonexistent_xyz", json=[],
    )
    assert resp.status_code == 404


# ─── フェーズ5.0 c.9: Web シナリオ E2E（4 業種で industry-package → standardization-score 連動）


@pytest.mark.parametrize(
    "company_id,expected_industry",
    [
        ("sample_mfg_01", "manufacturing"),
        ("sample_wholesale_01", "wholesale"),
        ("sample_retail_01", "retail"),
        ("sample_chain_01", "chain_franchise"),
    ],
)
def test_web_scenario_industry_package_and_score_consistency(
    company_id: str, expected_industry: str,
) -> None:
    """Web 画面が叩く 2 つのエンドポイントの整合性を 4 業種で保証する（c.9）。

    industry-package で得た base_industry / package と、
    standardization-score の base_package_category / missing_* が
    互いに矛盾しないことを保証する。フロントが両者を並列フェッチして
    差分テーブルを描画する用途を想定。
    """
    pkg_resp = client.get(f"/api/v1/clo/industry-package/{company_id}")
    score_resp = client.get(f"/api/v1/clo/standardization-score/{company_id}")
    assert pkg_resp.status_code == 200, pkg_resp.text
    assert score_resp.status_code == 200, score_resp.text

    pkg_md = pkg_resp.json()["metadata"]
    score_md = score_resp.json()["metadata"]

    # 業種は両者で一致
    assert pkg_md["base_industry"] == expected_industry
    assert score_md["base_package_category"] == expected_industry

    pkg = pkg_md["package"]
    pkg_kpi_ids = {k["metric_id"] for k in pkg["kpis"]}
    pkg_measure_ids = set(pkg["measure_ids"])

    # missing_kpi_ids / missing_measure_ids はパッケージのサブセット
    assert set(score_md["missing_kpi_ids"]).issubset(pkg_kpi_ids)
    assert set(score_md["missing_measure_ids"]).issubset(pkg_measure_ids)

    # スコア・カバレッジは 0-100 範囲、片方だけクランプも許容
    assert 0.0 <= score_md["coverage_pct"] <= 100.0
    assert 0.0 <= score_md["score"] <= 100.0
    # サンプルは Override 未保存（連鎖化追加減点 0）
    assert score_md["chain_franchise_loading_misuse_count"] == 0

    # サンプル Override 未保存のため、施策はすべて未採用 = pkg と一致
    assert sorted(score_md["missing_measure_ids"]) == sorted(pkg_measure_ids)


def test_web_scenario_chain_package_constraints_in_metadata() -> None:
    """連鎖化パッケージの metadata が c.8 強制ガードを満たす。

    loading 系施策が混入せず、様式第5 は第65条のみであることを確認する。
    """
    resp = client.get("/api/v1/clo/industry-package/sample_chain_01")
    assert resp.status_code == 200
    pkg = resp.json()["metadata"]["package"]

    # measure_ids に「loading」系の典型施策が混入しない
    forbidden = {"warehouse_dx_wms", "pallet_standardization", "relay_transport"}
    assert forbidden.isdisjoint(pkg["measure_ids"]), (
        f"連鎖化に loading 施策が混入: {pkg['measure_ids']}"
    )

    # KPI に handling_* プレフィックスが無い
    for kpi in pkg["kpis"]:
        assert not kpi["metric_id"].startswith("handling_"), (
            f"連鎖化に handling_* KPI が混入: {kpi['metric_id']}"
        )

    # 様式第5 レポートは第65条（第46条が混入しない）
    form5_reports = [r for r in pkg["reports"] if "様式第5" in r["name"]]
    assert len(form5_reports) >= 1
    for r in form5_reports:
        assert "第65条" in r["name"]
        assert "第46条" not in r["name"]


def test_web_scenario_standardization_score_metadata_includes_chain_misuse_field() -> None:
    """c.8 で追加した chain_franchise_loading_misuse_count が metadata に含まれる。

    Web TypeScript 型 (StandardizationScoreResult) との contract を保証する。
    """
    resp = client.get("/api/v1/clo/standardization-score/sample_chain_01")
    assert resp.status_code == 200
    md = resp.json()["metadata"]
    # 新フィールドが Pydantic から JSON に正しく出力される
    assert "chain_franchise_loading_misuse_count" in md
    assert md["chain_franchise_loading_misuse_count"] == 0


def test_web_scenario_summary_text_links_score_and_package() -> None:
    """summary テキストに業種パッケージ名と score の両方が現れる（Web 表示の整合性）。"""
    resp = client.get("/api/v1/clo/standardization-score/sample_mfg_01")
    body = resp.json()
    assert "標準化スコア" in body["summary"]
    # rationale に基準パッケージ名が記録される
    md = body["metadata"]
    assert any("基準パッケージ" in r for r in md["rationale"])
    assert any("製造業" in r for r in md["rationale"])


# ─── c.9 後追い: Web 可読性向上（measure_details / chain_franchise_notice）


@pytest.mark.parametrize(
    "company_id",
    ["sample_mfg_01", "sample_wholesale_01", "sample_retail_01", "sample_chain_01"],
)
def test_industry_package_metadata_includes_measure_details(company_id: str) -> None:
    """industry-package の metadata に施策の name / description / form3_section が含まれる。

    measure_id 単独表示は CLO 担当者に伝わらないため、Web 表示用に
    ALL_MEASURES から解決した詳細を同梱する。
    """
    resp = client.get(f"/api/v1/clo/industry-package/{company_id}")
    assert resp.status_code == 200
    md = resp.json()["metadata"]
    assert "measure_details" in md
    details = md["measure_details"]
    assert isinstance(details, list)
    pkg_measure_ids = set(md["package"]["measure_ids"])
    detail_ids = {d["measure_id"] for d in details}
    # measure_details は package.measure_ids を完全カバーする
    # （ALL_MEASURES に登録済の施策のみ採用しているため）
    assert detail_ids == pkg_measure_ids
    # 各エントリに name / description / form3_section / measure_type が含まれる
    for d in details:
        assert d["name"] and isinstance(d["name"], str)
        assert d["description"] and isinstance(d["description"], str)
        assert d["form3_section"] in ("load", "wait", "loading")


def test_industry_package_chain_franchise_notice_present() -> None:
    """連鎖化事業者では chain_franchise_notice が含まれ、第65条と荷役等対象外を含む。"""
    resp = client.get("/api/v1/clo/industry-package/sample_chain_01")
    assert resp.status_code == 200
    md = resp.json()["metadata"]
    notice = md.get("chain_franchise_notice")
    assert notice is not None
    assert notice["legal_article"] == "第65条"
    assert "第65条" in notice["headline"]
    assert "荷役等" in notice["scope_note"]


@pytest.mark.parametrize(
    "company_id",
    ["sample_mfg_01", "sample_wholesale_01", "sample_retail_01"],
)
def test_industry_package_chain_franchise_notice_absent_for_non_chain(
    company_id: str,
) -> None:
    """製造 / 卸 / 小売では chain_franchise_notice が None。"""
    resp = client.get(f"/api/v1/clo/industry-package/{company_id}")
    assert resp.status_code == 200
    md = resp.json()["metadata"]
    assert md.get("chain_franchise_notice") is None


def test_chain_franchise_measure_details_excludes_loading_section() -> None:
    """連鎖化の measure_details に form3_section='loading' が無い（c.8 強制ガード × c.9 表示）。"""
    resp = client.get("/api/v1/clo/industry-package/sample_chain_01")
    assert resp.status_code == 200
    details = resp.json()["metadata"]["measure_details"]
    for d in details:
        assert d["form3_section"] != "loading", (
            f"連鎖化に loading 系施策 {d['measure_id']} の詳細が含まれている"
        )
