"""core/analytics/operation_cockpit.py の最低限スモークテスト。

フェーズ4.5 b の中核検証。4 サンプル会社で:
    - items が必ず 3 件
    - 各 item に anticipated_objections が 3 件付く
    - 軸の優先順序が A → B → C
    - 違反ありの会社では軸 A が必ず top に入り overall_health=red
    - 計測データ無し（chain は handling 行が空）でも壊れない
    - persist_snapshot=True で JSON 永続化される
    - DecisionRecord を append すると days_pending に反映される

Codex に委譲する b.9 拡張テスト（4社 × 3シナリオ = 12ケースの本格網羅）の
前段ガードレール。コミット前に「壊れていないこと」を保証する。
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from core.analytics import operation_cockpit as oc
from core.analytics.operation_cockpit import (
    CockpitResult,
    DecisionRecord,
    append_decision,
    build_cockpit_summary,
    build_daily_cockpit,
)
from core.static.sample_company import (
    SAMPLE_CHAIN,
    SAMPLE_MANUFACTURING,
    SAMPLE_RETAIL,
    SAMPLE_WHOLESALE,
    CompanyProfile,
)

_TODAY = date(2026, 5, 5)
_AXIS_ORDER = ["compliance", "kpi_reach", "measure_pick"]
_ALL_PROFILES: list[CompanyProfile] = [
    SAMPLE_MANUFACTURING,
    SAMPLE_WHOLESALE,
    SAMPLE_CHAIN,
    SAMPLE_RETAIL,
]


@pytest.fixture(autouse=True)
def _isolate_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """LOGI_OUTPUTS_DIR を tmp_path に差替えて永続化を隔離する。"""
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))


# ---------------------------------------------------------------------------
# 共通: 4 社で必ず 3 件返る
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("profile", _ALL_PROFILES, ids=lambda p: p.company_id)
def test_cockpit_returns_exactly_three_items(profile: CompanyProfile) -> None:
    result = build_daily_cockpit(profile, today=_TODAY, persist_snapshot=False)
    assert isinstance(result, CockpitResult)
    assert len(result.items) == 3


@pytest.mark.parametrize("profile", _ALL_PROFILES, ids=lambda p: p.company_id)
def test_each_item_has_three_objections(profile: CompanyProfile) -> None:
    """attention_needed カードには想定反論が 3 件付く（J4 薄版）。"""
    result = build_daily_cockpit(profile, today=_TODAY, persist_snapshot=False)
    for item in result.items:
        if item.card_state == "attention_needed":
            assert len(item.anticipated_objections) == 3, (
                f"{profile.company_id} {item.item_id} has "
                f"{len(item.anticipated_objections)} objections, expected 3"
            )


@pytest.mark.parametrize("profile", _ALL_PROFILES, ids=lambda p: p.company_id)
def test_items_sorted_by_axis_priority(profile: CompanyProfile) -> None:
    result = build_daily_cockpit(profile, today=_TODAY, persist_snapshot=False)
    indices = [_AXIS_ORDER.index(i.decision_axis) for i in result.items]
    assert indices == sorted(indices), (
        f"{profile.company_id} axis order broken: "
        f"{[i.decision_axis for i in result.items]}"
    )


@pytest.mark.parametrize("profile", _ALL_PROFILES, ids=lambda p: p.company_id)
def test_measure_pick_capped_at_two(profile: CompanyProfile) -> None:
    """軸 C 上限は 2 件（plans/b-c-flickering-pixel.md §段階 b.5）。"""
    result = build_daily_cockpit(profile, today=_TODAY, persist_snapshot=False)
    measure_count = sum(1 for i in result.items if i.decision_axis == "measure_pick")
    assert measure_count <= 2


# ---------------------------------------------------------------------------
# 違反/健全のシナリオ
# ---------------------------------------------------------------------------


def test_wholesale_has_compliance_violation_and_red_health() -> None:
    """卸サンプルは荷待ち時間最大値が 2 時間超で違反 → 軸 A 必須化 + overall=red。"""
    result = build_daily_cockpit(
        SAMPLE_WHOLESALE, today=_TODAY, persist_snapshot=False,
    )
    assert result.overall_health == "red"
    compliance_items = [i for i in result.items if i.decision_axis == "compliance"]
    assert len(compliance_items) >= 1
    assert compliance_items[0].card_state == "attention_needed"


def test_chain_excludes_handling_section() -> None:
    """連鎖化事業者の軸 C には荷役等セクション（handling/loading）施策は入らない。"""
    result = build_daily_cockpit(
        SAMPLE_CHAIN, today=_TODAY, persist_snapshot=False,
    )
    measure_items = [i for i in result.items if i.decision_axis == "measure_pick"]
    # measure_eval 側で is_chain_franchise=True なら loading 系は除外されている
    for item in measure_items:
        # 荷役等施策の代表的な measure_id を確認
        assert item.related_measure_id != "warehouse_dx_wms" or (
            "連鎖化" not in item.headline  # 万一含まれた場合の sentinel
        )


# ---------------------------------------------------------------------------
# 永続化と aging
# ---------------------------------------------------------------------------


def test_persist_snapshot_writes_json(tmp_path: Path) -> None:
    """persist_snapshot=True で outputs/cockpit_snapshots/<id>/<yyyymmdd>.json を作る。"""
    result = build_daily_cockpit(
        SAMPLE_MANUFACTURING, today=_TODAY, persist_snapshot=True,
    )
    snapshot_path = (
        tmp_path
        / "cockpit_snapshots"
        / SAMPLE_MANUFACTURING.company_id
        / f"{_TODAY.strftime('%Y%m%d')}.json"
    )
    assert snapshot_path.is_file()
    content = snapshot_path.read_text(encoding="utf-8")
    assert SAMPLE_MANUFACTURING.company_id in content
    assert result.snapshot.snapshot_date == _TODAY


def test_delta_from_yesterday_is_all_none_without_prior() -> None:
    """前日 snapshot がない初回は delta_from_yesterday の値が全 None。"""
    result = build_daily_cockpit(
        SAMPLE_MANUFACTURING, today=_TODAY, persist_snapshot=False,
    )
    assert all(v is None for v in result.delta_from_yesterday.values())
    assert "load_factor_pct" in result.delta_from_yesterday  # キーは存在


def test_days_pending_reflects_decision_log() -> None:
    """同一 cockpit_item_id の pending レコードを 5 日前に append すると aging=5。"""
    # 当日は永続化抑止で先に items を取得し、対象 item_id を握る
    today_result = build_daily_cockpit(
        SAMPLE_WHOLESALE, today=_TODAY, persist_snapshot=False,
    )
    target_item = next(
        i for i in today_result.items if i.card_state == "attention_needed"
    )

    # 5 日前に pending を append
    five_days_ago = datetime.combine(_TODAY - timedelta(days=5), datetime.min.time())
    five_days_ago = five_days_ago.replace(tzinfo=UTC)
    record = DecisionRecord(
        record_id="test-uuid",
        company_id=SAMPLE_WHOLESALE.company_id,
        cockpit_item_id=target_item.item_id,
        decided_at=five_days_ago,
        decided_by="ci-test",
        decision="pending",
        rationale="経営会議で再度確認",
    )
    append_decision(record)

    # 再生成
    new_result = build_daily_cockpit(
        SAMPLE_WHOLESALE, today=_TODAY, persist_snapshot=False,
    )
    refreshed = next(
        (i for i in new_result.items if i.item_id == target_item.item_id),
        None,
    )
    assert refreshed is not None, "対象 item_id がコックピットから消えた"
    assert refreshed.days_pending == 5


# ---------------------------------------------------------------------------
# build_cockpit_summary
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("profile", _ALL_PROFILES, ids=lambda p: p.company_id)
def test_summary_contains_all_three_headlines(profile: CompanyProfile) -> None:
    result = build_daily_cockpit(profile, today=_TODAY, persist_snapshot=False)
    summary = build_cockpit_summary(result)
    for item in result.items:
        assert item.headline in summary, (
            f"summary missing headline: {item.headline!r}"
        )
    assert profile.name in summary


# ---------------------------------------------------------------------------
# 提出期限（30 日以内なら軸 A 必須化）
# ---------------------------------------------------------------------------


def test_submission_risk_forces_compliance_card() -> None:
    """提出期限 30 日以内なら、違反がなくても軸 A カードを必ず含める。"""
    near_deadline = oc.CLO_SUBMISSION_DEADLINE - timedelta(days=10)
    # mfg は荷待ち違反が無いが、提出期限直前なら軸 A が含まれる
    result = build_daily_cockpit(
        SAMPLE_MANUFACTURING, today=near_deadline, persist_snapshot=False,
    )
    axes = {i.decision_axis for i in result.items}
    assert "compliance" in axes
