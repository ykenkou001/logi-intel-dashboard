"""core/analytics/wait_time_heatmap.py の単体テスト。"""
from __future__ import annotations

from core.analytics.wait_time_heatmap import (
    HeatmapResult,
    _classify_severity,
    build_wait_time_heatmap,
)
from core.static.sample_company import (
    SAMPLE_CHAIN,
    SAMPLE_MANUFACTURING,
    CompanyProfile,
    CompanySite,
    WaitTimeRow,
    get_sample,
)


def test_classify_severity_thresholds() -> None:
    """severity 判定の閾値が改善基準告示数値と整合。"""
    assert _classify_severity(None) == "none"
    assert _classify_severity(0) == "green"
    assert _classify_severity(30) == "green"
    assert _classify_severity(31) == "yellow"
    assert _classify_severity(89) == "yellow"
    assert _classify_severity(90) == "yellow"
    assert _classify_severity(91) == "red"
    assert _classify_severity(150) == "red"


def test_retail_sample_produces_12_cells() -> None:
    """小売サンプルは 3 拠点 × 4 時間帯 = 12 セル。"""
    profile = get_sample("sample_retail_01")
    assert profile is not None
    result = build_wait_time_heatmap(profile)
    assert isinstance(result, HeatmapResult)
    assert len(result.cells) == 12
    assert result.site_names == ["関東地域DC", "中部地域DC", "関西地域DC"]
    assert result.time_slots == ["morning", "midday", "evening", "night"]


def test_retail_sample_kanto_morning_is_yellow() -> None:
    """関東地域DC・朝便は平均 42 分で yellow（30 分超）。"""
    profile = get_sample("sample_retail_01")
    assert profile is not None
    result = build_wait_time_heatmap(profile)
    cell = next(
        c for c in result.cells
        if c.site_name == "関東地域DC" and c.time_slot == "morning"
    )
    assert cell.avg_minutes == 42.0
    assert cell.severity == "yellow"


def test_retail_sample_chubu_all_green() -> None:
    """中部地域DC は全時間帯 green（平均 30 分以下）。"""
    profile = get_sample("sample_retail_01")
    assert profile is not None
    result = build_wait_time_heatmap(profile)
    chubu_cells = [c for c in result.cells if c.site_name == "中部地域DC"]
    assert all(c.severity == "green" for c in chubu_cells)


def test_summary_mentions_worst_yellow() -> None:
    """summary に最悪 yellow セルが言及される。"""
    profile = get_sample("sample_retail_01")
    assert profile is not None
    result = build_wait_time_heatmap(profile)
    assert "関東地域DC" in result.summary
    assert "42" in result.summary


def test_threshold_and_target_are_from_standard() -> None:
    """threshold = 120分、avg_target = 30分（WAIT_TIME_STANDARD と一致）。"""
    profile = get_sample("sample_retail_01")
    assert profile is not None
    result = build_wait_time_heatmap(profile)
    assert result.threshold_minutes == 120
    assert result.avg_target_minutes == 30


def test_citations_include_improvement_standards() -> None:
    """改善基準告示の出典が citations に含まれる。"""
    profile = get_sample("sample_retail_01")
    assert profile is not None
    result = build_wait_time_heatmap(profile)
    labels = [c.label for c in result.citations]
    assert any("自動車運転者の労働時間" in lbl for lbl in labels)


def test_legacy_profile_without_site_name_returns_empty_cells() -> None:
    """既存サンプル（site_name 未指定）はセル数 0（heatmap 不可）。"""
    # SAMPLE_MANUFACTURING の wait_time_rows は site_name=None
    result = build_wait_time_heatmap(SAMPLE_MANUFACTURING)
    assert len(result.cells) == 0
    assert result.site_names == []
    assert "計測データが拠点別に整備" in result.summary or result.summary != ""


def test_chain_sample_has_no_cells_without_site_name() -> None:
    """連鎖化サンプルも site_name 未指定なのでセル 0。"""
    result = build_wait_time_heatmap(SAMPLE_CHAIN)
    assert len(result.cells) == 0


def test_low_confidence_flag_below_minimum_runs() -> None:
    """measured_count が 100 未満なら confidence_low=True。"""
    profile = CompanyProfile(
        company_id="test_low_conf",
        name="テスト企業",
        jsic_code="3159",
        main_business="x",
        annual_revenue_jpy=10_000_000_000,
        annual_freight_tons_total=100_000,
        operating_profit_jpy=500_000_000,
        cost_of_goods_sold_jpy=8_000_000_000,
        clo_name="テスト CLO",
        plan_period_start_fy=2026,
        plan_period_end_fy=2030,
        sites=[
            CompanySite(name="拠点A", site_type="dc",
                        prefecture="東京都", annual_freight_tons=100_000)
        ],
        wait_time_rows=[
            WaitTimeRow(
                bucket_label="拠点A・朝便",
                measured_count=50,  # 100 未満
                average_minutes=20,
                max_minutes=40,
                over_2h_count=0,
                site_name="拠点A",
                time_slot="morning",
            ),
        ],
    )
    result = build_wait_time_heatmap(profile)
    morning = next(c for c in result.cells if c.time_slot == "morning")
    assert morning.confidence_low is True


def test_red_severity_when_avg_exceeds_90_minutes() -> None:
    """平均 91 分以上で red。"""
    profile = CompanyProfile(
        company_id="test_red",
        name="テスト企業",
        jsic_code="3159",
        main_business="x",
        annual_revenue_jpy=10_000_000_000,
        annual_freight_tons_total=100_000,
        operating_profit_jpy=500_000_000,
        cost_of_goods_sold_jpy=8_000_000_000,
        clo_name="テスト CLO",
        plan_period_start_fy=2026,
        plan_period_end_fy=2030,
        sites=[
            CompanySite(name="混雑拠点", site_type="dc",
                        prefecture="東京都", annual_freight_tons=100_000)
        ],
        wait_time_rows=[
            WaitTimeRow(
                bucket_label="混雑拠点・朝便",
                measured_count=200,
                average_minutes=110,
                max_minutes=180,
                over_2h_count=15,
                site_name="混雑拠点",
                time_slot="morning",
            ),
        ],
    )
    result = build_wait_time_heatmap(profile)
    morning = next(c for c in result.cells if c.time_slot == "morning")
    assert morning.severity == "red"
    assert "⚠️" in result.summary


def test_all_day_lane_appears_when_time_slot_unknown() -> None:
    """time_slot=None の行があると all_day レーンが追加される。"""
    profile = CompanyProfile(
        company_id="test_unknown_slot",
        name="テスト企業",
        jsic_code="3159",
        main_business="x",
        annual_revenue_jpy=10_000_000_000,
        annual_freight_tons_total=100_000,
        operating_profit_jpy=500_000_000,
        cost_of_goods_sold_jpy=8_000_000_000,
        clo_name="テスト CLO",
        plan_period_start_fy=2026,
        plan_period_end_fy=2030,
        sites=[
            CompanySite(name="拠点A", site_type="dc",
                        prefecture="東京都", annual_freight_tons=100_000)
        ],
        wait_time_rows=[
            WaitTimeRow(
                bucket_label="拠点A・全日",
                measured_count=300,
                average_minutes=25,
                max_minutes=80,
                over_2h_count=0,
                site_name="拠点A",
                time_slot=None,  # 不明
            ),
        ],
    )
    result = build_wait_time_heatmap(profile)
    assert "all_day" in result.time_slots
