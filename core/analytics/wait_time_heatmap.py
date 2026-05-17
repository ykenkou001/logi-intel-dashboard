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

フェーズ 5.5 Tier S3 拡張:
    - build_wait_time_heatmap(profile, facility=...) で施設単位フィルタを追加
      （facility=None なら既存挙動の全社集計、後方互換完全維持）
    - Facility.site_name を WaitTimeRow.site_name と一致させてフィルタする
      （CompanyProfile を破壊変更しない設計判断、plans/facility_store.md §3.3）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from core.export.citation import Citation, improvement_standards_citation
from core.static._freshness import all_warnings, get
from core.static.improvement_standards import WAIT_TIME_STANDARD
from core.static.sample_company import CompanyProfile, WaitTimeRow

if TYPE_CHECKING:
    from core.io.facility_store import Facility

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
    """ヒートマップ全体結果。

    フェーズ 5.5 Tier S3 で施設フィルタ用フィールドを追加（既存利用箇所は
    facility_* / measurement_* / is_consigned_warehouse / consigned_notice を
    無視できる: default 値で全社集計と互換）。

    Codex §8.4-2（フォロー PR）で include_consigned + 除外件数フィールドを追加。
    全社集計時に寄託先 site を既定除外しつつ、件数を可視化する。
    """

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
    # --- Tier S3: 施設フィルタ時の補足情報（facility 指定なしのときは None / 空） ---
    facility_id: str | None = None
    facility_name: str | None = None
    measurement_period_label: str | None = None
    """例: '2025-04-01 〜 2026-03-31（月次）'"""
    measurement_conditions: list[str] = field(default_factory=list)
    exclusion_reasons: list[str] = field(default_factory=list)
    is_consigned_warehouse: bool = False
    consigned_notice: str | None = None
    """寄託先施設の場合に表示する自社測定外バナー文言。"""
    # --- Tier S3 フォロー PR: 全社集計時の寄託先除外の可視化 ---
    include_consigned: bool = False
    """今回の集計で寄託先 site を含めたか（facility 指定時は False 固定）。"""
    primary_aggregated_site_count: int = 0
    """主集計に含まれた拠点数（除外後）。"""
    excluded_consigned_site_count: int = 0
    """寄託先として除外された拠点数（全社集計時のみ意味あり）。"""
    excluded_consigned_site_names: list[str] = field(default_factory=list)
    """除外された寄託先拠点名一覧（CLO 説明責任のため metadata に残す）。"""


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


def build_wait_time_heatmap(
    profile: CompanyProfile,
    facility: Facility | None = None,
    include_consigned: bool = False,
    facilities: list[Facility] | None = None,
) -> HeatmapResult:
    """CompanyProfile.wait_time_rows を拠点 × 時間帯 4 区分で集計する。

    Args:
        profile: 自社プロフィール（wait_time_rows を持つ）
        facility: 指定時はその施設の site_name に紐付く行のみで集計する
            （フェーズ 5.5 Tier S3 で追加）。facility.site_name が None の場合は
            ValueError（測定単位が未紐付け＝集計不能）。
        include_consigned: 全社集計時（facility=None）に寄託先施設の site も含めるか。
            既定 False（Codex §8.4-2: 自社管理施設の主集計に寄託先を混入させない）。
            facility 直接指定時はこの引数は無視され、対象施設のみで集計する。
        facilities: 全社集計時に参照する Facility 一覧。None なら
            load_facilities(profile.company_id) を実行時に呼ぶ。テスト等で
            外部からの注入が必要な場合に指定する。

    Returns:
        HeatmapResult: ヒートマップ表示に必要な構造化データ
            facility 指定時は facility_id / facility_name / measurement_period_label /
            exclusion_reasons / is_consigned_warehouse / consigned_notice が設定される。
            全社集計時は excluded_consigned_site_* / primary_aggregated_site_count が
            設定される。

    Raises:
        ValueError: facility.site_name が None の場合
        ValueError: facility.company_id が profile.company_id と一致しない場合
    """
    # Tier S3: 施設フィルタ事前検証
    target_site_name: str | None = None
    if facility is not None:
        if facility.company_id != profile.company_id:
            raise ValueError(
                f"facility.company_id={facility.company_id!r} は "
                f"profile.company_id={profile.company_id!r} と一致しません"
            )
        if facility.site_name is None:
            raise ValueError(
                f"facility_id={facility.facility_id!r} は site_name が未設定です。"
                "wait_time_rows との連結キーが必要です（plans/facility_store.md §3.3）"
            )
        target_site_name = facility.site_name

    # Tier S3 フォロー: 全社集計時に寄託先 site を除外するための準備
    consigned_site_names: set[str] = set()
    excluded_consigned_site_names: list[str] = []
    effective_include_consigned: bool = include_consigned
    if facility is None and not include_consigned:
        # 全社集計 & 既定（寄託先除外）モード
        facility_pool = facilities
        if facility_pool is None:
            # 遅延 import で循環参照回避
            from core.io.facility_store import load_facilities

            facility_pool = load_facilities(profile.company_id)
        for f in facility_pool:
            if f.is_consigned_for_aggregation and f.site_name:
                consigned_site_names.add(f.site_name)
    elif facility is not None:
        # facility 直接指定時は include_consigned 無効
        effective_include_consigned = False

    # 1. site_name 指定行のみ抽出（拠点別レーンを構成）
    site_rows: dict[str, dict[str, list[WaitTimeRow]]] = {}
    for row in profile.wait_time_rows:
        if row.site_name is None:
            continue
        # Tier S3: facility 指定時は対象 site_name のみ
        if target_site_name is not None and row.site_name != target_site_name:
            continue
        # Tier S3 フォロー: 全社集計 + 既定モードで寄託先 site を除外
        if facility is None and row.site_name in consigned_site_names:
            if row.site_name not in excluded_consigned_site_names:
                excluded_consigned_site_names.append(row.site_name)
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

    # 5. 全体集計（ヘッダ表示用）— facility 指定時は対象 site_name のみで集計
    all_rows = [r for r in profile.wait_time_rows if r.site_name is not None]
    if target_site_name is not None:
        all_rows = [r for r in all_rows if r.site_name == target_site_name]
    elif facility is None and not include_consigned and consigned_site_names:
        # 全社集計 + 既定モード: 寄託先 site の行も overall から除外
        all_rows = [r for r in all_rows if r.site_name not in consigned_site_names]
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

    # 8. Tier S3: facility 指定時の補足情報
    facility_id_out: str | None = None
    facility_name_out: str | None = None
    measurement_period_label: str | None = None
    measurement_conditions: list[str] = []
    exclusion_reasons: list[str] = []
    is_consigned_warehouse = False
    consigned_notice: str | None = None
    if facility is not None:
        facility_id_out = facility.facility_id
        facility_name_out = facility.name
        period = facility.measurement_period
        measurement_period_label = (
            f"{period.start_on.isoformat()} 〜 {period.end_on.isoformat()}"
            f"（{period.unit_label}）"
        )
        measurement_conditions = list(facility.measurement_conditions)
        exclusion_reasons = list(facility.exclusion_reasons)
        is_consigned_warehouse = facility.is_consigned_warehouse
        if facility.is_consigned_warehouse:
            consigned_notice = (
                f"⚠️ {facility.name} は寄託先施設（自社測定外）です。"
                "計測値は委託先報告に基づくため、様式第5 提出時は「測定実施者」を"
                "明示し、責任主体（自社・寄託先）を区別して注記してください。"
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
        facility_id=facility_id_out,
        facility_name=facility_name_out,
        measurement_period_label=measurement_period_label,
        measurement_conditions=measurement_conditions,
        exclusion_reasons=exclusion_reasons,
        is_consigned_warehouse=is_consigned_warehouse,
        consigned_notice=consigned_notice,
        include_consigned=effective_include_consigned,
        primary_aggregated_site_count=len(site_names),
        excluded_consigned_site_count=len(excluded_consigned_site_names),
        excluded_consigned_site_names=excluded_consigned_site_names,
    )
