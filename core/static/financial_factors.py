"""財務翻訳レイヤ用の係数・定数（炭素価格・罰則・NPV 割引率等）。

CLO 計画書の物流 KPI（CO2 削減・コスト削減・荷待ち時間）を
**経営層が直感的に理解できる円単位**に変換するための係数を集約する。

設計方針:
    - 炭素価格は単一値ではなく **min/max レンジ**で表示（実勢と政策想定の両方）
    - ESG プレミアムは数値化が困難なため定性記述に留める（説明テキストのみ）
    - 不作為コストは罰則金額 + ブランド毀損リスクを併記
    - 全係数に出典を付与（経営会議「出典は？」即答用）
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from core.static._freshness import Freshness, register


@dataclass(frozen=True)
class CarbonPriceRange:
    """炭素価格レンジ（円/t-CO2）。

    実勢（J-クレジット）と政策想定（GX-ETS / EU CBAM 連動）の両方を併記する。
    施策の炭素回避額は両端で示し、経営会議では幅で議論できる形にする。
    """

    j_credit_jpy_per_ton: float = 3000.0
    """J-クレジット直近実勢（〜2026年初頭の取引帯）。"""

    gx_ets_target_jpy_per_ton: float = 5000.0
    """GX-ETS 試行段階の想定炭素価格（2030年想定値・環境省試算）。"""

    @property
    def low(self) -> float:
        return self.j_credit_jpy_per_ton

    @property
    def high(self) -> float:
        return self.gx_ets_target_jpy_per_ton


@dataclass(frozen=True)
class PenaltyAmounts:
    """物流効率化法の罰則金額（円）。"""

    clo_unappointed_max_fine_jpy: int = 1_000_000
    """CLO 未選任の罰金上限（物流効率化法 第78条 等）。"""

    notification_failure_max_fine_jpy: int = 200_000
    """届出怠慢の過料上限。"""

    plan_failure_consequence: str = (
        "計画未達の場合: 国交大臣による勧告 → 命令 → 企業名公表"
    )
    """計画未達時の段階的措置（金銭罰ではないがブランド毀損リスク大）。"""


@dataclass(frozen=True)
class NpvParameters:
    """NPV 算定パラメータ。"""

    discount_rate_pct: float = 3.0
    """割引率。中堅企業の標準的な hurdle rate に整合（要件次第で見直し）。"""

    horizon_years: int = 5
    """累積効果の評価期間（CLO 計画期間 5 年に整合）。"""


# ESG プレミアムの定性説明テキスト
# 数値化は資本コスト改善の定量化が研究段階であり、本アプリでは数値化を見送る。
# 経営会議では「ESG 評価向上 → 機関投資家からの評価」程度の定性インパクトとして扱う。
ESG_QUALITATIVE_NOTE: str = (
    "ESG プレミアム（資本コスト改善・機関投資家評価向上）は定性効果として認識する。"
    "TCFD 開示・SBT 認定企業の資本コスト低減効果は学術研究で観察されているが、"
    "本アプリでは過度な数値化を避け、CLO 計画達成 = ESG 評価向上の定性連関のみ示す。"
)

# 不作為コストの定性説明テンプレート
INACTION_RISK_NOTE_TEMPLATE: str = (
    "【不作為コスト】\n"
    "  - CLO 未選任: 罰金上限 {clo_fine:,}円（物流効率化法）\n"
    "  - 届出怠慢: 過料上限 {notify_fine:,}円\n"
    "  - 計画未達: {plan_failure}\n"
    "  ※ 金銭罰の規模は限定的だが、企業名公表によるブランド毀損・"
    "取引先・株主からの信認失墜リスクが本質。"
)


# シングルトン定数として公開
CARBON_PRICE = CarbonPriceRange()
PENALTIES = PenaltyAmounts()
NPV_PARAMS = NpvParameters()


def build_inaction_risk_note() -> str:
    """不作為コストの定性記述テキストを生成する。"""
    return INACTION_RISK_NOTE_TEMPLATE.format(
        clo_fine=PENALTIES.clo_unappointed_max_fine_jpy,
        notify_fine=PENALTIES.notification_failure_max_fine_jpy,
        plan_failure=PENALTIES.plan_failure_consequence,
    )


FRESHNESS = Freshness(
    label="財務翻訳係数（炭素価格レンジ・罰則・NPV）",
    last_updated=date(2026, 5, 3),
    update_cadence="annual",
    source_url=(
        "https://www.meti.go.jp/policy/energy_environment/global_warming/"
        "JCM/about_jcm.html"
    ),
    notes=(
        "J-クレジット実勢価格・GX-ETS 想定価格は年次でチェック。"
        "罰則金額は物流効率化法本体（改正時のみ更新）。"
    ),
)
register("financial_factors", FRESHNESS)
