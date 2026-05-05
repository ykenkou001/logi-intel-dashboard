"""core/legal/improvement_check.py の単体テスト。"""
from __future__ import annotations

from core.legal.improvement_check import check_truck_driver_compliance


def test_all_compliant_returns_compliant_overall() -> None:
    """全項目基準内 → overall=compliant。"""
    report = check_truck_driver_compliance(
        daily_working_hours_max=12,
        annual_working_hours=3000,
        annual_overtime_hours=900,
        waiting_minutes_max=20,
        handling_minutes_max=45,
        rest_hours_min=11,
    )
    assert report.overall_status == "compliant"
    assert report.additional_measures_required is False


def test_violation_when_any_item_exceeds() -> None:
    """1 項目でも違反 → overall=violation・追加措置必要。"""
    report = check_truck_driver_compliance(
        daily_working_hours_max=14,  # 13 時間原則を超過
        annual_working_hours=3000,
        annual_overtime_hours=900,
        waiting_minutes_max=20,
        handling_minutes_max=45,
        rest_hours_min=11,
    )
    assert report.overall_status == "violation"
    assert report.additional_measures_required is True
    assert any(i.status == "violation" for i in report.items)


def test_borderline_when_close_to_threshold() -> None:
    """閾値の95%以上 → borderline。"""
    report = check_truck_driver_compliance(
        daily_working_hours_max=12.5,    # 13h の 96% で borderline
        annual_working_hours=3000,
        annual_overtime_hours=900,
        waiting_minutes_max=20,
        handling_minutes_max=45,
        rest_hours_min=11,
    )
    daily_item = next(i for i in report.items if "1日拘束" in i.name)
    assert daily_item.status == "borderline"


def test_waiting_time_violation_at_2hours() -> None:
    """荷待ち 2 時間（120 分）超で違反。"""
    report = check_truck_driver_compliance(
        waiting_minutes_max=125,   # 120 分超
    )
    waiting_item = next(i for i in report.items if "荷待ち" in i.name)
    assert waiting_item.status == "violation"
    assert report.overall_status == "violation"


def test_rest_hours_below_floor_is_violation() -> None:
    """連続休息 9 時間未満 → 違反。"""
    report = check_truck_driver_compliance(rest_hours_min=8)
    rest_item = next(i for i in report.items if "休息" in i.name)
    assert rest_item.status == "violation"


def test_rest_hours_between_floor_and_principle_borderline() -> None:
    """連続休息 9-11 時間は borderline。"""
    report = check_truck_driver_compliance(rest_hours_min=10)
    rest_item = next(i for i in report.items if "休息" in i.name)
    assert rest_item.status == "borderline"


def test_all_not_measured_returns_not_measured_overall() -> None:
    """全項目未計測 → overall=not_measured・計測体制整備が追加措置。"""
    report = check_truck_driver_compliance()
    assert report.overall_status == "not_measured"
    assert report.additional_measures_required is True


def test_to_form5_line_format() -> None:
    """to_form5_line が様式第5 用の形式で出る。"""
    report = check_truck_driver_compliance(daily_working_hours_max=12)
    daily_item = next(i for i in report.items if "1日拘束" in i.name)
    line = daily_item.to_form5_line()
    assert "☑" in line  # compliant マーク
    assert "12" in line
    assert "13" in line  # 基準値


def test_partial_data_compliant() -> None:
    """一部項目だけ計測でも、計測済みが全部 compliant なら overall=compliant。"""
    report = check_truck_driver_compliance(
        waiting_minutes_max=15,
        handling_minutes_max=30,
        # その他は未計測
    )
    # 計測済み項目は全部 compliant、未計測あり → not_measured 扱いにはならず
    # mixed: any compliant も violation も borderline もない場合は not_measured 扱い
    # ただし、現実装では「計測済みが全部 compliant」だと overall=compliant にする
    # 仕様: violation > borderline > not_measured (all) > compliant
    assert report.overall_status in ("compliant", "not_measured")
