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


# ---------------------------------------------------------------------------
# Tier S3: Facility フィルタ拡張テスト
# ---------------------------------------------------------------------------


def _make_test_facility(
    *,
    facility_id: str = "fac_kanto",
    company_id: str = "sample_retail_01",
    site_name: str | None = "関東地域DC",
    is_consigned: bool = False,
):
    from datetime import date

    from core.io.facility_store import Facility, FacilityMeasurementPeriod

    return Facility(
        facility_id=facility_id,
        company_id=company_id,
        name="関東 DC（テスト施設）",
        address="東京都江東区豊洲 1-1-1",
        prefecture="東京都",
        industry_code="5411",
        site_name=site_name,
        measurement_period=FacilityMeasurementPeriod(
            start_on=date(2025, 4, 1),
            end_on=date(2026, 3, 31),
            unit_label="月次",
        ),
        measurement_conditions=["パレット便のみ"],
        exclusion_reasons=["2025-08 改修工事中"],
        is_consigned_warehouse=is_consigned,
    )


def test_facility_filter_narrows_to_target_site() -> None:
    """facility 指定時は site_name 一致行のみで集計される（拠点 1 件分のセル）。"""
    profile = get_sample("sample_retail_01")
    assert profile is not None
    facility = _make_test_facility(site_name="関東地域DC")
    result = build_wait_time_heatmap(profile, facility=facility)

    assert result.site_names == ["関東地域DC"]
    assert result.facility_id == "fac_kanto"
    assert result.facility_name == "関東 DC（テスト施設）"
    # 4 時間帯のみ（all_day 無し）→ 4 セル
    assert len(result.cells) == 4
    assert all(c.site_name == "関東地域DC" for c in result.cells)


def test_facility_filter_includes_period_label() -> None:
    """facility 指定時は measurement_period_label がフォーマットされる。"""
    profile = get_sample("sample_retail_01")
    assert profile is not None
    facility = _make_test_facility()
    result = build_wait_time_heatmap(profile, facility=facility)

    assert result.measurement_period_label is not None
    assert "2025-04-01" in result.measurement_period_label
    assert "2026-03-31" in result.measurement_period_label
    assert "月次" in result.measurement_period_label
    assert result.measurement_conditions == ["パレット便のみ"]
    assert result.exclusion_reasons == ["2025-08 改修工事中"]


def test_facility_without_site_name_raises_value_error() -> None:
    """site_name=None の Facility は wait_time_rows と紐付かないので ValueError。"""
    import pytest

    profile = get_sample("sample_retail_01")
    assert profile is not None
    facility = _make_test_facility(site_name=None)
    with pytest.raises(ValueError, match="site_name が未設定"):
        build_wait_time_heatmap(profile, facility=facility)


def test_facility_company_id_mismatch_raises_value_error() -> None:
    """profile.company_id と facility.company_id が一致しなければ ValueError。"""
    import pytest

    profile = get_sample("sample_retail_01")
    assert profile is not None
    facility = _make_test_facility(company_id="different_company")
    with pytest.raises(ValueError, match="一致しません"):
        build_wait_time_heatmap(profile, facility=facility)


def test_facility_consigned_warehouse_emits_notice() -> None:
    """is_consigned_warehouse=True で consigned_notice が出力される。集計は通常通り。"""
    profile = get_sample("sample_retail_01")
    assert profile is not None
    facility = _make_test_facility(is_consigned=True)
    result = build_wait_time_heatmap(profile, facility=facility)

    assert result.is_consigned_warehouse is True
    assert result.consigned_notice is not None
    assert "寄託先施設" in result.consigned_notice
    assert "自社測定外" in result.consigned_notice
    # 集計はそのまま実行される（Codex 二者議論で「警告付き集計」案を採用）
    assert len(result.cells) == 4


def test_facility_none_preserves_legacy_behavior() -> None:
    """facility=None（デフォルト）は既存挙動と完全互換（後方互換確認）。"""
    profile = get_sample("sample_retail_01")
    assert profile is not None
    result_default = build_wait_time_heatmap(profile)
    result_explicit_none = build_wait_time_heatmap(profile, facility=None)

    assert result_default.cells == result_explicit_none.cells
    assert result_default.site_names == result_explicit_none.site_names
    assert result_default.facility_id is None
    assert result_default.consigned_notice is None
    assert result_default.is_consigned_warehouse is False


# ---------------------------------------------------------------------------
# Tier S3 フォロー PR: include_consigned 引数（Codex §8.4-2 反映）
# ---------------------------------------------------------------------------


def test_include_consigned_false_excludes_consigned_site() -> None:
    """全社集計（既定）で寄託先 site が除外される。"""
    profile = get_sample("sample_retail_01")
    assert profile is not None
    # 関東地域DC を寄託先として登録
    facilities = [
        _make_test_facility(
            facility_id="fac_consigned_kanto",
            site_name="関東地域DC",
            is_consigned=True,
        )
    ]
    result = build_wait_time_heatmap(
        profile, include_consigned=False, facilities=facilities
    )

    # 関東地域DC は除外され、中部 + 関西の 2 拠点のみ集計
    assert "関東地域DC" not in result.site_names
    assert result.excluded_consigned_site_count == 1
    assert "関東地域DC" in result.excluded_consigned_site_names
    assert result.include_consigned is False
    assert result.primary_aggregated_site_count == len(result.site_names)


def test_include_consigned_true_keeps_consigned_site() -> None:
    """include_consigned=True で寄託先 site も主集計に含まれる。"""
    profile = get_sample("sample_retail_01")
    assert profile is not None
    facilities = [
        _make_test_facility(
            facility_id="fac_consigned_kanto",
            site_name="関東地域DC",
            is_consigned=True,
        )
    ]
    result = build_wait_time_heatmap(
        profile, include_consigned=True, facilities=facilities
    )

    # 関東地域DC も含めて全 3 拠点が集計対象
    assert "関東地域DC" in result.site_names
    assert result.include_consigned is True
    # excluded_consigned_site_count は 0（除外していないので）
    assert result.excluded_consigned_site_count == 0


def test_include_consigned_ignored_when_facility_specified() -> None:
    """facility 直接指定時は include_consigned が無視され、対象 site のみ集計。"""
    profile = get_sample("sample_retail_01")
    assert profile is not None
    facility = _make_test_facility(site_name="関東地域DC", is_consigned=True)
    # facilities 一覧（無視されることを確認）
    facilities_pool = [facility]

    result = build_wait_time_heatmap(
        profile,
        facility=facility,
        include_consigned=False,  # 通常なら除外だが facility 指定優先
        facilities=facilities_pool,
    )
    # facility=facility のとき対象 site のみで集計（除外ロジック非適用）
    assert result.site_names == ["関東地域DC"]
    assert result.include_consigned is False
    assert result.excluded_consigned_site_count == 0


def test_overall_avg_excludes_consigned_rows_in_default_mode() -> None:
    """全社集計（既定）の overall_avg は寄託先 site の行を含めない。"""
    profile = get_sample("sample_retail_01")
    assert profile is not None
    facilities_with_consigned = [
        _make_test_facility(
            facility_id="fac_consigned_kanto",
            site_name="関東地域DC",
            is_consigned=True,
        )
    ]
    result_excluded = build_wait_time_heatmap(
        profile, include_consigned=False, facilities=facilities_with_consigned
    )
    result_included = build_wait_time_heatmap(
        profile, include_consigned=True, facilities=facilities_with_consigned
    )

    # 関東を除外した overall_avg は含めたものと異なる
    assert result_excluded.overall_avg_minutes is not None
    assert result_included.overall_avg_minutes is not None
    # 関東 DC は朝便平均 42 分（yellow）で全体平均を上げる方向に作用
    # 除外時の方が平均が下がる（少なくとも一致しない）
    assert result_excluded.overall_avg_minutes != result_included.overall_avg_minutes


def test_no_facilities_means_no_exclusion() -> None:
    """寄託先 Facility 未登録なら除外は発生しない（旧挙動と等価）。"""
    profile = get_sample("sample_retail_01")
    assert profile is not None
    result = build_wait_time_heatmap(
        profile, include_consigned=False, facilities=[]
    )
    assert result.excluded_consigned_site_count == 0
    assert result.excluded_consigned_site_names == []
    # 3 拠点全部が集計対象
    assert len(result.site_names) == 3
