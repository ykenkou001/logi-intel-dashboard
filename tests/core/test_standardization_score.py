"""F2 標準化スコア (core/analytics/standardization_score.py) のテスト。

検証カバレッジ (plans/b-c-flickering-pixel.md §段階 c.6 F2):
    - 完全実装 (全 KPI 履歴 + 全施策 approved) で score ≥ 90
    - Override 5 件 unmanaged で penalty 25pt が単調反映
    - 未実装多数で coverage 低下 → score 30 以下
    - 単調性: unmanaged 0,1,2,5,10 で score 単調減少
    - approved_better_practice / required_localization は減点なし
    - temporary_exception は期限内なら減点なし、期限切れで -3pt
    - bonus: approved_better_practice >= 2 件で +5pt
    - サンプル4社で動作確認 (transport は ValueError)
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from core.analytics.standardization_score import (
    APPROVED_PRACTICE_BONUS,
    APPROVED_PRACTICE_BONUS_MIN_COUNT,
    EXPIRED_TEMPORARY_PENALTY_PER_ENTRY,
    UNMANAGED_PENALTY_PER_ENTRY,
    build_standardization_summary,
    compute_standardization_score,
)
from core.playbook.industry_packages import (
    CompanyPackageOverride,
    OverrideEntry,
    get_package,
)
from core.static.sample_company import (
    SAMPLE_CHAIN,
    SAMPLE_MANUFACTURING,
    SAMPLE_RETAIL,
    SAMPLE_WHOLESALE,
    CompanyProfile,
    KpiHistoryEntry,
)

_TODAY = date(2026, 5, 6)


def _profile_with_history(
    base: CompanyProfile, metric_ids: list[str],
) -> CompanyProfile:
    """指定 metric_id すべてに直近期 1 件分の履歴を持たせた profile を返す。"""
    return base.model_copy(update={
        "kpi_history": [
            KpiHistoryEntry(fy=2025, metric=mid, value=42.0, unit="%")
            for mid in metric_ids
        ],
    })


def _full_history(base: CompanyProfile) -> CompanyProfile:
    """base の業種パッケージの全 KPI に履歴を埋めた profile。"""
    pkg = get_package(_industry_of(base))
    assert pkg is not None
    return _profile_with_history(base, [k.metric_id for k in pkg.kpis])


def _full_implementation(
    base: CompanyProfile,
) -> tuple[CompanyProfile, CompanyPackageOverride]:
    """KPI 履歴 + 全施策 approved の coverage 100% 状態を作る。

    bonus が発火する (approved >= 2 件) ため score = 100 で clamp する。
    各テストはこれをベースに追加 override を差し込んで差分を観察する。
    """
    industry = _industry_of(base)
    pkg = get_package(industry)
    assert pkg is not None
    profile = _full_history(base)
    override = CompanyPackageOverride(
        company_id=profile.company_id,
        base_industry=industry,
        entries=[
            OverrideEntry(
                target_kind="measure",
                target_id=mid,
                category="approved_better_practice",
                rationale="自社実証で採用済",
                approved_by="山田CLO",
            )
            for mid in pkg.measure_ids
        ],
        last_reviewed=_TODAY,
    )
    return profile, override


def _industry_of(profile: CompanyProfile) -> str:
    from core.static.jsic import category_of
    cat = category_of(profile.jsic_code)
    assert cat is not None
    return cat


def _override_with_extra(
    base: CompanyPackageOverride,
    extra: list[OverrideEntry],
) -> CompanyPackageOverride:
    """既存 Override に entry を追加した copy を返す (frozen 維持)。"""
    return base.model_copy(update={"entries": [*base.entries, *extra]})


# ---------------------------------------------------------------------------
# 1. coverage 計算と境界条件
# ---------------------------------------------------------------------------


def test_no_history_no_override_returns_zero_coverage() -> None:
    profile = SAMPLE_MANUFACTURING.model_copy(update={"kpi_history": []})
    result = compute_standardization_score(profile, override=None, today=_TODAY)
    assert result.coverage_pct == 0.0
    # coverage 0 - penalty 0 + bonus 0 = 0、ただし min 0 で clamp
    assert result.score == 0.0
    assert result.deviation_count_unmanaged == 0
    assert result.deviation_count_total == 0
    # missing_kpi_ids にすべての KPI が並ぶ
    pkg = get_package("manufacturing")
    assert pkg is not None
    assert sorted(result.missing_kpi_ids) == sorted(k.metric_id for k in pkg.kpis)
    assert sorted(result.missing_measure_ids) == sorted(pkg.measure_ids)


def test_full_kpi_and_measure_yields_high_score() -> None:
    """全 KPI 履歴 + 全施策 approved で score >= 90 (HANDOFF 境界条件)。"""
    profile, override = _full_implementation(SAMPLE_MANUFACTURING)
    result = compute_standardization_score(profile, override, today=_TODAY)
    assert result.coverage_pct == 100.0
    assert result.score >= 90.0
    assert result.deviation_count_unmanaged == 0
    assert not result.missing_kpi_ids
    assert not result.missing_measure_ids


def test_partial_implementation_low_score() -> None:
    """KPI 履歴 1 件のみ + Override なしで coverage が低く score 30 以下。"""
    pkg = get_package("manufacturing")
    assert pkg is not None
    one_metric = pkg.kpis[0].metric_id
    profile = _profile_with_history(SAMPLE_MANUFACTURING, [one_metric])
    result = compute_standardization_score(profile, override=None, today=_TODAY)
    # 分母 = KPI 件数 + 施策件数 = 5 + 6 = 11、分子 = 1
    expected = 1.0 / (len(pkg.kpis) + len(pkg.measure_ids)) * 100.0
    assert result.coverage_pct == pytest.approx(expected, rel=0.01)
    assert result.score < 30.0


# ---------------------------------------------------------------------------
# 2. Override 4 分類の減点・加点
# ---------------------------------------------------------------------------


def test_unmanaged_deviation_penalty_per_entry() -> None:
    """unmanaged 5 件で coverage 100 から 25pt 減点 (単調性確認)。"""
    profile, base_override = _full_implementation(SAMPLE_MANUFACTURING)
    override = _override_with_extra(base_override, [
        OverrideEntry(
            target_kind="kpi",
            target_id=f"unmanaged_metric_{i}",
            category="unmanaged_deviation",
            rationale="計測体制不十分",
        )
        for i in range(5)
    ])
    result = compute_standardization_score(profile, override, today=_TODAY)
    assert result.deviation_count_unmanaged == 5
    # base coverage 100 + bonus 5 - penalty 25 = 80（clamp なし）
    expected = 100.0 + APPROVED_PRACTICE_BONUS - UNMANAGED_PENALTY_PER_ENTRY * 5
    expected = min(100.0, max(0.0, expected))
    assert result.score == pytest.approx(expected, abs=0.5)


def test_unmanaged_score_monotonic_decreasing() -> None:
    """unmanaged 件数 0,1,2,5,10 で score 単調減少 (HANDOFF 単調性)。

    coverage を低めの 50% 付近で固定し、bonus / clamp の影響を排除。
    """
    pkg = get_package("manufacturing")
    assert pkg is not None
    # KPI 履歴のみ（施策側 coverage は 0）→ coverage ≈ 45%
    profile = _full_history(SAMPLE_MANUFACTURING)
    scores: list[float] = []
    for n in (0, 1, 2, 5, 10):
        override = CompanyPackageOverride(
            company_id=profile.company_id,
            base_industry="manufacturing",
            entries=[
                OverrideEntry(
                    target_kind="kpi",
                    target_id=f"u_{i}",
                    category="unmanaged_deviation",
                    rationale="x",
                )
                for i in range(n)
            ],
            last_reviewed=_TODAY,
        )
        result = compute_standardization_score(profile, override, today=_TODAY)
        scores.append(result.score)
    # 厳密単調減少
    for i in range(1, len(scores)):
        assert scores[i] < scores[i - 1], (
            f"score 単調減少違反: scores={scores}"
        )


def test_approved_better_practice_does_not_penalize() -> None:
    """approved_better_practice の追加で score が下がらない。"""
    profile, base_override = _full_implementation(SAMPLE_MANUFACTURING)
    score_before = compute_standardization_score(
        profile, base_override, today=_TODAY,
    ).score
    override = _override_with_extra(base_override, [
        OverrideEntry(
            target_kind="kpi",
            target_id="extra_kpi",
            category="approved_better_practice",
            rationale="自社実証",
            approved_by="山田CLO",
            diff={"target_value": 50.0},
        ),
    ])
    result = compute_standardization_score(profile, override, today=_TODAY)
    assert result.deviation_count_unmanaged == 0
    assert result.score >= score_before


def test_required_localization_does_not_penalize() -> None:
    """required_localization の追加で score が下がらない。"""
    profile, base_override = _full_implementation(SAMPLE_WHOLESALE)
    score_before = compute_standardization_score(
        profile, base_override, today=_TODAY,
    ).score
    override = _override_with_extra(base_override, [
        OverrideEntry(
            target_kind="kpi",
            target_id="wait_time_avg_minutes",
            category="required_localization",
            rationale="郊外型小規模拠点",
            approved_by="山田CLO",
            diff={"target_value": 60.0},
        ),
    ])
    result = compute_standardization_score(profile, override, today=_TODAY)
    assert result.deviation_count_unmanaged == 0
    assert result.score >= score_before


def test_temporary_exception_active_does_not_penalize() -> None:
    """temporary_exception は期限内なら減点なし。"""
    profile, base_override = _full_implementation(SAMPLE_MANUFACTURING)
    score_before = compute_standardization_score(
        profile, base_override, today=_TODAY,
    ).score
    override = _override_with_extra(base_override, [
        OverrideEntry(
            target_kind="kpi",
            target_id="load_factor_pct",
            category="temporary_exception",
            rationale="新拠点立上げ",
            approved_by="山田CLO",
            expires_at=_TODAY + timedelta(days=30),
            diff={"target_value": 40.0},
        ),
    ])
    result = compute_standardization_score(profile, override, today=_TODAY)
    assert result.deviation_count_unmanaged == 0
    # 期限内 temporary_exception は減点しない → score は変わらない
    assert result.score >= score_before


def test_temporary_exception_expired_penalizes() -> None:
    """temporary_exception は期限切れで 3pt × 件数 減点。"""
    profile, base_override = _full_implementation(SAMPLE_MANUFACTURING)
    score_before = compute_standardization_score(
        profile, base_override, today=_TODAY,
    ).score
    override = _override_with_extra(base_override, [
        OverrideEntry(
            target_kind="kpi",
            target_id=f"m_{i}",
            category="temporary_exception",
            rationale="期限切れ",
            approved_by="山田CLO",
            expires_at=_TODAY - timedelta(days=1),
            diff={"target_value": 40.0},
        )
        for i in range(2)
    ])
    result = compute_standardization_score(profile, override, today=_TODAY)
    # base 100 で clamp していたが、3pt × 2 = 6pt 減点で
    # 100 + 5(bonus) - 6 = 99 に下がる（または減点後 clamp）
    expected = min(100.0, score_before + 0) - (
        EXPIRED_TEMPORARY_PENALTY_PER_ENTRY * 2
    )
    expected = max(0.0, min(100.0, expected))
    # base が clamp 100 だったので、減点後は 100 - 6 = 94 が目安だが、
    # clamp 前の生スコアは coverage 100 + bonus 5 - 6 = 99 のため
    # min(100, 99) = 99 になる。両方の場合をカバーする緩い条件で確認。
    assert result.score < score_before
    assert result.score >= max(0.0, expected - 1.0)


def test_approved_practice_bonus_fires_at_threshold() -> None:
    """approved_better_practice ≥ 2 件で +5pt (coverage 90 で 95 に)。"""
    pkg = get_package("manufacturing")
    assert pkg is not None
    # KPI 履歴を 1 件減らして coverage を下げる (満点回避)
    metrics = [k.metric_id for k in pkg.kpis][:-1]
    profile = _profile_with_history(SAMPLE_MANUFACTURING, metrics)
    override = CompanyPackageOverride(
        company_id=profile.company_id,
        base_industry="manufacturing",
        entries=[
            OverrideEntry(
                target_kind="kpi",
                target_id=f"k_{i}",
                category="approved_better_practice",
                rationale="自社実証",
                approved_by="山田CLO",
                diff={"target_value": 50.0},
            )
            for i in range(APPROVED_PRACTICE_BONUS_MIN_COUNT)
        ],
        last_reviewed=_TODAY,
    )
    result = compute_standardization_score(profile, override, today=_TODAY)
    # bonus 発火の確認: rationale に bonus +5pt が現れる
    assert any("bonus +5pt" in r for r in result.rationale)


def test_approved_practice_bonus_does_not_fire_below_threshold() -> None:
    """approved_better_practice 1 件では bonus 発火しない。"""
    profile = _full_history(SAMPLE_MANUFACTURING)
    override = CompanyPackageOverride(
        company_id=profile.company_id,
        base_industry="manufacturing",
        entries=[
            OverrideEntry(
                target_kind="kpi",
                target_id="load_factor_pct",
                category="approved_better_practice",
                rationale="自社実証",
                approved_by="山田CLO",
                diff={"target_value": 50.0},
            ),
        ],
        last_reviewed=_TODAY,
    )
    result = compute_standardization_score(profile, override, today=_TODAY)
    assert any("bonus +0pt" in r for r in result.rationale)


# ---------------------------------------------------------------------------
# 3. 施策実装ステータス判定 (Override の measure 採用)
# ---------------------------------------------------------------------------


def test_measure_adoption_via_approved_override() -> None:
    """Override target_kind=measure & approved → 採用済とみなし missing から除外。"""
    profile = _full_history(SAMPLE_MANUFACTURING)
    override = CompanyPackageOverride(
        company_id=profile.company_id,
        base_industry="manufacturing",
        entries=[
            OverrideEntry(
                target_kind="measure",
                target_id="load_factor_tms",
                category="approved_better_practice",
                rationale="TMS 導入完了",
                approved_by="山田CLO",
            ),
        ],
        last_reviewed=_TODAY,
    )
    result = compute_standardization_score(profile, override, today=_TODAY)
    assert "load_factor_tms" not in result.missing_measure_ids


def test_measure_unmanaged_does_not_count_as_implemented() -> None:
    """target_kind=measure でも unmanaged は採用済とみなさない。"""
    profile = _full_history(SAMPLE_MANUFACTURING)
    override = CompanyPackageOverride(
        company_id=profile.company_id,
        base_industry="manufacturing",
        entries=[
            OverrideEntry(
                target_kind="measure",
                target_id="load_factor_tms",
                category="unmanaged_deviation",
                rationale="導入計画なし",
            ),
        ],
        last_reviewed=_TODAY,
    )
    result = compute_standardization_score(profile, override, today=_TODAY)
    assert "load_factor_tms" in result.missing_measure_ids


# ---------------------------------------------------------------------------
# 4. 4 業種で動作 + 出典・鮮度警告
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "profile",
    [SAMPLE_MANUFACTURING, SAMPLE_WHOLESALE, SAMPLE_RETAIL, SAMPLE_CHAIN],
    ids=["manufacturing", "wholesale", "retail", "chain"],
)
def test_runs_for_all_sample_companies(profile: CompanyProfile) -> None:
    result = compute_standardization_score(profile, override=None, today=_TODAY)
    assert 0.0 <= result.score <= 100.0
    assert result.citations
    # 物流効率化法の citation が必ず含まれる
    assert any(
        "物流効率化法" in c.label or "物流" in c.label for c in result.citations
    )


def test_unsupported_industry_raises() -> None:
    """transport (ALL_PACKAGES に無い業種) は ValueError。"""
    profile = SAMPLE_MANUFACTURING.model_copy(update={"jsic_code": "4411"})
    with pytest.raises(ValueError, match="業種"):
        compute_standardization_score(profile, today=_TODAY)


def test_unknown_jsic_code_raises() -> None:
    """JSIC マスタに無いコードは ValueError。"""
    profile = SAMPLE_MANUFACTURING.model_copy(update={"jsic_code": "9999"})
    with pytest.raises(ValueError, match="業種"):
        compute_standardization_score(profile, today=_TODAY)


# ---------------------------------------------------------------------------
# 5. score 範囲 (0-100 clamp)
# ---------------------------------------------------------------------------


def test_score_clamps_to_zero_with_extreme_penalties() -> None:
    """大量 unmanaged (50 件) でも score は 0 で clamp される。"""
    profile = SAMPLE_MANUFACTURING.model_copy(update={"kpi_history": []})
    override = CompanyPackageOverride(
        company_id=profile.company_id,
        base_industry="manufacturing",
        entries=[
            OverrideEntry(
                target_kind="kpi",
                target_id=f"x_{i}",
                category="unmanaged_deviation",
                rationale="x",
            )
            for i in range(50)
        ],
        last_reviewed=_TODAY,
    )
    result = compute_standardization_score(profile, override, today=_TODAY)
    assert result.score == 0.0


def test_score_clamps_to_hundred_with_max_bonus() -> None:
    """coverage 100 + bonus 5 でも 100 で clamp される。"""
    profile, override = _full_implementation(SAMPLE_MANUFACTURING)
    result = compute_standardization_score(profile, override, today=_TODAY)
    assert result.score == 100.0


# ---------------------------------------------------------------------------
# 6. summary
# ---------------------------------------------------------------------------


def test_build_summary_contains_key_numbers() -> None:
    profile = _full_history(SAMPLE_MANUFACTURING)
    result = compute_standardization_score(profile, override=None, today=_TODAY)
    summary = build_standardization_summary(result)
    assert "標準化スコア" in summary
    assert f"{result.score:.1f}" in summary
