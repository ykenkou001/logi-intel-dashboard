"""定期報告書（様式第5）ドラフト生成 — フェーズ3.5 Step 7。

毎年 7 月末提出の様式第5 の Word ドラフトを生成する。
フェーズ4.5「継続運用」への橋渡しとなる機能。

設計方針:
    - 中長期計画（plan_draft）を内部で再実行して進捗比較セクションを構築
    - 計測データはサンプル別の標準値テンプレート（実データ取込はフェーズ4.0）
    - 改善基準告示準拠チェックは check_truck_driver_compliance を経由
    - 提出実務チェックリスト（Codex 1 取込）を最終ページに統合
    - 連鎖化事業者は荷役等項目を docx_form5_writer 側で自動省略
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.analytics.plan_draft import PlanDraftResult, generate_plan_draft
from core.export.citation import (
    Citation,
    co2_factors_citation,
    improvement_standards_citation,
    logistics_efficiency_law_article46_citation,
    logistics_efficiency_law_article65_citation,
    logistics_efficiency_law_article66_citation,
)
from core.export.docx_form5_writer import (
    Form5Sections,
    HandlingTimeRow,
    ProgressRow,
    WaitTimeRow,
    write_form5,
)
from core.export.submission_checklist import (
    SubmissionChecklist,
    build_submission_checklist,
)
from core.legal.improvement_check import (
    ComplianceReport,
    check_truck_driver_compliance,
)
from core.static._freshness import all_warnings
from core.static.sample_company import DataSource, get_sample


@dataclass
class PeriodicReportResult:
    """定期報告書ドラフト生成の結果。"""

    company_id: str
    company_name: str
    report_period: str
    eligibility_categories: list[str]

    compliance: ComplianceReport
    wait_time_rows: list[WaitTimeRow]
    handling_time_rows: list[HandlingTimeRow]
    progress_rows: list[ProgressRow]
    submission_checklist: SubmissionChecklist

    files: dict[str, str] = field(default_factory=dict)
    citations: list[Citation] = field(default_factory=list)
    freshness_warnings: list[str] = field(default_factory=list)
    data_source: DataSource = "estimated"


# サンプル別の計測値テンプレート（実データ取込はフェーズ4.0）
# 出典: 国交省 様式第5 記載見本集（manufacturing_report_advanced.md）の数値レンジ
_WAIT_TIME_TEMPLATES: dict[str, list[WaitTimeRow]] = {
    "sample_mfg_01": [
        WaitTimeRow(
            bucket_label="全体",
            measured_count=8420,
            average_minutes=14,
            max_minutes=112,
            over_2h_count=0,
        ),
        WaitTimeRow(
            bucket_label="都市部拠点（埼玉・愛知）",
            measured_count=4100,
            average_minutes=18,
            max_minutes=112,
            over_2h_count=0,
        ),
        WaitTimeRow(
            bucket_label="地方拠点（兵庫）",
            measured_count=4320,
            average_minutes=9,
            max_minutes=35,
            over_2h_count=0,
        ),
    ],
    "sample_wholesale_01": [
        WaitTimeRow(
            bucket_label="全体",
            measured_count=12500,
            average_minutes=35,
            max_minutes=145,
            over_2h_count=8,
        ),
        WaitTimeRow(
            bucket_label="関東センター（千葉）",
            measured_count=4500,
            average_minutes=32,
            max_minutes=130,
            over_2h_count=3,
        ),
        WaitTimeRow(
            bucket_label="関西センター（大阪）",
            measured_count=3800,
            average_minutes=38,
            max_minutes=145,
            over_2h_count=5,
        ),
    ],
    "sample_chain_01": [
        WaitTimeRow(
            bucket_label="全体（4 DC合算）",
            measured_count=25000,
            average_minutes=18,
            max_minutes=65,
            over_2h_count=0,
        ),
        WaitTimeRow(
            bucket_label="関東第一センター（埼玉）",
            measured_count=12000,
            average_minutes=15,
            max_minutes=55,
            over_2h_count=0,
        ),
        WaitTimeRow(
            bucket_label="関西センター（大阪）",
            measured_count=7000,
            average_minutes=20,
            max_minutes=65,
            over_2h_count=0,
        ),
    ],
}

_HANDLING_TIME_TEMPLATES: dict[str, list[HandlingTimeRow]] = {
    "sample_mfg_01": [
        HandlingTimeRow(
            bucket_label="パレット納品",
            measured_count=6200,
            average_minutes=28,
            max_minutes=45,
            over_1h_pct=0.0,
        ),
        HandlingTimeRow(
            bucket_label="かご車納品",
            measured_count=1800,
            average_minutes=35,
            max_minutes=58,
            over_1h_pct=0.0,
        ),
        HandlingTimeRow(
            bucket_label="バラ納品",
            measured_count=420,
            average_minutes=52,
            max_minutes=104,
            over_1h_pct=8.0,
        ),
    ],
    "sample_wholesale_01": [
        HandlingTimeRow(
            bucket_label="パレット納品",
            measured_count=5000,
            average_minutes=30,
            max_minutes=90,
            over_1h_pct=0.0,
        ),
        HandlingTimeRow(
            bucket_label="バラ納品",
            measured_count=800,
            average_minutes=75,
            max_minutes=120,
            over_1h_pct=12.0,
        ),
    ],
    # 連鎖化（コンビニ）は荷役等時間が法令上対象外のため、参考表示のみ簡素に
    "sample_chain_01": [],
}


async def generate_periodic_report(
    company_id: str,
    report_fy: int = 2026,
) -> PeriodicReportResult:
    """サンプル企業プロフィールから定期報告書ドラフトを生成する。

    Args:
        company_id: サンプル企業ID（例: "sample_mfg_01"）
        report_fy: 報告対象年度（西暦・例: 2026 → 2026年4月〜2027年3月）

    Returns:
        PeriodicReportResult — 様式第5 Word のパスと各セクション結果

    Raises:
        ValueError: company_id が未登録の場合
    """
    profile = get_sample(company_id)
    if profile is None:
        raise ValueError(
            f"サンプル企業 '{company_id}' が見つかりません。"
            "利用可能: sample_mfg_01 / sample_wholesale_01 / sample_chain_01"
        )

    # 中長期計画書を内部生成（Ⅴ 進捗比較セクションの基礎）
    plan = await generate_plan_draft(company_id)

    # 計測データ（サンプル別テンプレート）
    wait_rows = list(_WAIT_TIME_TEMPLATES.get(company_id, []))
    handling_rows = list(_HANDLING_TIME_TEMPLATES.get(company_id, []))

    # 改善基準告示準拠チェック（計測データから max を抽出）
    compliance = _build_compliance(wait_rows, handling_rows)

    # 中長期計画 vs 実績ギャップ
    progress_rows = _build_progress_rows(plan)

    # 提出実務チェックリスト（Codex 1 取込）
    checklist = build_submission_checklist(
        company_name=profile.name,
        main_business=profile.main_business,
        jsic_code=profile.jsic_code,
        clo_name=profile.clo_name,
        is_chain_franchise=profile.is_chain_franchise,
        must_appoint_clo=plan.eligibility.must_appoint_clo,
    )

    report_period = (
        f"{report_fy}年度（{report_fy}年4月1日〜{report_fy + 1}年3月31日）"
    )

    sections = Form5Sections(
        company_name=profile.name,
        company_id=profile.company_id,
        main_business=profile.main_business,
        jsic_code=profile.jsic_code,
        eligibility_categories=list(plan.eligibility.categories),
        clo_name=profile.clo_name,
        report_period=report_period,
        compliance=compliance,
        wait_time_rows=wait_rows,
        handling_time_rows=handling_rows,
        progress_rows=progress_rows,
        submission_checklist=checklist,
    )

    docx_path = write_form5(sections)

    citations = _build_citations(plan)

    return PeriodicReportResult(
        company_id=profile.company_id,
        company_name=profile.name,
        report_period=report_period,
        eligibility_categories=list(plan.eligibility.categories),
        compliance=compliance,
        wait_time_rows=wait_rows,
        handling_time_rows=handling_rows,
        progress_rows=progress_rows,
        submission_checklist=checklist,
        files={"docx": str(docx_path)},
        citations=citations,
        freshness_warnings=all_warnings(),
        data_source=profile.data_source,
    )


def _build_compliance(
    wait_rows: list[WaitTimeRow],
    handling_rows: list[HandlingTimeRow],
) -> ComplianceReport:
    """計測データから改善基準告示の遵守状況を構築する。

    荷待ち時間・荷役等時間の最大値を計測データから取得し、
    その他の項目は標準的な遵守値（サンプル前提）を埋める。
    """
    waiting_max = max((w.max_minutes for w in wait_rows), default=None)
    handling_max = max((h.max_minutes for h in handling_rows), default=None)

    # サンプル企業はいずれも改善基準告示の遵守を前提（実データはフェーズ4.0）
    return check_truck_driver_compliance(
        daily_working_hours_max=12.5,        # 13h 基準内
        annual_working_hours=2950.0,          # 3300h 基準内
        annual_overtime_hours=850.0,          # 960h 基準内
        waiting_minutes_max=waiting_max,
        handling_minutes_max=handling_max,
        rest_hours_min=11.0,                  # 原則 11h 遵守
    )


def _build_progress_rows(plan: PlanDraftResult) -> list[ProgressRow]:
    """中長期計画 vs 実績ギャップの行リストを構築する。

    plan.target_proposal の各目標に対して、初年度の進捗を「△ 継続対応」中心で配置。
    計画期間 5 年の初年度なので「達成」は限定的に。
    """
    rows: list[ProgressRow] = []

    # 数値目標 4 つに対する進捗（初年度想定で 30-50% 進捗）
    for t in plan.target_proposal.targets:
        plan_target = (
            f"{t.proposed_target:.1f}{t.proposed_target_unit}（{t.target_year}年目標）"
        )
        if t.current_industry_avg is not None:
            actual_label = (
                f"業界平均水準（{t.current_industry_avg:.1f}{t.current_industry_avg_unit}）"
                "から計画値へ初年度 30% 進捗"
            )
        else:
            actual_label = "計測データを蓄積中（初年度・基準値設定段階）"
        rows.append(ProgressRow(
            measure_name=t.name,
            plan_target=plan_target,
            actual_result=actual_label,
            status_mark="△ 継続対応",
        ))

    # 主要施策（simulation）に対する初年度進捗
    for m in plan.simulation.measures[:3]:
        if m.cost_saving_jpy_per_year:
            target_text = (
                f"年間 約{m.cost_saving_jpy_per_year / 1e8:.2f}億円のコスト削減"
            )
            actual_text = "初年度は試行導入。本格展開は 2027 年度以降"
        else:
            target_text = m.description[:40] + "…" if len(m.description) > 40 else m.description
            actual_text = "施策の実施計画策定中"
        rows.append(ProgressRow(
            measure_name=m.name,
            plan_target=target_text,
            actual_result=actual_text,
            status_mark="△ 継続対応",
        ))

    return rows


def _build_citations(plan: PlanDraftResult) -> list[Citation]:
    """様式第5 出典リスト（条文 + 改善基準告示 + CO2 ガイドライン）。"""
    citations: list[Citation] = [
        improvement_standards_citation(),
        co2_factors_citation(),
    ]
    if "chain_franchise" in plan.eligibility.categories:
        citations.append(logistics_efficiency_law_article65_citation())
    elif any(
        c in plan.eligibility.categories
        for c in ("first_class_shipper", "second_class_shipper")
    ):
        citations.append(logistics_efficiency_law_article46_citation())
    if plan.eligibility.must_appoint_clo:
        citations.append(logistics_efficiency_law_article66_citation())
    return citations


def build_periodic_report_summary(r: PeriodicReportResult) -> str:
    """PeriodicReportResult から CLO 向けサマリーテキストを生成する。"""
    lines: list[str] = [
        f"=== 定期報告書（様式第5）ドラフト: {r.company_name} ===",
        f"報告対象期間: {r.report_period}",
        f"区分: {' / '.join(r.eligibility_categories) or '該当なし'}",
        "",
        "【生成成果物】",
        f"  Word（様式第5・国交省提出フォーマット）: {r.files.get('docx', '(未生成)')}",
        "",
        "【Ⅱ 判断基準の遵守状況】",
        f"  総合判定: {r.compliance.summary}",
    ]
    for item in r.compliance.items:
        lines.append(f"  ・{item.to_form5_line()}")

    lines += [
        "",
        "【Ⅲ 追加措置】",
        (
            "  該当なし（全項目遵守）"
            if not r.compliance.additional_measures_required
            else "  違反／未計測項目あり — 追加措置を様式第5 Ⅲ に記載"
        ),
        "",
        "【Ⅳ 計測データ サマリー】",
    ]
    if r.wait_time_rows:
        max_wait = max(w.max_minutes for w in r.wait_time_rows)
        avg_wait = sum(w.average_minutes for w in r.wait_time_rows) / len(r.wait_time_rows)
        total_over = sum(w.over_2h_count for w in r.wait_time_rows)
        lines.append(
            f"  荷待ち時間: 平均 {avg_wait:.0f}分 / 最大 {max_wait:.0f}分 "
            f"/ 2時間超 {total_over}件"
        )
    else:
        lines.append("  荷待ち時間: 計測データなし（計測体制整備が必要）")

    if r.handling_time_rows:
        max_h = max(h.max_minutes for h in r.handling_time_rows)
        avg_h = sum(h.average_minutes for h in r.handling_time_rows) / len(r.handling_time_rows)
        lines.append(
            f"  荷役等時間: 平均 {avg_h:.0f}分 / 最大 {max_h:.0f}分"
        )
    elif "chain_franchise" in r.eligibility_categories:
        lines.append(
            "  荷役等時間: 連鎖化事業者は判断基準対象外（参考記載なし）"
        )

    lines += [
        "",
        f"【Ⅴ 中長期計画の進捗】 {len(r.progress_rows)} 項目",
    ]
    for p in r.progress_rows[:6]:
        lines.append(f"  {p.status_mark} {p.measure_name}: {p.plan_target}")

    lines += [
        "",
        "",
    ]
    lines.extend(r.submission_checklist.to_text_lines())

    lines += [
        "",
        "【次のアクション】",
        "  1. 計測データを自社実データに差し替え（フェーズ4.0「実データ入力フォーム」で対応予定）",
        "  2. Word（様式第5）を社内レビュー → CLO 署名 → 毎年 7 月末までに国交省提出",
        "  3. 違反項目があれば Ⅲ 追加措置欄を埋めて中長期計画書（様式第3）の改定に反映",
        "",
        _format_data_source_note(r.data_source),
    ]

    return "\n".join(lines)


def _format_data_source_note(data_source: DataSource) -> str:
    """データ出所注釈をサマリー末尾に表示する。"""
    if data_source == "actual":
        return "※ 入力プロフィールは自社実績データ（actual）に基づく。"
    return (
        "※ 入力プロフィールは業界統計からの推計値（estimated）。"
        "提出前には自社実測データへの差し替えを推奨。"
    )


__all__ = [
    "PeriodicReportResult",
    "build_periodic_report_summary",
    "generate_periodic_report",
]
