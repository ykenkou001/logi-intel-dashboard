"""特定荷主3区分の適用判定エンジン。

法令根拠:
    物資の流通の効率化に関する法律（改正物流効率化法）
    - 第46条: 特定荷主（年間取扱貨物 9 万トン以上）
        - 特定第一種荷主（発荷主）
        - 特定第二種荷主（着荷主）
    - 第65条: 特定連鎖化事業者（フランチャイズ本部・販売額ベース）

判定の入力:
    - jsic_code: 自社業種（JSIC 細分類4桁）
    - annual_freight_tons_total: 年間取扱貨物量（実測 or 推計）
    - annual_revenue_jpy: 年間売上（連鎖化判定用）
    - is_chain_franchise: 連鎖化事業者か（明示的指定）

判定の出力:
    EligibilityResult — 該当区分の集合と、判定根拠の説明
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from core.static.industry_freight_coef import estimate_freight_tons
from core.static.jsic import category_of

# 特定荷主の閾値（トン/年）
SHIPPER_THRESHOLD_TONS: int = 90_000

# 特定連鎖化事業者の閾値（円/年・販売額）
# 注: 法令上は「直近2事業年度の売上の平均が一定額以上」の規定。
# 実装上は単年売上で簡易判定し、ボーダーラインは個別精査を促す。
CHAIN_FRANCHISE_THRESHOLD_JPY: int = 100_000_000_000  # 1,000 億円（暫定値）

EligibilityCategory = Literal[
    "first_class_shipper",      # 特定第一種荷主（発荷主）
    "second_class_shipper",     # 特定第二種荷主（着荷主）
    "chain_franchise",          # 特定連鎖化事業者
    "none",                     # 該当なし
]


@dataclass(frozen=True)
class EligibilityResult:
    """適用判定の結果。"""

    categories: list[EligibilityCategory]   # 該当区分（複数該当あり得る）
    annual_freight_tons_used: float | None  # 判定に使用した取扱量（実測 or 推計値）
    is_estimate: bool                       # 取扱量が推計値か
    reasons: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def applies(self) -> bool:
        """いずれかの区分に該当するか。"""
        return self.categories != ["none"] and len(self.categories) > 0

    @property
    def must_appoint_clo(self) -> bool:
        """CLO 選任義務があるか。"""
        return self.applies


def evaluate_eligibility(
    jsic_code: str,
    annual_freight_tons_total: float | None = None,
    annual_revenue_jpy: int | None = None,
    is_chain_franchise: bool = False,
    override_first_class: bool | None = None,
    override_second_class: bool | None = None,
) -> EligibilityResult:
    """3区分の適用判定を実行する。

    Args:
        jsic_code: 自社の JSIC 細分類4桁
        annual_freight_tons_total: 年間取扱貨物量（実測トン）。None なら売上から推計
        annual_revenue_jpy: 年間売上（円）。連鎖化判定用 + 取扱量推計のフォールバック
        is_chain_franchise: 連鎖化事業者として運営しているか（明示）
        override_first_class: 第一種荷主として明示的に該当 / 非該当指定（ヒアリング結果優先）
        override_second_class: 第二種荷主として明示的に該当 / 非該当指定

    Returns:
        EligibilityResult
    """
    categories: list[EligibilityCategory] = []
    reasons: list[str] = []
    notes: list[str] = []

    # 取扱量の確定（実測 > 推計 > 不明）
    tons_used = annual_freight_tons_total
    is_estimate = False
    if tons_used is None and annual_revenue_jpy is not None:
        tons_used = estimate_freight_tons(jsic_code, annual_revenue_jpy)
        if tons_used is not None:
            is_estimate = True
            notes.append(
                f"年間取扱量が未指定のため売上から推計: 約 {tons_used:,.0f} トン "
                f"（業種別物流原単位 by jsic_code={jsic_code}）"
            )

    # 連鎖化事業者の判定（第65条）
    if is_chain_franchise:
        # 連鎖化フラグ ON ＋ 売上が閾値超 → 該当
        if annual_revenue_jpy is not None and annual_revenue_jpy >= CHAIN_FRANCHISE_THRESHOLD_JPY:
            categories.append("chain_franchise")
            reasons.append(
                f"連鎖化事業者（売上 {annual_revenue_jpy:,} 円 ≥ "
                f"閾値 {CHAIN_FRANCHISE_THRESHOLD_JPY:,} 円）→ 第65条適用"
            )
        else:
            notes.append(
                "連鎖化フラグは ON だが売上が連鎖化閾値未満。法令の正確な閾値は"
                "「直近2事業年度平均売上」のため、個別精査を推奨。"
            )

    # 特定第一種荷主・第二種荷主の判定（第46条）
    cat = category_of(jsic_code)
    is_shipper_industry = cat in ("manufacturing", "wholesale", "retail")

    if not is_shipper_industry and cat != "chain_franchise":
        notes.append(
            f"jsic_code={jsic_code} は荷主業種（製造/卸売/小売）として登録されていません。"
            "運送業者（H 大分類）の場合、本判定の対象外です。"
        )

    # 第一種（発荷主）
    if override_first_class is True:
        categories.append("first_class_shipper")
        reasons.append("第一種荷主に明示的に指定（ユーザー入力）")
    elif override_first_class is False:
        notes.append("第一種荷主に該当しないと明示的に指定")
    elif is_shipper_industry and tons_used is not None and tons_used >= SHIPPER_THRESHOLD_TONS:
        categories.append("first_class_shipper")
        reasons.append(
            f"年間取扱貨物 {tons_used:,.0f} トン ≥ 閾値 {SHIPPER_THRESHOLD_TONS:,} トン "
            f"→ 第46条 特定第一種荷主に該当{'（推計値）' if is_estimate else ''}"
        )

    # 第二種（着荷主）— 多くの企業は発荷主と着荷主の両方に該当
    if override_second_class is True:
        categories.append("second_class_shipper")
        reasons.append("第二種荷主に明示的に指定（ユーザー入力）")
    elif override_second_class is False:
        notes.append("第二種荷主に該当しないと明示的に指定")
    elif is_shipper_industry and tons_used is not None and tons_used >= SHIPPER_THRESHOLD_TONS:
        # 既定では第一種に該当する企業は第二種にも該当する想定（仕入れ・原材料受入れあり）
        categories.append("second_class_shipper")
        reasons.append(
            "原材料・仕入の年間入荷量も閾値以上の可能性が高いため第二種に該当 "
            "（明示的に override_second_class=False で除外可能）"
        )

    # 9万トン近辺で推計判定の場合は注意喚起
    if (
        is_estimate
        and tons_used is not None
        and SHIPPER_THRESHOLD_TONS * 0.7 < tons_used < SHIPPER_THRESHOLD_TONS * 1.3
    ):
        notes.append(
            "⚠️ 取扱量が9万トン基準の前後 30% 以内（ボーダーライン）。"
            "推計値ではなく実績データで再判定することを強く推奨。"
        )

    if not categories:
        categories.append("none")
        reasons.append("いずれの区分にも該当しない（CLO 選任義務なし）")

    return EligibilityResult(
        categories=categories,
        annual_freight_tons_used=tons_used,
        is_estimate=is_estimate,
        reasons=reasons,
        notes=notes,
    )
