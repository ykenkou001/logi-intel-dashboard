"""core/analytics/operation_cockpit.py のシナリオ網羅テスト（b.9 拡張）。

4 サンプル × 3 シナリオ = 12 ケースで build_daily_cockpit / build_cockpit_summary
の挙動をスナップショット fixture と突合。

シナリオ:
    - baseline             : profile そのまま
    - violation_added      : wait_time_rows[0].max_minutes を 150 に上書き
                             （違反確実発生）+ over_2h_count=1 で件数も整合
    - measurements_cleared : wait_time_rows / handling_time_rows / kpi_history を空
                             （未計測状態で軸 A が attention_needed/state_card に揺れるか確認）

スナップショット fixture:
    tests/fixtures/cockpit_summaries/<company_id>__<scenario>.txt

Fixture 更新:
    UPDATE_COCKPIT_SNAPSHOTS=1 uv run pytest \
        tests/core/test_analytics_operation_cockpit_scenarios.py
    fixture が無ければ作成、あれば上書き。差分は人手レビュー後コミット。

plan: plans/b-c-flickering-pixel.md §段階 b.9
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

import pytest

from core.analytics.operation_cockpit import (
    CockpitItem,
    CockpitResult,
    build_cockpit_summary,
    build_daily_cockpit,
)
from core.static.sample_company import (
    SAMPLE_CHAIN,
    SAMPLE_MANUFACTURING,
    SAMPLE_RETAIL,
    SAMPLE_WHOLESALE,
    CompanyProfile,
    WaitTimeRow,
)

_TODAY = date(2026, 5, 5)
_FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "cockpit_summaries"
_DATE_PATTERN = re.compile(r"\(\d{4}-\d{2}-\d{2}\)")
# 鮮度警告セクションは静的データ登録の有無（テスト実行順序）で揺れるため、
# スナップショット比較からは除外する（経過日数も日々ズレる）
_FRESHNESS_SECTION = re.compile(
    r"\n+【鮮度警告】.*\Z", re.DOTALL,
)
_UPDATE_SNAPSHOTS = os.environ.get("UPDATE_COCKPIT_SNAPSHOTS") == "1"

ScenarioName = Literal["baseline", "violation_added", "measurements_cleared"]
SCENARIOS: list[ScenarioName] = [
    "baseline",
    "violation_added",
    "measurements_cleared",
]


@dataclass(frozen=True)
class CaseId:
    """company_id × scenario を 1 つの ID にまとめる。pytest 表示用。"""

    company_id: str
    scenario: ScenarioName

    def __str__(self) -> str:
        return f"{self.company_id}__{self.scenario}"


_PROFILES: dict[str, CompanyProfile] = {
    SAMPLE_MANUFACTURING.company_id: SAMPLE_MANUFACTURING,
    SAMPLE_WHOLESALE.company_id: SAMPLE_WHOLESALE,
    SAMPLE_CHAIN.company_id: SAMPLE_CHAIN,
    SAMPLE_RETAIL.company_id: SAMPLE_RETAIL,
}

_ALL_CASES: list[CaseId] = [
    CaseId(company_id=cid, scenario=sc)
    for cid in _PROFILES
    for sc in SCENARIOS
]


# ---------------------------------------------------------------------------
# シナリオ生成ヘルパ
# ---------------------------------------------------------------------------


def _apply_scenario(
    profile: CompanyProfile, scenario: ScenarioName,
) -> CompanyProfile:
    """profile を base に scenario を適用した CompanyProfile を返す。

    Pydantic v2 model_copy(update=...) で frozen 性を保ちつつ差分適用する。
    """
    if scenario == "baseline":
        return profile

    if scenario == "violation_added":
        # 既存 wait_time_rows の最初の行を 150 分に書換。空なら 1 行追加
        if profile.wait_time_rows:
            head = profile.wait_time_rows[0]
            new_head = WaitTimeRow(
                bucket_label=head.bucket_label,
                measured_count=max(head.measured_count, 1),
                average_minutes=max(head.average_minutes, 60.0),
                max_minutes=150.0,
                over_2h_count=max(head.over_2h_count, 1),
                site_name=head.site_name,
                time_slot=head.time_slot,
            )
            new_rows = [new_head, *profile.wait_time_rows[1:]]
        else:
            new_rows = [WaitTimeRow(
                bucket_label="violation_added",
                measured_count=120,
                average_minutes=60.0,
                max_minutes=150.0,
                over_2h_count=3,
            )]
        return profile.model_copy(update={"wait_time_rows": new_rows})

    if scenario == "measurements_cleared":
        return profile.model_copy(update={
            "wait_time_rows": [],
            "handling_time_rows": [],
            "kpi_history": [],
        })

    raise AssertionError(f"unknown scenario: {scenario}")


# ---------------------------------------------------------------------------
# Fixtures（pytest）
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """LOGI_OUTPUTS_DIR を tmp_path に差替えて永続化を隔離する。"""
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))


def _build_for_case(case: CaseId) -> CockpitResult:
    profile = _apply_scenario(_PROFILES[case.company_id], case.scenario)
    return build_daily_cockpit(profile, today=_TODAY, persist_snapshot=False)


def _normalize_for_snapshot(text: str) -> str:
    """generated_at の日付を正規化し、鮮度警告セクションを除去する。

    - 日付（YYYY-MM-DD）→ __DATE__: build_daily_cockpit() は datetime.now(UTC) を
      使うため、タイムゾーン差で日付が前後しうる
    - 鮮度警告セクション全体を削除: テスト実行順序により _freshness レジストリの
      登録モジュール集合が変わり、警告メッセージ数が変動する。鮮度警告は
      静的データ更新タイミングに依存し、cockpit ロジックの決定論的出力ではない
    """
    normalized = _DATE_PATTERN.sub("(__DATE__)", text)
    return _FRESHNESS_SECTION.sub("", normalized).rstrip() + "\n"


def _fixture_path(case: CaseId) -> Path:
    return _FIXTURE_DIR / f"{case}.txt"


# ---------------------------------------------------------------------------
# 1. 共通インバリアント — 12 ケース全てで成立するべき性質
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", _ALL_CASES, ids=str)
def test_cockpit_returns_three_items_for_all_cases(case: CaseId) -> None:
    """4 社 × 3 シナリオ = 12 ケース全てで items は必ず 3 件。"""
    result = _build_for_case(case)
    assert len(result.items) == 3


@pytest.mark.parametrize("case", _ALL_CASES, ids=str)
def test_axis_priority_order_for_all_cases(case: CaseId) -> None:
    """軸 A → B → C の表示順を保つ。"""
    result = _build_for_case(case)
    axis_order = ["compliance", "kpi_reach", "measure_pick"]
    indices = [axis_order.index(i.decision_axis) for i in result.items]
    assert indices == sorted(indices)


@pytest.mark.parametrize("case", _ALL_CASES, ids=str)
def test_attention_cards_have_three_objections(case: CaseId) -> None:
    """attention_needed カードには想定反論が必ず 3 件付く（J4 薄版）。"""
    result = _build_for_case(case)
    for item in result.items:
        if item.card_state == "attention_needed":
            assert len(item.anticipated_objections) == 3, (
                f"{case} item {item.item_id}: "
                f"objections={len(item.anticipated_objections)}"
            )


@pytest.mark.parametrize("case", _ALL_CASES, ids=str)
def test_summary_contains_all_three_headlines(case: CaseId) -> None:
    """build_cockpit_summary の出力に 3 件の headline すべてが含まれる。"""
    result = _build_for_case(case)
    summary = build_cockpit_summary(result)
    for item in result.items:
        assert item.headline in summary, f"{case}: missing {item.headline!r}"


@pytest.mark.parametrize("case", _ALL_CASES, ids=str)
def test_measure_pick_capped_at_two(case: CaseId) -> None:
    """軸 C の上限は 2 件（plans b.5）。"""
    result = _build_for_case(case)
    measure_count = sum(
        1 for i in result.items if i.decision_axis == "measure_pick"
    )
    assert measure_count <= 2


@pytest.mark.parametrize("case", _ALL_CASES, ids=str)
def test_total_score_within_0_100(case: CaseId) -> None:
    """3 軸スコアと total_score が常に 0-100 範囲内。"""
    result = _build_for_case(case)
    for item in result.items:
        assert 0 <= item.urgency_score <= 100
        assert 0 <= item.impact_score <= 100
        assert 0 <= item.confidence_score <= 100
        assert 0 <= item.total_score <= 100


# ---------------------------------------------------------------------------
# 2. シナリオ別の挙動
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "company_id", list(_PROFILES.keys()),
    ids=lambda cid: cid,
)
def test_violation_added_forces_compliance_top(company_id: str) -> None:
    """violation_added シナリオでは items[0] が compliance 軸（軸 A 必須化）。"""
    case = CaseId(company_id=company_id, scenario="violation_added")
    result = _build_for_case(case)
    assert result.items[0].decision_axis == "compliance"
    # overall_health は red になるべき
    assert result.overall_health == "red"


@pytest.mark.parametrize(
    "company_id", list(_PROFILES.keys()),
    ids=lambda cid: cid,
)
def test_measurements_cleared_no_compliance_attention(company_id: str) -> None:
    """measurements_cleared シナリオでは荷待ち違反は発生せず（計測なしのため）、
    軸 A は attention_needed で出ない（state_card または出ない）。

    ただし提出期限直前等の他要因で軸 A が必須化される可能性があるため、
    今日の固定日（2026-05-05）では submission_risk=False 前提。
    """
    case = CaseId(company_id=company_id, scenario="measurements_cleared")
    result = _build_for_case(case)
    compliance_attention = [
        i for i in result.items
        if i.decision_axis == "compliance" and i.card_state == "attention_needed"
    ]
    assert len(compliance_attention) == 0, (
        f"{case}: 計測クリア後に compliance attention カードが出てしまった: "
        f"{[i.headline for i in compliance_attention]}"
    )


def test_chain_baseline_excludes_loading_section_in_measure_pick() -> None:
    """連鎖化事業者のサンプル baseline で軸 C に loading セクション施策が入らない。"""
    case = CaseId(company_id="sample_chain_01", scenario="baseline")
    result = _build_for_case(case)
    measure_items = [
        i for i in result.items if i.decision_axis == "measure_pick"
    ]
    # 各 measure_pick の measure_id が loading 系（warehouse_dx_wms 等）でないこと
    loading_ids = {"warehouse_dx_wms"}
    for item in measure_items:
        assert item.related_measure_id not in loading_ids, (
            f"連鎖化サンプルで loading 施策 {item.related_measure_id} が軸 C に混入"
        )


@pytest.mark.parametrize("case", _ALL_CASES, ids=str)
def test_baseline_data_source_is_sample_with_confidence_penalty(
    case: CaseId,
) -> None:
    """data_source='sample' のサンプル4社は confidence の base が 60 に。

    全 attention_needed カードで confidence ≤ 80 程度に収まる
    （base 60 ± 加点減点）。
    """
    result = _build_for_case(case)
    assert result.data_source == "sample"
    for item in result.items:
        if item.card_state == "attention_needed":
            assert item.confidence_score <= 80, (
                f"{case} {item.item_id}: confidence "
                f"{item.confidence_score} > 80（sample 制裁効いていない？）"
            )


@pytest.mark.parametrize("case", _ALL_CASES, ids=str)
def test_delta_keys_always_present(case: CaseId) -> None:
    """delta_from_yesterday は前日 snapshot 不在時でも全キーが存在し値は None。"""
    result = _build_for_case(case)
    expected_keys = {
        "load_factor_pct",
        "wait_time_avg_min",
        "wait_time_max_min",
        "handling_time_avg_min",
        "co2_intensity_g_per_tonkm",
    }
    assert set(result.delta_from_yesterday.keys()) == expected_keys
    assert all(v is None for v in result.delta_from_yesterday.values()), (
        f"{case}: 前日 snapshot 不在なのに delta に値あり: "
        f"{result.delta_from_yesterday}"
    )


# ---------------------------------------------------------------------------
# 3. スナップショット比較（人手レビュー一致を確認）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", _ALL_CASES, ids=str)
def test_summary_matches_snapshot(case: CaseId) -> None:
    """build_cockpit_summary の出力が tests/fixtures/cockpit_summaries/ と一致。

    UPDATE_COCKPIT_SNAPSHOTS=1 で再生成。差分は人手レビュー後コミット。
    """
    result = _build_for_case(case)
    actual = _normalize_for_snapshot(build_cockpit_summary(result))
    path = _fixture_path(case)

    if _UPDATE_SNAPSHOTS:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8")
        return

    if not path.is_file():
        pytest.fail(
            f"snapshot が存在しません: {path}\n"
            f"以下で再生成してください:\n"
            f"  UPDATE_COCKPIT_SNAPSHOTS=1 uv run pytest "
            f"tests/core/test_analytics_operation_cockpit_scenarios.py"
        )

    expected = path.read_text(encoding="utf-8")
    assert actual == expected, (
        f"\nスナップショット不一致: {case}\n"
        f"fixture: {path}\n"
        f"再生成するには:\n"
        f"  UPDATE_COCKPIT_SNAPSHOTS=1 uv run pytest "
        f"tests/core/test_analytics_operation_cockpit_scenarios.py\n"
        f"--- expected ---\n{expected}\n"
        f"--- actual ---\n{actual}\n"
    )


# ---------------------------------------------------------------------------
# 4. 個別 サンプル × シナリオ の重要観点
# ---------------------------------------------------------------------------


def test_wholesale_baseline_overall_health_red() -> None:
    """卸 baseline は荷待ち最大 137 分超（構造的に違反） → red。"""
    case = CaseId(company_id="sample_wholesale_01", scenario="baseline")
    result = _build_for_case(case)
    assert result.overall_health == "red"


def test_manufacturing_measurements_cleared_health_not_red() -> None:
    """製造業 計測クリアでは違反は発生しない（red にならない）。"""
    case = CaseId(company_id="sample_mfg_01", scenario="measurements_cleared")
    result = _build_for_case(case)
    assert result.overall_health != "red"


def test_violation_added_compliance_item_marks_wait_time() -> None:
    """violation_added の軸 A item は荷待ち時間関連を指す。"""
    for cid in _PROFILES:
        result = _build_for_case(CaseId(company_id=cid, scenario="violation_added"))
        compliance: CockpitItem = result.items[0]
        assert compliance.decision_axis == "compliance"
        assert compliance.related_compliance_item == "荷待ち時間"
        assert "違反" in compliance.headline
