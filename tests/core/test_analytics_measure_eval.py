"""core/analytics/measure_eval.py の単体テスト。"""
from __future__ import annotations

from core.analytics.measure_eval import (
    _derive_available_resources,
    _score_compliance,
    _score_feasibility,
    _score_roi,
    _score_subsidy,
    build_eval_summary,
    evaluate_measures,
)
from core.playbook.measures import get_measure
from core.static.sample_company import get_sample

# ---- _score_roi ----


def test_score_roi_no_saving_returns_30() -> None:
    assert _score_roi(None, 1_000_000) == 30.0
    assert _score_roi(0, 1_000_000) == 30.0


def test_score_roi_high_ratio_returns_100() -> None:
    # 年 1 億円削減 / 投資 100 万円 = 100 倍 → 100点
    assert _score_roi(100_000_000, 1_000_000) == 100.0


def test_score_roi_low_ratio_returns_20() -> None:
    # 年 50 万円削減 / 投資 100 万円 = 0.5 倍 → 20点
    assert _score_roi(500_000, 1_000_000) == 20.0


def test_score_roi_monotonic() -> None:
    """投資固定で削減額が増えるとスコアは単調増加する。"""
    assert _score_roi(1_000_000, 1_000_000) <= _score_roi(2_000_000, 1_000_000)
    assert _score_roi(2_000_000, 1_000_000) <= _score_roi(5_000_000, 1_000_000)


# ---- _score_feasibility ----


def test_score_feasibility_easiest_is_100() -> None:
    assert _score_feasibility(1, []) == 100.0


def test_score_feasibility_hardest_is_20() -> None:
    assert _score_feasibility(5, []) == 20.0


def test_score_feasibility_missing_resources_penalty() -> None:
    base = _score_feasibility(2, [])
    with_missing = _score_feasibility(2, ["multi_site"])
    assert with_missing < base
    assert with_missing == base - 20.0


def test_score_feasibility_floor_zero() -> None:
    """難易度 5 で 5 リソース不足 → 0 点（負にはならない）。"""
    score = _score_feasibility(5, ["a", "b", "c", "d", "e"])
    assert score == 0.0


# ---- _score_compliance ----


def test_score_compliance_load_section_high() -> None:
    """積載率セクション施策 → 必須項目該当で 80 + 法令条文 20 = 100。"""
    m = get_measure("modal_shift_to_rail")
    assert m is not None
    score = _score_compliance(m, is_chain=False)
    assert score == 100.0


def test_score_compliance_chain_franchise_excludes_loading() -> None:
    """連鎖化事業者は荷役等セクションが必須でない → スコアが下がる。"""
    relay = get_measure("relay_transport")
    assert relay is not None
    non_chain = _score_compliance(relay, is_chain=False)
    chain = _score_compliance(relay, is_chain=True)
    assert chain < non_chain


# ---- _score_subsidy ----


def test_score_subsidy_zero_returns_zero() -> None:
    assert _score_subsidy([]) == 0.0


def test_score_subsidy_one_returns_50() -> None:
    assert _score_subsidy(["A"]) == 50.0


def test_score_subsidy_two_or_more_returns_100() -> None:
    assert _score_subsidy(["A", "B"]) == 100.0
    assert _score_subsidy(["A", "B", "C"]) == 100.0


# ---- _derive_available_resources ----


def test_derive_resources_manufacturing_sample() -> None:
    """製造業サンプル: 3 拠点 / 自社保有 12台 / dc 含む / 3 都道府県 → 全部入り。"""
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    resources = _derive_available_resources(profile)
    assert "it_capability" in resources
    assert "multi_site" in resources
    assert "fleet_owned" in resources
    assert "warehouse_management" in resources
    assert "long_distance_transport" in resources


def test_derive_resources_chain_no_owned_fleet() -> None:
    """連鎖化事業者は自社保有車両 0 → fleet_owned 含まれない。"""
    profile = get_sample("sample_chain_01")
    assert profile is not None
    resources = _derive_available_resources(profile)
    assert "fleet_owned" not in resources


# ---- evaluate_measures ----


def test_evaluate_returns_top_3_recommendations() -> None:
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    result = evaluate_measures(profile)
    assert len(result.top_recommendations) == 3
    # Top 3 は all_scored の先頭 3 件と一致
    assert result.top_recommendations == result.all_scored[:3]


def test_evaluate_top_recommendations_sorted_desc() -> None:
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    result = evaluate_measures(profile)
    scores = [s.total_score for s in result.top_recommendations]
    assert scores == sorted(scores, reverse=True)


def test_evaluate_chain_franchise_excludes_loading_high_score() -> None:
    """連鎖化事業者では荷役等セクション施策の compliance スコアが下がる。"""
    profile = get_sample("sample_chain_01")
    assert profile is not None
    result = evaluate_measures(profile)
    # 連鎖化事業者の Top 3 に「荷役等」セクションは入りにくい
    loading_in_top = any(
        s.measure.form3_section == "loading"
        for s in result.top_recommendations
    )
    # 必ずしも除外されないがスコア劣後すべき
    if loading_in_top:
        # 入っていても compliance スコアは load/wait より低い
        loading_scores = [
            s.compliance_score for s in result.top_recommendations
            if s.measure.form3_section == "loading"
        ]
        non_loading_scores = [
            s.compliance_score for s in result.top_recommendations
            if s.measure.form3_section != "loading"
        ]
        if non_loading_scores:
            assert max(loading_scores) <= max(non_loading_scores)


def test_evaluate_estimated_cost_saving_present_for_cost_reduction_measure() -> None:
    profile = get_sample("sample_wholesale_01")
    assert profile is not None
    result = evaluate_measures(profile)
    # load_factor_tms（cost_reduction_pct=24%）は試算値が出る
    score = next(
        (s for s in result.all_scored if s.measure.measure_id == "load_factor_tms"),
        None,
    )
    assert score is not None
    assert score.estimated_annual_cost_saving_jpy is not None
    assert score.estimated_annual_cost_saving_jpy > 0


def test_evaluate_visualization_baseline_low_roi_score() -> None:
    """前提施策（コスト削減効果なし）は ROI スコア 30 固定。"""
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    result = evaluate_measures(profile)
    score = next(
        (s for s in result.all_scored if s.measure.measure_id == "visualization_baseline"),
        None,
    )
    assert score is not None
    assert score.roi_score == 30.0


def test_evaluate_max_difficulty_filters_high_difficulty() -> None:
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    result = evaluate_measures(profile, max_difficulty=2)
    for s in result.all_scored:
        assert s.measure.implementation_difficulty <= 2


def test_evaluate_includes_citations() -> None:
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    result = evaluate_measures(profile)
    assert any("物流効率化法" in c.label for c in result.citations)


def test_evaluate_explicit_resources_overrides_derived() -> None:
    """available_resources を明示指定すると自動推定が上書きされる。"""
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    result = evaluate_measures(profile, available_resources=["it_capability"])
    # multi_site なし → load_factor_tms など multi_site 必須施策は missing_resources にあがる
    score = next(
        (s for s in result.all_scored if s.measure.measure_id == "load_factor_tms"),
        None,
    )
    assert score is not None
    assert "multi_site" in score.missing_resources


# ---- build_eval_summary ----


def test_build_eval_summary_includes_top_3_and_rationale() -> None:
    profile = get_sample("sample_mfg_01")
    assert profile is not None
    result = evaluate_measures(profile)
    text = build_eval_summary(result)
    assert "Top 3 推薦" in text
    assert "選定根拠" in text
    assert "全施策ランキング" in text
    # Top 3 の measure_id が含まれる
    for s in result.top_recommendations:
        assert s.measure.measure_id in text


def test_build_eval_summary_chain_franchise() -> None:
    profile = get_sample("sample_chain_01")
    assert profile is not None
    result = evaluate_measures(profile)
    text = build_eval_summary(result)
    assert "スマートマート" in text
    assert "chain_franchise" in text
