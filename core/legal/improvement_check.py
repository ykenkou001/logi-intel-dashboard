"""改善基準告示準拠チェックエンジン。

入力された運転実績値（荷待ち・荷役・拘束時間等）が改善基準告示の基準内に
収まっているかを判定する。様式第5（定期報告書）に記載する遵守状況の根拠と
なる。

法令根拠:
    厚生労働省告示「自動車運転者の労働時間等の改善のための基準」
    （詳細は core/static/improvement_standards.py 参照）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from core.static.improvement_standards import TRUCK_DRIVER_STANDARD

ComplianceStatus = Literal["compliant", "violation", "borderline", "not_measured"]


@dataclass(frozen=True)
class ComplianceItem:
    """1 つの判断基準項目の遵守状況。"""

    name: str  # 項目名（例: "1日拘束時間"）
    status: ComplianceStatus
    measured_value: float | None  # 実測値
    threshold: float  # 告示基準値
    unit: str  # 単位（例: "時間", "分"）
    note: str = ""

    def to_form5_line(self) -> str:
        """様式第5 報告書向けの 1 行表示。"""
        check = {
            "compliant": "☑ 遵守",
            "violation": "☒ 違反",
            "borderline": "△ 要注意",
            "not_measured": "― 未計測",
        }[self.status]
        if self.measured_value is None:
            return f"{check}  {self.name} （基準: {self.threshold}{self.unit}）"
        return (
            f"{check}  {self.name}: 実測 {self.measured_value}{self.unit} "
            f"／ 基準 {self.threshold}{self.unit}"
        )


@dataclass(frozen=True)
class ComplianceReport:
    """改善基準告示の総合チェック結果。"""

    items: list[ComplianceItem]
    overall_status: ComplianceStatus
    summary: str
    additional_measures_required: bool  # 追加措置が必要か（様式第5 Ⅲ用）
    notes: list[str] = field(default_factory=list)


def _check_threshold(
    name: str,
    measured: float | None,
    threshold: float,
    unit: str,
    *,
    borderline_ratio: float = 0.95,
) -> ComplianceItem:
    """単一項目の閾値チェック。

    measured が None なら not_measured、threshold 超過なら violation、
    borderline_ratio 以上 threshold 未満なら borderline、それ以下なら compliant。
    """
    if measured is None:
        return ComplianceItem(name, "not_measured", None, threshold, unit)
    if measured > threshold:
        return ComplianceItem(
            name,
            "violation",
            measured,
            threshold,
            unit,
            note="基準超過。様式第5 Ⅲ で追加措置を記載する必要あり",
        )
    if measured >= threshold * borderline_ratio:
        return ComplianceItem(
            name,
            "borderline",
            measured,
            threshold,
            unit,
            note="基準値ぎりぎり。改善余地を要検討",
        )
    return ComplianceItem(name, "compliant", measured, threshold, unit)


def check_truck_driver_compliance(
    daily_working_hours_max: float | None = None,
    annual_working_hours: float | None = None,
    annual_overtime_hours: float | None = None,
    waiting_minutes_max: float | None = None,
    handling_minutes_max: float | None = None,
    rest_hours_min: float | None = None,
) -> ComplianceReport:
    """トラック運転者の改善基準告示準拠状況を一括チェックする。

    Args:
        daily_working_hours_max: 1日拘束時間の最大値（時間）
        annual_working_hours: 年間総拘束時間（時間）
        annual_overtime_hours: 年間時間外労働（時間）
        waiting_minutes_max: 荷待ち時間の最大値（分）— 2時間=120分基準
        handling_minutes_max: 荷役等時間の最大値（分）— 2時間=120分基準
        rest_hours_min: 連続休息の最小値（時間）

    Returns:
        ComplianceReport
    """
    std = TRUCK_DRIVER_STANDARD
    items: list[ComplianceItem] = []

    items.append(
        _check_threshold(
            "1日拘束時間（原則）",
            daily_working_hours_max,
            std.max_daily_working_hours_principle,
            "時間",
        )
    )
    items.append(
        _check_threshold(
            "年間総拘束時間",
            annual_working_hours,
            std.max_annual_working_hours_principle,
            "時間",
        )
    )
    items.append(
        _check_threshold(
            "年間時間外労働",
            annual_overtime_hours,
            std.max_annual_overtime_hours,
            "時間",
        )
    )
    items.append(
        _check_threshold(
            "荷待ち時間",
            waiting_minutes_max,
            120,  # 2 時間 = 120 分（物流効率化法 判断基準）
            "分",
        )
    )
    items.append(
        _check_threshold(
            "荷役等時間",
            handling_minutes_max,
            120,  # 2 時間 = 120 分（物流効率化法 判断基準）
            "分",
        )
    )

    # 連続休息は「最低何時間か」なので逆向きの判定
    if rest_hours_min is None:
        items.append(
            ComplianceItem(
                "連続休息時間",
                "not_measured",
                None,
                std.min_rest_hours_principle,
                "時間",
            )
        )
    elif rest_hours_min < std.min_rest_hours_floor:
        items.append(
            ComplianceItem(
                "連続休息時間",
                "violation",
                rest_hours_min,
                std.min_rest_hours_floor,
                "時間",
                note="下限 9 時間を割っている",
            )
        )
    elif rest_hours_min < std.min_rest_hours_principle:
        items.append(
            ComplianceItem(
                "連続休息時間",
                "borderline",
                rest_hours_min,
                std.min_rest_hours_principle,
                "時間",
                note="原則 11 時間を満たしていない（下限 9h はクリア）",
            )
        )
    else:
        items.append(
            ComplianceItem(
                "連続休息時間",
                "compliant",
                rest_hours_min,
                std.min_rest_hours_principle,
                "時間",
            )
        )

    # 総合判定
    if any(i.status == "violation" for i in items):
        overall: ComplianceStatus = "violation"
        summary = "改善基準告示違反項目あり。追加措置の記載が必要"
        additional_measures = True
    elif any(i.status == "borderline" for i in items):
        overall = "borderline"
        summary = "全項目基準内だが、ぎりぎりの項目あり。改善余地を継続精査"
        additional_measures = False
    elif all(i.status == "not_measured" for i in items):
        overall = "not_measured"
        summary = "計測データが存在しない。計測体制の整備が必要"
        additional_measures = True  # 計測体制整備が追加措置
    else:
        overall = "compliant"
        summary = "全項目基準内に収まっている"
        additional_measures = False

    return ComplianceReport(
        items=items,
        overall_status=overall,
        summary=summary,
        additional_measures_required=additional_measures,
    )
