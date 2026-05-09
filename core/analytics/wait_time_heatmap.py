"""拠点別 × 時間帯別 荷待ち時間ヒートマップ集計。

J3 デイリーコックピット（フェーズ4.5）の前提となる可視化。CLO が「どの拠点が
朝混むのか」を 5 秒で把握できるよう、CompanyProfile.wait_time_rows を
拠点 × 時間帯 4 区分（朝/昼/夕/夜）で集計する。

設計方針:
    - WaitTimeRow.site_name + WaitTimeRow.time_slot を縦横軸キーとして集計
    - site_name 未指定の行は集計対象外（拠点別レーンに振り分けられない）
    - time_slot 未指定の行は "all_day" レーンに振り分け
    - severity 判定は core.static.improvement_standards.WAIT_TIME_STANDARD を参照
      （30 分以下=green / 30〜90 分=yellow / 90 分超=red / 未計測=none）
    - 計測便数が少ない場合（measurement_minimum_runs 未満）は confidence_low フラグ
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from core.export.citation import Citation, improvement_standards_citation
from core.static._freshness import all_warnings, get
from core.static.improvement_standards import WAIT_TIME_STANDARD
from core.static.sample_company import CompanyProfile, WaitTimeRow

Severity = Literal["green", "yellow", "red", "none"]
"""ヒートマップセルの severity:
- "green":  平均 ≤ 30 分（avg_target_minutes 以下）
- "yellow": 平均 30〜90 分（threshold の 75% 以下）
- "red":    平均 > 90 分（threshold 接近 or 超過）
- "none":   計測なし（measured_count == 0）
"""

# 表示順固定（ヒートマップの横軸順序）
TIME_SLOT_ORDER: tuple[str, ...] = ("morning", "midday", "evening", "night", "all_day")
TIME_SLOT_LABEL: dict[str, str] = {
    "morning": "朝便（6-10時）",
    "midday": "昼便（10-15時）",
    "evening": "夕便（15-19時）",
    "night": "夜便（19-翌6時）",
    "all_day": "時間帯不明",
}


@dataclass(frozen=True)
class HeatmapCell:
    """拠点 × 時間帯 1 セルの集計結果。"""

    site_name: str
    time_slot: str
    """morning/midday/evening/night/all_day のいずれか。"""
    avg_minutes: float | None
    max_minutes: float | None
    measured_count: int
    over_2h_count: int
    severity: Severity
    confidence_low: bool = False
    """計測便数が WAIT_TIME_STANDARD.measurement_minimum_runs 未満なら True。"""


@dataclass
class HeatmapResult:
    """ヒートマップ全体結果。"""

    company_id: str
    company_name: str
    cells: list[HeatmapCell] = field(default_factory=list)
    site_names: list[str] = field(default_factory=list)
    time_slots: list[str] = field(default_factory=list)
    overall_avg_minutes: float | None = None
    overall_max_minutes: float | None = None
    threshold_minutes: int = 120
    avg_target_minutes: int = 30
    citations: list[Citation] = field(default_factory=list)
    freshness_warnings: list[str] = field(default_factory=list)
    summary: str = ""


def _classify_severity(avg_minutes: float | None) -> Severity:
    """平均荷待ち時間から severity を判定する。"""
    if avg_minutes is None:
        return "none"
    if avg_minutes <= WAIT_TIME_STANDARD.avg_target_minutes:
        return "green"
    # threshold (120分) の 75% = 90分 を yellow/red 境界とする
    if avg_minutes <= WAIT_TIME_STANDARD.threshold_minutes * 0.75:
        return "yellow"
    return "red"


def _aggregate_rows(rows: list[WaitTimeRow]) -> tuple[float | None, float | None, int, int]:
    """複数行をまとめた加重平均を返す（avg, max, count_total, over_2h_total）。"""
    total_count = sum(r.measured_count for r in rows)
    if total_count == 0:
        return None, None, 0, 0
    weighted_sum = sum(r.average_minutes * r.measured_count for r in rows)
    avg = weighted_sum / total_count
    max_min = max(r.max_minutes for r in rows)
    over_2h_sum = sum(r.over_2h_count for r in rows)
    return avg, max_min, total_count, over_2h_sum


def build_wait_time_heatmap(profile: CompanyProfile) -> HeatmapResult:
    """CompanyProfile.wait_time_rows を拠点 × 時間帯 4 区分で集計する。

    Args:
        profile: 自社プロフィール（wait_time_rows を持つ）

    Returns:
        HeatmapResult: ヒートマップ表示に必要な構造化データ
    """
    # 1. site_name 指定行のみ抽出（拠点別レーンを構成）
    site_rows: dict[str, dict[str, list[WaitTimeRow]]] = {}
    for row in profile.wait_time_rows:
        if row.site_name is None:
            continue
        slot_key: str = row.time_slot if row.time_slot is not None else "all_day"
        site_rows.setdefault(row.site_name, {}).setdefault(slot_key, []).append(row)

    # 2. 縦軸（site_names）順序：profile.sites の順序を尊重し、
    #    そこに含まれない site_name（誤記等）は末尾に追加
    site_order_from_profile = [s.name for s in profile.sites]
    site_names: list[str] = []
    for s in site_order_from_profile:
        if s in site_rows:
            site_names.append(s)
    for s in site_rows:
        if s not in site_names:
            site_names.append(s)

    # 3. 横軸：time_slot は固定順序、ただし all_day レーンは
    #    1 件以上ある場合のみ表示
    has_all_day = any("all_day" in slots for slots in site_rows.values())
    time_slots = [s for s in TIME_SLOT_ORDER if s != "all_day" or has_all_day]

    # 4. セル集計
    cells: list[HeatmapCell] = []
    minimum_runs = WAIT_TIME_STANDARD.measurement_minimum_runs
    for site in site_names:
        for slot in time_slots:
            rows = site_rows.get(site, {}).get(slot, [])
            avg, max_min, count, over_2h = _aggregate_rows(rows)
            severity = _classify_severity(avg)
            cells.append(
                HeatmapCell(
                    site_name=site,
                    time_slot=slot,
                    avg_minutes=avg,
                    max_minutes=max_min,
                    measured_count=count,
                    over_2h_count=over_2h,
                    severity=severity,
                    confidence_low=(0 < count < minimum_runs),
                )
            )

    # 5. 全体集計（ヘッダ表示用）
    all_rows = [r for r in profile.wait_time_rows if r.site_name is not None]
    overall_avg, overall_max, _, _ = _aggregate_rows(all_rows)

    # 6. 出典・鮮度
    citations: list[Citation] = [improvement_standards_citation()]
    standard_freshness = get("improvement_standards")
    warnings = all_warnings()
    if standard_freshness is not None:
        wt = standard_freshness.warning_text()
        if wt and wt not in warnings:
            warnings = [*warnings, wt]

    # 7. summary（経営層向け1行）
    red_cells = [c for c in cells if c.severity == "red"]
    yellow_cells = [c for c in cells if c.severity == "yellow"]
    if red_cells:
        worst = max(red_cells, key=lambda c: c.avg_minutes or 0)
        summary = (
            f"⚠️ {worst.site_name}・{TIME_SLOT_LABEL[worst.time_slot]} の平均待機 "
            f"{worst.avg_minutes:.0f}分（基準 30 分超）。"
            f"red セル {len(red_cells)} 件・yellow {len(yellow_cells)} 件。"
        )
    elif yellow_cells:
        worst = max(yellow_cells, key=lambda c: c.avg_minutes or 0)
        summary = (
            f"yellow セル {len(yellow_cells)} 件あり。"
            f"最長 {worst.site_name}・{TIME_SLOT_LABEL[worst.time_slot]} で "
            f"平均 {worst.avg_minutes:.0f} 分。30 分以下が目標。"
        )
    else:
        summary = (
            f"全セル green（平均 30 分以下）。全体平均 "
            f"{overall_avg:.0f} 分・最大 {overall_max:.0f} 分。"
            if overall_avg is not None
            else "計測データが拠点別に整備されていません（site_name 指定の行を追加してください）。"
        )

    return HeatmapResult(
        company_id=profile.company_id,
        company_name=profile.name,
        cells=cells,
        site_names=site_names,
        time_slots=time_slots,
        overall_avg_minutes=overall_avg,
        overall_max_minutes=overall_max,
        threshold_minutes=WAIT_TIME_STANDARD.threshold_minutes,
        avg_target_minutes=WAIT_TIME_STANDARD.avg_target_minutes,
        citations=citations,
        freshness_warnings=list(warnings),
        summary=summary,
    )
