"""特定荷主3区分 適用判定の分析サマリー生成。

本モジュールは判定ロジック自体を持たず、core/legal/eligibility.py の
`evaluate_eligibility` 結果を CLO 計画書／経営会議向けの読みやすい
サマリーに整形することに専念する。
"""
from __future__ import annotations

from core.legal.eligibility import EligibilityCategory, EligibilityResult
from core.static.jsic import lookup

_CATEGORY_LABELS: dict[EligibilityCategory, str] = {
    "first_class_shipper": "特定第一種荷主（発荷主）",
    "second_class_shipper": "特定第二種荷主（着荷主）",
    "chain_franchise": "特定連鎖化事業者",
    "none": "該当なし",
}

_BUSINESS_CATEGORY_LABELS: dict[str, str] = {
    "manufacturing": "製造業",
    "wholesale": "卸売業",
    "retail": "小売業",
    "chain_franchise": "連鎖化事業者",
    "transport": "運輸業",
    "other": "その他",
}


def build_eligibility_summary(
    result: EligibilityResult,
    jsic_code: str,
    annual_revenue_jpy: int | None,
    annual_freight_tons_total: float | None,
    is_chain_franchise: bool,
) -> str:
    """EligibilityResult から CLO 計画書用のサマリーテキストを生成する。"""
    entry = lookup(jsic_code)
    jsic_name = entry.name if entry else "（未登録業種）"
    category_label = _BUSINESS_CATEGORY_LABELS.get(
        entry.category if entry else "other", "不明"
    )

    lines: list[str] = [
        "=== 特定荷主3区分 適用判定（物流効率化法 第46条 / 第65条）===",
        f"業種: {jsic_name}（{jsic_code}）/ {category_label}",
    ]

    inputs: list[str] = []
    if annual_revenue_jpy is not None:
        inputs.append(f"年間売上 {annual_revenue_jpy / 1e8:.1f}億円")
    if annual_freight_tons_total is not None:
        inputs.append(f"取扱量 {annual_freight_tons_total:,.0f}トン（実測）")
    else:
        inputs.append("取扱量 未指定")
    inputs.append(f"連鎖化フラグ {'ON' if is_chain_franchise else 'OFF'}")
    lines.append(f"入力: {' / '.join(inputs)}")

    lines += [
        "",
        "【取扱量の確定】",
    ]
    if result.annual_freight_tons_used is not None:
        label = "推計値" if result.is_estimate else "実測値"
        lines.append(
            f"  {label}: 約 {result.annual_freight_tons_used:,.0f} トン / 年"
        )
    else:
        lines.append("  取扱量: 不明（売上・取扱量とも未指定または推計不可）")

    cat_labels = "、".join(_CATEGORY_LABELS.get(c, c) for c in result.categories)
    obligation = "✅ あり（CLO 選任義務）" if result.must_appoint_clo else "❌ なし"

    lines += [
        "",
        "【判定結果】",
        f"  該当区分: {cat_labels}",
        f"  CLO 選任義務: {obligation}",
        "",
        "【判定根拠】",
    ]
    for reason in result.reasons:
        lines.append(f"  ・{reason}")

    if result.notes:
        lines += [
            "",
            "【注意事項】",
        ]
        for note in result.notes:
            lines.append(f"  ・{note}")

    lines += [
        "",
        "【法令根拠】",
        "  ・物資の流通の効率化に関する法律 第46条（特定荷主・年間取扱9万トン以上）",
        "  ・物資の流通の効率化に関する法律 第65条（特定連鎖化事業者）",
        "  ・選任義務違反は最大 100万円以下の罰金（同法 第163条）",
    ]

    if result.must_appoint_clo:
        lines += [
            "",
            "【次のアクション】",
            "  → 中長期計画書（様式第3別紙）の作成が必要（2026年10月末 初回提出期限）",
            "  → Step 4 の数値目標提案・Step 7 の計画書ドラフト生成へ進めます",
        ]

    return "\n".join(lines)
