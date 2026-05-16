"""CLO 義務対象スクリーニング判定（`/check` Web 画面用）。

`core/legal/eligibility.py` が荷主3区分の細分化（第一種/第二種/連鎖化）に
踏み込むのに対し、本モジュールは **30 秒で対象か判定する入口** として
「荷主・連鎖化・倉庫・運送」4 区分の粗粒度スクリーニングを行う。

法令根拠:
    物資の流通の効率化に関する法律（改正物流効率化法）
    - 第46条: 特定荷主（年間取扱貨物 9 万トン以上）約 3,200 社
    - 第65条: 特定連鎖化事業者（フランチャイズ本部）
    - 別途規定: 特定倉庫業者（年間入庫貨物 70 万トン以上）約 70 社
    - 別途規定: 特定貨物自動車運送事業者等（保有車両 150 台以上）約 790 社

    出典: 国交省ポータル
        https://www.revised-logistics-act-portal.mlit.go.jp/designation/
    施行日: 2026-04-01
    初回計画提出期限: 2026-10-31
    罰則:
        - CLO 未選任 100 万円以下の罰金
        - 届出懈怠 20 万円以下の過料

判定の方針:
    - 利用者が「正確な実測値」を持たない前提で **バンド（範囲）入力** を受け付ける
    - 閾値前後の bands は `gray_zone` として扱い、実測再確認を促す
    - 4 区分は **互いに排他ではない**（複数該当あり得る）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

ScreeningCategory = Literal[
    "shipper",  # 特定荷主（第46条）
    "chain_franchise",  # 特定連鎖化事業者（第65条）
    "warehouse",  # 特定倉庫業者
    "freight_transport",  # 特定貨物自動車運送事業者等
]

Verdict = Literal["applies", "gray_zone", "not_applies"]

IndustryHint = Literal[
    "food",
    "chemical",
    "retail",
    "chain_franchise",
    "transport",
    "warehouse",
    "other",
]

FreightTonsBand = Literal["lt_10k", "10k_50k", "50k_90k", "ge_90k", "unknown"]
VehiclesBand = Literal["lt_50", "50_150", "ge_150", "none"]
WarehouseTonsBand = Literal["lt_100k", "100k_700k", "ge_700k", "none"]
CloStatus = Literal["appointed", "planning", "not_considered"]


# 閾値定数（法令準拠）
SHIPPER_THRESHOLD_TONS: int = 90_000
"""特定荷主の閾値（年間取扱貨物量・トン）。"""

WAREHOUSE_THRESHOLD_TONS: int = 700_000
"""特定倉庫業者の閾値（年間入庫貨物量・トン）。"""

FREIGHT_TRANSPORT_THRESHOLD_VEHICLES: int = 150
"""特定貨物自動車運送事業者等の閾値（保有車両台数）。"""

CHAIN_FRANCHISE_THRESHOLD_JPY: int = 100_000_000_000
"""特定連鎖化事業者の閾値（年間売上・円・暫定値）。"""

SUBMISSION_DEADLINE: date = date(2026, 10, 31)
"""初回中長期計画 提出期限。"""

ENFORCEMENT_DATE: date = date(2026, 4, 1)
"""改正物流効率化法 施行日。"""


@dataclass(frozen=True)
class ScreeningInput:
    """`/check` 画面からの入力。"""

    industry: IndustryHint
    freight_tons_band: FreightTonsBand
    vehicles_band: VehiclesBand
    warehouse_tons_band: WarehouseTonsBand
    annual_revenue_jpy: int | None = None
    clo_status: CloStatus = "not_considered"
    is_chain_franchise: bool = False


@dataclass(frozen=True)
class CategoryFinding:
    """1 区分の判定結果。"""

    category: ScreeningCategory
    verdict: Verdict
    reason: str
    legal_article: str
    threshold_label: str


@dataclass(frozen=True)
class ScreeningResult:
    """4 区分の総合判定結果。"""

    findings: list[CategoryFinding]
    notes: list[str] = field(default_factory=list)
    days_until_deadline: int = 0

    @property
    def applies_any(self) -> bool:
        """いずれかの区分で `applies` か。"""
        return any(f.verdict == "applies" for f in self.findings)

    @property
    def gray_zone_any(self) -> bool:
        """いずれかの区分で `gray_zone` か。"""
        return any(f.verdict == "gray_zone" for f in self.findings)

    @property
    def overall_verdict(self) -> Verdict:
        """画面上部に出す総合判定。

        - 1 件でも applies があれば applies
        - 1 件でも gray_zone があれば gray_zone
        - すべて not_applies なら not_applies
        """
        if self.applies_any:
            return "applies"
        if self.gray_zone_any:
            return "gray_zone"
        return "not_applies"


def _shipper_verdict(
    band: FreightTonsBand,
    industry: IndustryHint,
) -> CategoryFinding:
    """特定荷主の判定（第46条）。"""
    legal = "物流効率化法 第46条"
    threshold = f"年間取扱貨物 {SHIPPER_THRESHOLD_TONS:,} トン以上"

    # 運送・倉庫業を主たる業種とする企業は荷主区分の対象外（典型的に）
    if industry in ("transport", "warehouse"):
        return CategoryFinding(
            category="shipper",
            verdict="not_applies",
            reason="運輸・倉庫業を主たる業種とする企業は荷主区分の対象外（自社で発荷主・着荷主の運送を行う場合は個別精査）",
            legal_article=legal,
            threshold_label=threshold,
        )

    if band == "ge_90k":
        return CategoryFinding(
            category="shipper",
            verdict="applies",
            reason=(
                f"年間取扱貨物が {SHIPPER_THRESHOLD_TONS:,} トン以上 → "
                "特定荷主に該当（全国 約 3,200 社の範囲）"
            ),
            legal_article=legal,
            threshold_label=threshold,
        )
    if band == "50k_90k":
        return CategoryFinding(
            category="shipper",
            verdict="gray_zone",
            reason="年間取扱貨物が 5〜9 万トン帯。閾値前後のため実績データでの再判定を推奨",
            legal_article=legal,
            threshold_label=threshold,
        )
    if band == "unknown":
        return CategoryFinding(
            category="shipper",
            verdict="gray_zone",
            reason="年間取扱貨物量が不明。社内で実績集計が必要",
            legal_article=legal,
            threshold_label=threshold,
        )
    return CategoryFinding(
        category="shipper",
        verdict="not_applies",
        reason="年間取扱貨物が 5 万トン未満 → 特定荷主に該当しない見込み",
        legal_article=legal,
        threshold_label=threshold,
    )


def _chain_franchise_verdict(
    is_chain_franchise: bool,
    annual_revenue_jpy: int | None,
) -> CategoryFinding | None:
    """特定連鎖化事業者の判定（第65条）。

    連鎖化フラグが OFF の場合は判定対象外として ``None`` を返す。
    """
    if not is_chain_franchise:
        return None

    legal = "物流効率化法 第65条"
    threshold = (
        f"年間売上 {CHAIN_FRANCHISE_THRESHOLD_JPY // 100_000_000:,} 億円以上"
        "（暫定値・直近2期平均で精査）"
    )

    if annual_revenue_jpy is None:
        return CategoryFinding(
            category="chain_franchise",
            verdict="gray_zone",
            reason="連鎖化事業者として運営しているが売上未入力。法令上は直近2期平均で判定するため個別精査が必要",
            legal_article=legal,
            threshold_label=threshold,
        )
    if annual_revenue_jpy >= CHAIN_FRANCHISE_THRESHOLD_JPY:
        return CategoryFinding(
            category="chain_franchise",
            verdict="applies",
            reason=(
                f"連鎖化事業者で年間売上 {annual_revenue_jpy:,} 円 ≥ "
                f"{CHAIN_FRANCHISE_THRESHOLD_JPY:,} 円 → 特定連鎖化事業者に該当"
            ),
            legal_article=legal,
            threshold_label=threshold,
        )
    # 閾値の 70% 以上はボーダーライン
    if annual_revenue_jpy >= CHAIN_FRANCHISE_THRESHOLD_JPY * 0.7:
        return CategoryFinding(
            category="chain_franchise",
            verdict="gray_zone",
            reason="連鎖化事業者で売上が閾値の前後。法令の正確な閾値は「直近2事業年度の平均売上」のため個別精査を推奨",
            legal_article=legal,
            threshold_label=threshold,
        )
    return CategoryFinding(
        category="chain_franchise",
        verdict="not_applies",
        reason="連鎖化事業者だが売上が閾値未満 → 特定連鎖化事業者に該当しない見込み",
        legal_article=legal,
        threshold_label=threshold,
    )


def _warehouse_verdict(band: WarehouseTonsBand) -> CategoryFinding | None:
    """特定倉庫業者の判定。

    倉庫を保有していない（`band == "none"`）場合は判定対象外。
    """
    if band == "none":
        return None

    legal = "物流効率化法 特定倉庫業者規定"
    threshold = f"営業倉庫の年間入庫貨物 {WAREHOUSE_THRESHOLD_TONS:,} トン以上"

    if band == "ge_700k":
        return CategoryFinding(
            category="warehouse",
            verdict="applies",
            reason=(
                f"営業倉庫の年間入庫貨物が {WAREHOUSE_THRESHOLD_TONS:,} トン以上 → "
                "特定倉庫業者に該当（全国 約 70 社の範囲）"
            ),
            legal_article=legal,
            threshold_label=threshold,
        )
    if band == "100k_700k":
        return CategoryFinding(
            category="warehouse",
            verdict="gray_zone",
            reason=(
                "営業倉庫の年間入庫貨物が 10〜70 万トン帯。"
                "閾値前後のため実績データでの再判定を推奨"
            ),
            legal_article=legal,
            threshold_label=threshold,
        )
    return CategoryFinding(
        category="warehouse",
        verdict="not_applies",
        reason="営業倉庫の年間入庫貨物が 10 万トン未満 → 特定倉庫業者に該当しない見込み",
        legal_article=legal,
        threshold_label=threshold,
    )


def _freight_transport_verdict(band: VehiclesBand) -> CategoryFinding | None:
    """特定貨物自動車運送事業者等の判定。

    保有車両なし（`band == "none"`）の場合は判定対象外。
    """
    if band == "none":
        return None

    legal = "物流効率化法 特定貨物自動車運送事業者等規定"
    threshold = f"保有車両 {FREIGHT_TRANSPORT_THRESHOLD_VEHICLES} 台以上"

    if band == "ge_150":
        return CategoryFinding(
            category="freight_transport",
            verdict="applies",
            reason=(
                f"保有車両が {FREIGHT_TRANSPORT_THRESHOLD_VEHICLES} 台以上 → "
                "特定貨物自動車運送事業者等に該当（全国 約 790 社の範囲）"
            ),
            legal_article=legal,
            threshold_label=threshold,
        )
    if band == "50_150":
        return CategoryFinding(
            category="freight_transport",
            verdict="gray_zone",
            reason="保有車両が 50〜150 台帯。閾値前後のため実車両台数での再判定を推奨",
            legal_article=legal,
            threshold_label=threshold,
        )
    return CategoryFinding(
        category="freight_transport",
        verdict="not_applies",
        reason="保有車両が 50 台未満 → 特定貨物自動車運送事業者等に該当しない見込み",
        legal_article=legal,
        threshold_label=threshold,
    )


def screen(
    input_: ScreeningInput,
    *,
    today: date | None = None,
) -> ScreeningResult:
    """4 区分のスクリーニング判定を実行する。

    Args:
        input_: ユーザー入力（業種ヒント + 各バンド + CLO 選任状況）
        today: 期限カウントダウンの基準日（テスト注入用・既定は date.today()）

    Returns:
        ScreeningResult（findings + notes + days_until_deadline）
    """
    findings: list[CategoryFinding] = [
        _shipper_verdict(input_.freight_tons_band, input_.industry),
    ]

    chain = _chain_franchise_verdict(input_.is_chain_franchise, input_.annual_revenue_jpy)
    if chain is not None:
        findings.append(chain)

    warehouse = _warehouse_verdict(input_.warehouse_tons_band)
    if warehouse is not None:
        findings.append(warehouse)

    transport = _freight_transport_verdict(input_.vehicles_band)
    if transport is not None:
        findings.append(transport)

    notes: list[str] = []
    if input_.clo_status == "appointed":
        notes.append("CLO は既に選任済みとの回答。届出書類の準備状況も併せて確認してください")
    elif input_.clo_status == "planning":
        notes.append("CLO 選任予定との回答。施行日（2026-04-01）までに選任 + 届出が必要")
    elif input_.clo_status == "not_considered" and any(
        f.verdict == "applies" for f in findings
    ):
        notes.append(
            "⚠️ いずれかの区分で対象に該当する見込みだが CLO 選任が未検討。"
            "直ちに経営層への報告が必要"
        )

    if any(f.verdict == "gray_zone" for f in findings):
        notes.append("閾値前後（グレーゾーン）の項目あり。社内で実測データを集計したうえで個別相談を推奨")

    today_ = today or date.today()
    days = (SUBMISSION_DEADLINE - today_).days

    return ScreeningResult(
        findings=findings,
        notes=notes,
        days_until_deadline=days,
    )
