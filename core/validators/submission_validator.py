"""CLO 計画書（様式第3別紙）の提出前バリデータ。

国交省への提出直前に、生成済みの計画書ドラフトに対して以下を機械的に検査する:

1. **網羅性**: 様式第3 必須3項目 ×（実施措置／計画内容／実施時期）= 9 項目が揃っているか
2. **数値整合性**: 施策効果（CO2 / コスト / 投資 / 回収期間）が非負・桁妥当か
3. **出典欠落**: 主要根拠（CO2目標・積載率・モーダルシフト等）の citation が揃っているか
4. **告示準拠**: 数値目標が改善基準告示・物流分野国家目標と矛盾しないか

設計方針:
    - 入力は `PlanDraftResult` または「サンプル企業ID」のいずれか
    - 出力は `ValidationReport`（経営会議で「準拠率 X%」を言える形）
    - 連鎖化事業者は「荷役等時間短縮」を必須から除外
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from docx import Document

from core.analytics.plan_draft import PlanDraftResult, generate_plan_draft

Severity = Literal["error", "warning", "info"]
IssueCategory = Literal[
    "form3_completeness",
    "numeric_consistency",
    "citation",
    "compliance",
]

# 様式第3 で必須となる 3 セクション（連鎖化事業者は荷役等を除外）
REQUIRED_SECTIONS_NON_CHAIN: tuple[str, ...] = (
    "積載率向上",
    "荷待ち時間短縮",
    "荷役等時間短縮",
)
REQUIRED_SECTIONS_CHAIN: tuple[str, ...] = (
    "積載率向上",
    "荷待ち時間短縮",
)

# 各セクションで埋まっているべき列見出し
REQUIRED_COLUMNS: tuple[str, ...] = ("実施措置", "計画内容", "実施時期")

# 出典で必ずカバーされていてほしいキーワード（label or url 部分一致）
REQUIRED_CITATION_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("co2_factors", "CO2排出量算定"),
    ("logistics_efficiency_law", "物流効率化法"),
    ("improvement_standards", "改善基準"),
)

# 桁妥当性レンジ（業界統計から外れた値を弾く）
MIN_CO2_REDUCTION_KG_PER_YEAR: float = 0.0
MAX_CO2_REDUCTION_KG_PER_YEAR: float = 1_000_000_000.0  # 100 万トン-CO2/年（極端値検出）
MAX_COST_SAVING_JPY_PER_YEAR: float = 100_000_000_000.0  # 1,000 億円/年
MAX_INVESTMENT_JPY: float = 50_000_000_000.0  # 500 億円
MAX_PAYBACK_YEARS: float = 30.0  # 30 年（計画期間 5 年に対し過大）

# 業界平均売上比の信頼性しきい値（reference_industry_sense_ranges.md と整合）
# 業界統計の母集団は小規模事業所中心のため、大企業の単純比較は桁外れになりやすい。
MAX_REVENUE_VS_AVG_PCT_RELIABLE: float = 1000.0


@dataclass(frozen=True)
class ValidationIssue:
    """個別の検証指摘。"""

    severity: Severity
    category: IssueCategory
    code: str
    message: str
    suggestion: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "category": self.category,
            "code": self.code,
            "message": self.message,
            "suggestion": self.suggestion,
        }


@dataclass
class ValidationReport:
    """提出前バリデータの結果。"""

    company_id: str
    company_name: str
    overall_pass: bool                    # error が 0 件か
    compliance_score_pct: float           # 法定様式準拠率（0〜100）
    checked_files: dict[str, str]         # 検査対象ファイル
    issues: list[ValidationIssue] = field(default_factory=list)

    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    def to_dict(self) -> dict[str, object]:
        return {
            "company_id": self.company_id,
            "company_name": self.company_name,
            "overall_pass": self.overall_pass,
            "compliance_score_pct": round(self.compliance_score_pct, 1),
            "checked_files": dict(self.checked_files),
            "error_count": len(self.errors()),
            "warning_count": len(self.warnings()),
            "issues": [i.to_dict() for i in self.issues],
        }


async def validate_submission(
    company_id: str,
    plan_draft: PlanDraftResult | None = None,
) -> ValidationReport:
    """サンプル企業ID から計画書ドラフトを生成（または再利用）し、提出前検査を実施する。

    Args:
        company_id: サンプル企業ID（例: "sample_mfg_01"）
        plan_draft: 既に `generate_plan_draft` で生成済みの結果。
            未指定なら本関数内で生成する。

    Returns:
        ValidationReport: 検査結果（指摘リストと準拠率）
    """
    if plan_draft is None:
        plan_draft = await generate_plan_draft(company_id)

    issues: list[ValidationIssue] = []

    # 1. 様式第3 docx の網羅性
    docx_path = plan_draft.files.get("docx")
    if docx_path is None:
        issues.append(ValidationIssue(
            severity="error",
            category="form3_completeness",
            code="FORM3_FILE_MISSING",
            message="様式第3別紙（docx）が生成されていません。",
            suggestion="logi_clo_plan_draft を先に実行してください。",
        ))
    else:
        is_chain = "chain_franchise" in (plan_draft.eligibility.categories or [])
        issues.extend(_validate_form3_completeness(
            Path(docx_path),
            is_chain_franchise=is_chain,
        ))

    # 2. 数値整合性
    issues.extend(_validate_numeric_consistency(plan_draft))

    # 3. 出典の網羅性
    issues.extend(_validate_citations(plan_draft))

    # 4. 告示・国家目標との整合
    issues.extend(_validate_compliance(plan_draft))

    error_count = sum(1 for i in issues if i.severity == "error")
    warning_count = sum(1 for i in issues if i.severity == "warning")
    overall_pass = error_count == 0

    score = _compute_compliance_score(error_count, warning_count, total_checks=20)

    return ValidationReport(
        company_id=plan_draft.company_id,
        company_name=plan_draft.company_name,
        overall_pass=overall_pass,
        compliance_score_pct=score,
        checked_files=dict(plan_draft.files),
        issues=issues,
    )


def _validate_form3_completeness(
    docx_path: Path,
    is_chain_franchise: bool,
) -> list[ValidationIssue]:
    """様式第3 docx を読み、必須セクション × 必須3列が埋まっているか検査する。"""
    issues: list[ValidationIssue] = []

    if not docx_path.exists():
        issues.append(ValidationIssue(
            severity="error",
            category="form3_completeness",
            code="FORM3_FILE_NOT_FOUND",
            message=f"様式第3 docx が見つかりません: {docx_path}",
        ))
        return issues

    doc = Document(str(docx_path))
    headings = [p.text for p in doc.paragraphs if p.style and p.style.name.startswith("Heading")]
    heading_text = " / ".join(headings)

    required = REQUIRED_SECTIONS_CHAIN if is_chain_franchise else REQUIRED_SECTIONS_NON_CHAIN

    for section_name in required:
        if not any(section_name in h for h in headings):
            issues.append(ValidationIssue(
                severity="error",
                category="form3_completeness",
                code=f"FORM3_SECTION_MISSING_{_to_code(section_name)}",
                message=f"必須セクション「{section_name}」が様式第3 に含まれていません。",
                suggestion=(
                    f"core/analytics/plan_draft.py の _build_form3 で "
                    f"PlanSection を「{section_name}」を含めて追加してください。"
                ),
            ))

    # 各セクションの表の中身を検査
    for table in doc.tables:
        # ヘッダ行が「実施措置／計画内容／実施時期」のテーブルだけが対象
        if len(table.rows) < 1:
            continue
        header_cells = [c.text.strip() for c in table.rows[0].cells]
        if not all(col in header_cells for col in REQUIRED_COLUMNS):
            continue
        # データ行を検査
        for row_idx, row in enumerate(table.rows[1:], start=1):
            cells = {
                header_cells[i]: row.cells[i].text.strip()
                for i in range(min(len(header_cells), len(row.cells)))
            }
            for col in REQUIRED_COLUMNS:
                value = cells.get(col, "").strip()
                if not value or value in {"（記載なし）", "未定", "TBD", "-"}:
                    issues.append(ValidationIssue(
                        severity="error",
                        category="form3_completeness",
                        code="FORM3_CELL_EMPTY",
                        message=(
                            f"様式第3 の表で「{col}」欄が空欄（行 {row_idx}）です。"
                            f"見出し: {heading_text[:60]}…"
                        ),
                        suggestion=f"「{col}」を具体的な値で埋めてください（提出不可）。",
                    ))

    # 表自体が見つからない場合
    has_measure_table = any(
        all(col in [c.text.strip() for c in t.rows[0].cells] for col in REQUIRED_COLUMNS)
        for t in doc.tables if len(t.rows) >= 1
    )
    if not has_measure_table:
        issues.append(ValidationIssue(
            severity="error",
            category="form3_completeness",
            code="FORM3_MEASURE_TABLE_MISSING",
            message="様式第3 に「実施措置／計画内容／実施時期」表が見つかりません。",
            suggestion=(
                "docx_form3_writer.write_form3 で sections に PlanSection を渡してください。"
            ),
        ))

    return issues


def _validate_numeric_consistency(plan: PlanDraftResult) -> list[ValidationIssue]:
    """シミュレーション数値と数値目標の整合性を検査する。"""
    issues: list[ValidationIssue] = []

    for m in plan.simulation.measures:
        co2 = m.co2_reduction_kg_per_year
        if co2 is not None:
            if co2 < MIN_CO2_REDUCTION_KG_PER_YEAR:
                issues.append(ValidationIssue(
                    severity="error",
                    category="numeric_consistency",
                    code="CO2_NEGATIVE",
                    message=(
                        f"施策「{m.name}」のCO2削減量が負値: {co2:,.0f}kg"
                    ),
                    suggestion="計算ロジックの符号を確認してください。",
                ))
            elif co2 > MAX_CO2_REDUCTION_KG_PER_YEAR:
                issues.append(ValidationIssue(
                    severity="warning",
                    category="numeric_consistency",
                    code="CO2_EXCESSIVE",
                    message=(
                        f"施策「{m.name}」のCO2削減量 "
                        f"{co2 / 1000:,.0f}t が上限 "
                        f"{MAX_CO2_REDUCTION_KG_PER_YEAR / 1000:,.0f}t を超過。"
                        "桁を確認してください。"
                    ),
                ))

        cost = m.cost_saving_jpy_per_year
        if cost is not None and cost < 0:
            issues.append(ValidationIssue(
                severity="error",
                category="numeric_consistency",
                code="COST_NEGATIVE",
                message=(
                    f"施策「{m.name}」のコスト削減額が負値: {cost:,.0f}円"
                ),
            ))
        if cost is not None and cost > MAX_COST_SAVING_JPY_PER_YEAR:
            issues.append(ValidationIssue(
                severity="warning",
                category="numeric_consistency",
                code="COST_EXCESSIVE",
                message=(
                    f"施策「{m.name}」のコスト削減額 "
                    f"{cost / 1e8:,.1f}億円が上限を超過。桁を確認してください。"
                ),
            ))

        if m.investment_jpy < 0:
            issues.append(ValidationIssue(
                severity="error",
                category="numeric_consistency",
                code="INVESTMENT_NEGATIVE",
                message=f"施策「{m.name}」の投資額が負値: {m.investment_jpy:,.0f}円",
            ))
        elif m.investment_jpy > MAX_INVESTMENT_JPY:
            issues.append(ValidationIssue(
                severity="warning",
                category="numeric_consistency",
                code="INVESTMENT_EXCESSIVE",
                message=(
                    f"施策「{m.name}」の投資額 {m.investment_jpy / 1e8:,.1f}億円が "
                    f"上限 {MAX_INVESTMENT_JPY / 1e8:,.0f}億円を超過。桁を確認してください。"
                ),
            ))

        if m.payback_years is not None and m.payback_years > MAX_PAYBACK_YEARS:
            issues.append(ValidationIssue(
                severity="warning",
                category="numeric_consistency",
                code="PAYBACK_TOO_LONG",
                message=(
                    f"施策「{m.name}」の単純回収期間 {m.payback_years:.1f} 年が "
                    f"目安 {MAX_PAYBACK_YEARS:.0f} 年を超過。経済性を再確認してください。"
                ),
            ))

    # 数値目標の検査
    for t in plan.target_proposal.targets:
        if t.proposed_target_unit.startswith("%") and abs(t.proposed_target) > 100.0:
            issues.append(ValidationIssue(
                severity="error",
                category="numeric_consistency",
                code="TARGET_PCT_OUT_OF_RANGE",
                message=(
                    f"数値目標「{t.name}」の値 {t.proposed_target} は %換算で範囲外です。"
                ),
            ))

    # 業界平均売上比の信頼性チェック
    # 業界統計の母集団（小規模事業所中心）と自社規模が乖離すると桁外れの値が出る。
    # 経営会議で単純表示すると defensibility が崩れるため warning を発行する。
    revenue_ratio = plan.benchmark.revenue_vs_avg_pct
    if revenue_ratio is not None and revenue_ratio > MAX_REVENUE_VS_AVG_PCT_RELIABLE:
        issues.append(ValidationIssue(
            severity="warning",
            category="numeric_consistency",
            code="BENCHMARK_RATIO_OUTLIER",
            message=(
                f"業界平均売上比 {revenue_ratio:.0f}% が信頼性しきい値 "
                f"{MAX_REVENUE_VS_AVG_PCT_RELIABLE:.0f}% を超過。"
                "業界統計の母集団と自社規模の乖離が大きく、経営会議では参考値として扱ってください。"
            ),
            suggestion=(
                "業界平均比の単純表示は避け、相対参照（規模優位企業として上位帯）"
                "に置き換えてください。"
            ),
        ))

    return issues


def _validate_citations(plan: PlanDraftResult) -> list[ValidationIssue]:
    """出典が主要キーワードを網羅しているかを検査する。"""
    issues: list[ValidationIssue] = []

    if not plan.citations:
        issues.append(ValidationIssue(
            severity="error",
            category="citation",
            code="CITATIONS_EMPTY",
            message="計画書ドラフトに出典が 1 件も付与されていません。",
            suggestion="経営会議で「出典は？」と聞かれて即答できる状態を担保してください。",
        ))
        return issues

    joined_text = " ".join(c.label + " " + c.url for c in plan.citations).lower()
    # 必須キーワード（CO2 と物流効率化法）— 改善基準は施策側でカバーされるため warning に留める
    if "co2" not in joined_text and "排出" not in joined_text and "ガイドライン" not in joined_text:
        issues.append(ValidationIssue(
            severity="warning",
            category="citation",
            code="CITATION_CO2_GUIDELINE_MISSING",
            message="CO2排出量算定ガイドラインの出典が見当たりません。",
            suggestion=(
                "core/export/citation.py:co2_factors_citation() を citations に追加してください。"
            ),
        ))
    if "物流効率化法" not in joined_text and "logistics" not in joined_text:
        issues.append(ValidationIssue(
            severity="error",
            category="citation",
            code="CITATION_EFFICIENCY_LAW_MISSING",
            message="物流効率化法（根拠法）の出典が citations に含まれていません。",
            suggestion="logistics_efficiency_law_citation() を citations に追加してください。",
        ))

    # 各 citation の URL チェック
    for c in plan.citations:
        if not c.url or not c.url.startswith("http"):
            issues.append(ValidationIssue(
                severity="error",
                category="citation",
                code="CITATION_URL_INVALID",
                message=f"出典「{c.label}」の URL が不正: '{c.url}'",
            ))

    return issues


def _validate_compliance(plan: PlanDraftResult) -> list[ValidationIssue]:
    """改善基準告示・物流分野国家目標との整合性を検査する。"""
    issues: list[ValidationIssue] = []

    # CLO 選任義務の有無と計画書の整合性
    if not plan.eligibility.must_appoint_clo:
        issues.append(ValidationIssue(
            severity="info",
            category="compliance",
            code="CLO_NOT_REQUIRED",
            message=(
                "判定上 CLO 選任義務はありません。"
                "それでも計画書ドラフトを提出する場合は任意の届出となります。"
            ),
        ))

    # CO2 削減目標が国家目標 ▲23.4% を下回っていないか
    co2_target = next(
        (t for t in plan.target_proposal.targets if "CO2" in t.name),
        None,
    )
    if co2_target is not None and abs(co2_target.proposed_target) < 23.0:
        issues.append(ValidationIssue(
            severity="warning",
            category="compliance",
            code="CO2_BELOW_NATIONAL_TARGET",
            message=(
                f"CO2 原単位削減目標 {co2_target.proposed_target}% が"
                "物流分野国家目標 ▲23.4% を下回っています。"
            ),
            suggestion="国家目標と整合する水準まで引き上げを検討してください。",
        ))

    # 積載率目標が現実的範囲（業界平均 38% 未満や 100% 超）でないか
    load_target = next(
        (t for t in plan.target_proposal.targets if "積載率" in t.name),
        None,
    )
    if load_target is not None:
        if load_target.proposed_target > 100.0:
            issues.append(ValidationIssue(
                severity="error",
                category="compliance",
                code="LOAD_FACTOR_OVER_100",
                message=f"積載率目標 {load_target.proposed_target}% が物理的上限 100% を超過。",
            ))
        elif load_target.proposed_target < (load_target.current_industry_avg or 0):
            issues.append(ValidationIssue(
                severity="warning",
                category="compliance",
                code="LOAD_FACTOR_BELOW_INDUSTRY_AVG",
                message=(
                    f"積載率目標 {load_target.proposed_target}% が業界平均 "
                    f"{load_target.current_industry_avg}% を下回っています。"
                ),
            ))

    return issues


def _compute_compliance_score(
    error_count: int, warning_count: int, total_checks: int,
) -> float:
    """準拠率（0〜100%）を算出する。

    error は 1 件あたり -10pt、warning は -3pt。下限 0、上限 100。
    """
    score = 100.0 - error_count * 10.0 - warning_count * 3.0
    return max(0.0, min(100.0, score))


def _to_code(label: str) -> str:
    """日本語ラベルを ASCII コード文字列に変換（issue code 用）。"""
    mapping = {
        "積載率向上": "LOAD",
        "荷待ち時間短縮": "WAIT",
        "荷役等時間短縮": "LOADING",
    }
    return mapping.get(label, label.encode("ascii", "ignore").decode() or "UNKNOWN")


def build_validation_summary(report: ValidationReport) -> str:
    """ValidationReport から CLO 向けサマリーテキストを生成する。"""
    lines: list[str] = [
        f"=== 提出前バリデータ結果: {report.company_name} ===",
        f"総合判定: {'✅ PASS（提出可）' if report.overall_pass else '❌ FAIL（提出前修正必須）'}",
        f"法定様式準拠率: {report.compliance_score_pct:.1f}%",
        f"  エラー: {len(report.errors())} 件 / 警告: {len(report.warnings())} 件",
        "",
    ]

    if report.errors():
        lines.append("【エラー（提出前修正必須）】")
        for i in report.errors():
            lines.append(f"  ❌ [{i.code}] {i.message}")
            if i.suggestion:
                lines.append(f"     → {i.suggestion}")
        lines.append("")

    if report.warnings():
        lines.append("【警告（提出前確認推奨）】")
        for i in report.warnings():
            lines.append(f"  ⚠️ [{i.code}] {i.message}")
            if i.suggestion:
                lines.append(f"     → {i.suggestion}")
        lines.append("")

    info_issues = [i for i in report.issues if i.severity == "info"]
    if info_issues:
        lines.append("【情報】")
        for i in info_issues:
            lines.append(f"  ℹ️ {i.message}")
        lines.append("")

    lines += [
        "【検査対象ファイル】",
    ]
    for key, path in report.checked_files.items():
        lines.append(f"  {key}: {path}")

    if report.overall_pass:
        lines += [
            "",
            "【次のアクション】",
            "  1. 警告項目を経営会議で確認・必要に応じて修正",
            "  2. 様式第3別紙（docx）に CLO 署名・押印",
            "  3. 2026年10月末までに国土交通省 e-Gov 電子申請で提出",
        ]
    else:
        lines += [
            "",
            "【次のアクション】",
            "  1. 上記エラーを順次修正（plan_draft 再生成 → 再検査）",
            "  2. 全エラー解消後に CLO 署名・押印",
            "  3. 提出は 2026年10月末まで（罰則: 計画未達は勧告・命令・企業名公表）",
        ]

    return "\n".join(lines)
