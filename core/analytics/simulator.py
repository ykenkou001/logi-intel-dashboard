"""施策効果シミュレータ。

CLO 計画書「実施措置／計画内容」セクションに記載する施策の
定量効果（CO2削減・コスト削減・ドライバー時間削減・投資回収）を
業界統計から概算で試算する。

対象施策（5種類）:
    1. モーダルシフト（トラック → 鉄道貨物 or 内航海運）
    2. 積載率向上（38% → 50%）
    3. 共同配送（同一エリア競合連携）
    4. 中継輸送（長距離運行の分割）
    5. バース予約システム（荷待ち時間削減）

設計方針:
    - 業界統計の標準ファクターで概算を出す（実測精緻化は次フェーズ）
    - 各施策の出典を明示（経営会議「出典は？」即答用）
    - 合算注意（施策間で対象が重複するため単純合算は過大）
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.export.citation import Citation, co2_factors_citation
from core.static._freshness import all_warnings
from core.static.co2_factors import CO2_FACTORS
from core.static.industry_freight_coef import estimate_freight_tons
from core.static.jsic import lookup

# 施策効果の標準ファクター（業界統計から）
_DEFAULT_LONG_DISTANCE_SHARE_PCT = 30.0  # 中長距離輸送比率（業界平均）
_DEFAULT_AVG_DISTANCE_KM = 500.0  # モーダルシフト対象の平均距離
_TARGET_LOAD_FACTOR_PCT = 50.0  # 目指す積載率
_BASELINE_LOAD_FACTOR_PCT = 38.0  # 業界平均積載率
_JOINT_DELIVERY_TRIP_REDUCTION_PCT = 30.0  # 共同配送の便数削減率
_JOINT_DELIVERY_COST_REDUCTION_PCT = 20.0  # 共同配送のコスト削減率
_RELAY_DRIVER_HOURS_SAVING_PER_TRIP = 2.5  # 中継輸送 1運行あたり拘束時間削減（h）
_BERTH_WAIT_TIME_REDUCTION_PCT = 50.0  # バース予約による荷待ち時間削減率
_AVG_DAILY_WAIT_HOURS_BEFORE = 1.5  # 改善前の平均荷待ち時間（h/日）
_DRIVER_HOURLY_COST_JPY = 3500.0  # ドライバー時給換算（業界平均）

# 投資額の概算（中小規模目安）
_MODAL_SHIFT_INVESTMENT_JPY = 5_000_000  # 鉄道コンテナ初期費用
_LOAD_FACTOR_INVESTMENT_JPY = 3_000_000  # TMS 導入
_JOINT_DELIVERY_INVESTMENT_JPY = 5_000_000  # WMS 連携・運用調整
_RELAY_INVESTMENT_JPY = 8_000_000  # 中継拠点準備（リース・人員配置）
_BERTH_BOOKING_INVESTMENT_JPY = 2_000_000  # バース予約システム

# 出典 URL
_AUTO_TRANSPORT_STATS_URL = "https://www.mlit.go.jp/k-toukei/jidousyayusou.html"
_LOGISTICS_EFFICIENCY_CASES_URL = (
    "https://www.mlit.go.jp/seisakutokatsu/freight/seisakutokatsu_freight_fr2_000018.html"
)
_RELAY_TRANSPORT_GUIDE_URL = "https://www.mlit.go.jp/jidosha/jidosha_tk1_000007.html"
_BERTH_BOOKING_REPORT_URL = "https://www.mlit.go.jp/jidosha/jidosha_tk1_000219.html"


@dataclass(frozen=True)
class MeasureSimulation:
    """単一施策のシミュレーション結果。"""

    name: str  # 施策名
    description: str  # 施策概要
    co2_reduction_kg_per_year: float | None  # 年間CO2削減量（kg）
    cost_saving_jpy_per_year: float | None  # 年間コスト削減額（円）
    driver_hours_saving_per_year: float | None  # 年間ドライバー時間削減（h）
    investment_jpy: float  # 必要投資額（円・概算）
    payback_years: float | None  # 単純回収期間（年）
    rationale: str  # 計算根拠
    citation: Citation  # 出典


@dataclass
class SimulationResult:
    """全施策のシミュレーション結果。"""

    jsic_code: str
    jsic_name: str
    prefecture: str
    revenue_jpy: int
    annual_freight_tons: float  # 年間取扱量（実測 or 推計）
    is_estimate: bool  # 取扱量が推計値か
    avg_distance_km: float  # 想定平均輸送距離
    long_distance_share_pct: float  # 中長距離輸送比率

    measures: list[MeasureSimulation] = field(default_factory=list)

    citations: list[Citation] = field(default_factory=list)
    freshness_warnings: list[str] = field(default_factory=list)

    @property
    def total_co2_reduction_kg(self) -> float:
        """全施策の合算CO2削減量（重複あり・最大値の参考）。"""
        return sum(m.co2_reduction_kg_per_year or 0.0 for m in self.measures)

    @property
    def total_cost_saving_jpy(self) -> float:
        """全施策の合算コスト削減（重複あり・最大値の参考）。"""
        return sum(m.cost_saving_jpy_per_year or 0.0 for m in self.measures)

    @property
    def total_investment_jpy(self) -> float:
        """全施策の合算投資額。"""
        return sum(m.investment_jpy for m in self.measures)


def _simulate_modal_shift(
    annual_freight_tons: float,
    avg_distance_km: float,
    long_distance_share_pct: float,
) -> MeasureSimulation:
    """モーダルシフト（トラック→鉄道貨物）。"""
    # 対象: 中長距離（500km超）の取扱量
    target_tons = annual_freight_tons * long_distance_share_pct / 100.0
    target_tonkm = target_tons * avg_distance_km

    # CO2削減: 営業用大型トラック 76 → 鉄道貨物 21 g-CO2/トンキロ
    co2_diff_g_per_tonkm = CO2_FACTORS.truck_large_commercial - CO2_FACTORS.rail_freight
    co2_reduction_kg = target_tonkm * co2_diff_g_per_tonkm / 1000.0

    # コスト削減: 鉄道シフトで燃料費 + 人件費 を約 15% 削減（業界事例）
    # トラック輸送コストの概算: 25円/トンキロ → 鉄道で約 21円/トンキロ
    cost_saving_jpy = target_tonkm * 4.0  # 4円/トンキロ削減 × トンキロ

    payback = _MODAL_SHIFT_INVESTMENT_JPY / cost_saving_jpy if cost_saving_jpy > 0 else None

    return MeasureSimulation(
        name="モーダルシフト（トラック→鉄道貨物）",
        description=(
            f"中長距離（{avg_distance_km:.0f}km超想定）の取扱量"
            f"{target_tons:,.0f}トン分を鉄道貨物にシフト"
        ),
        co2_reduction_kg_per_year=co2_reduction_kg,
        cost_saving_jpy_per_year=cost_saving_jpy,
        driver_hours_saving_per_year=None,
        investment_jpy=float(_MODAL_SHIFT_INVESTMENT_JPY),
        payback_years=payback,
        rationale=(
            f"対象トンキロ {target_tonkm:,.0f}トンキロ × CO2差 {co2_diff_g_per_tonkm}g/トンキロ"
        ),
        citation=co2_factors_citation(),
    )


def _simulate_load_factor(annual_freight_tons: float, avg_distance_km: float) -> MeasureSimulation:
    """積載率向上（38% → 50%）。"""
    # 必要トラック稼働量 = 取扱量 / 積載率 → 積載率向上で稼働量削減
    reduction_ratio = 1.0 - (_BASELINE_LOAD_FACTOR_PCT / _TARGET_LOAD_FACTOR_PCT)
    # CO2削減: 全自動車輸送量 × 営業用大型トラック原単位 × 削減率
    total_tonkm = annual_freight_tons * avg_distance_km
    co2_reduction_kg = total_tonkm * CO2_FACTORS.truck_large_commercial * reduction_ratio / 1000.0

    # コスト削減: 燃料費・傭車費・人件費が同比率で削減
    # トラック輸送コスト 約 25円/トンキロ × 削減率
    cost_saving_jpy = total_tonkm * 25.0 * reduction_ratio

    # ドライバー時間削減: 必要稼働時間が削減率分減少
    # 平均運行時間 = 取扱量×距離/100km/h（保守的に8h/100kmで計算）
    annual_driver_hours = total_tonkm / 100.0 * 1.0  # 1h/100km
    driver_hours_saving = annual_driver_hours * reduction_ratio

    payback = _LOAD_FACTOR_INVESTMENT_JPY / cost_saving_jpy if cost_saving_jpy > 0 else None

    return MeasureSimulation(
        name="積載率向上（38% → 50%）",
        description=(
            f"全国平均 38% から国交省「目指すべき水準」50% へ向上 "
            f"→ 必要トラック稼働量 {reduction_ratio * 100:.1f}% 削減"
        ),
        co2_reduction_kg_per_year=co2_reduction_kg,
        cost_saving_jpy_per_year=cost_saving_jpy,
        driver_hours_saving_per_year=driver_hours_saving,
        investment_jpy=float(_LOAD_FACTOR_INVESTMENT_JPY),
        payback_years=payback,
        rationale=(
            f"全トンキロ {total_tonkm:,.0f} × "
            f"トラック原単位 {CO2_FACTORS.truck_large_commercial}g × "
            f"削減率 {reduction_ratio * 100:.1f}%"
        ),
        citation=Citation(
            label="自動車輸送統計年報（国土交通省・年次）",
            url=_AUTO_TRANSPORT_STATS_URL,
            accessed_via="国土交通省 自動車輸送統計（年次）",
        ),
    )


def _simulate_joint_delivery(
    annual_freight_tons: float, avg_distance_km: float
) -> MeasureSimulation:
    """共同配送（同一エリア競合連携）。"""
    total_tonkm = annual_freight_tons * avg_distance_km
    reduction_ratio = _JOINT_DELIVERY_TRIP_REDUCTION_PCT / 100.0
    co2_reduction_kg = total_tonkm * CO2_FACTORS.truck_large_commercial * reduction_ratio / 1000.0
    cost_saving_jpy = total_tonkm * 25.0 * (_JOINT_DELIVERY_COST_REDUCTION_PCT / 100.0)
    payback = _JOINT_DELIVERY_INVESTMENT_JPY / cost_saving_jpy if cost_saving_jpy > 0 else None

    return MeasureSimulation(
        name="共同配送（同一エリア競合連携）",
        description=(
            f"配送便数 {_JOINT_DELIVERY_TRIP_REDUCTION_PCT:.0f}% 削減・"
            f"配送コスト {_JOINT_DELIVERY_COST_REDUCTION_PCT:.0f}% 削減"
            "（国交省 物流効率化法 認定事例より）"
        ),
        co2_reduction_kg_per_year=co2_reduction_kg,
        cost_saving_jpy_per_year=cost_saving_jpy,
        driver_hours_saving_per_year=None,
        investment_jpy=float(_JOINT_DELIVERY_INVESTMENT_JPY),
        payback_years=payback,
        rationale=("国交省 物流効率化法 認定事例の業界平均削減率を取扱量に乗じて算出"),
        citation=Citation(
            label="物流効率化法 認定事業 公表事例（国土交通省）",
            url=_LOGISTICS_EFFICIENCY_CASES_URL,
            accessed_via="国交省ポータル（静的参照）",
        ),
    )


def _simulate_relay_transport(
    annual_freight_tons: float,
    avg_distance_km: float,
    long_distance_share_pct: float,
) -> MeasureSimulation:
    """中継輸送（長距離運行の分割）。"""
    # 対象: 中長距離（500km超）運行
    target_tons = annual_freight_tons * long_distance_share_pct / 100.0
    # 1運行あたり 10トン換算で運行回数を試算
    annual_trips = target_tons / 10.0
    driver_hours_saving = annual_trips * _RELAY_DRIVER_HOURS_SAVING_PER_TRIP
    # 拘束時間削減の半分が直接的な人件費削減に寄与
    cost_saving_jpy = driver_hours_saving * _DRIVER_HOURLY_COST_JPY * 0.5
    payback = _RELAY_INVESTMENT_JPY / cost_saving_jpy if cost_saving_jpy > 0 else None

    return MeasureSimulation(
        name="中継輸送（長距離運行の分割）",
        description=(
            f"中長距離運行 約 {annual_trips:,.0f}回/年 を中継方式に変更 → "
            f"1運行あたり拘束時間 {_RELAY_DRIVER_HOURS_SAVING_PER_TRIP}h 削減"
        ),
        co2_reduction_kg_per_year=None,
        cost_saving_jpy_per_year=cost_saving_jpy,
        driver_hours_saving_per_year=driver_hours_saving,
        investment_jpy=float(_RELAY_INVESTMENT_JPY),
        payback_years=payback,
        rationale=("国交省「中継輸送に関する手引き」の標準的削減効果を運行回数に乗算"),
        citation=Citation(
            label="中継輸送に関する手引き（国土交通省）",
            url=_RELAY_TRANSPORT_GUIDE_URL,
            accessed_via="国交省ポータル（静的参照）",
        ),
    )


def _simulate_berth_booking(annual_freight_tons: float) -> MeasureSimulation:
    """バース予約システム（荷待ち時間削減）。"""
    # 1運行あたり 10トン換算で運行回数を試算
    annual_trips = annual_freight_tons / 10.0
    annual_wait_hours_before = annual_trips * _AVG_DAILY_WAIT_HOURS_BEFORE
    driver_hours_saving = annual_wait_hours_before * _BERTH_WAIT_TIME_REDUCTION_PCT / 100.0
    cost_saving_jpy = driver_hours_saving * _DRIVER_HOURLY_COST_JPY
    payback = _BERTH_BOOKING_INVESTMENT_JPY / cost_saving_jpy if cost_saving_jpy > 0 else None

    return MeasureSimulation(
        name="バース予約システム（荷待ち時間削減）",
        description=(
            f"荷待ち時間 平均 {_AVG_DAILY_WAIT_HOURS_BEFORE}h/便を "
            f"{_BERTH_WAIT_TIME_REDUCTION_PCT:.0f}% 削減"
        ),
        co2_reduction_kg_per_year=None,
        cost_saving_jpy_per_year=cost_saving_jpy,
        driver_hours_saving_per_year=driver_hours_saving,
        investment_jpy=float(_BERTH_BOOKING_INVESTMENT_JPY),
        payback_years=payback,
        rationale=("国交省 トラック予約システム導入効果調査の標準値を運行回数に乗算"),
        citation=Citation(
            label="トラック予約システム導入効果調査（国土交通省）",
            url=_BERTH_BOOKING_REPORT_URL,
            accessed_via="国交省ポータル（静的参照）",
        ),
    )


def simulate_measures(
    jsic_code: str,
    prefecture: str,
    revenue_jpy: int,
    annual_freight_tons: float | None = None,
    avg_distance_km: float = _DEFAULT_AVG_DISTANCE_KM,
    long_distance_share_pct: float = _DEFAULT_LONG_DISTANCE_SHARE_PCT,
) -> SimulationResult:
    """5施策の効果を同時にシミュレートする。

    Args:
        jsic_code: JSIC 細分類4桁コード
        prefecture: 主たる拠点の都道府県名
        revenue_jpy: 年間売上（円）
        annual_freight_tons: 年間取扱量（実測トン）。None なら売上から推計
        avg_distance_km: モーダルシフト対象の平均輸送距離（デフォルト 500km）
        long_distance_share_pct: 中長距離輸送比率（デフォルト 30%）

    Returns:
        SimulationResult

    Raises:
        ValueError: jsic_code が未収録、または取扱量が確定できない場合
    """
    entry = lookup(jsic_code)
    if entry is None:
        raise ValueError(
            f"JSIC コード '{jsic_code}' は未収録です。Step 1-4 と同じコードを指定してください。"
        )

    # 取扱量の確定
    is_estimate = False
    tons = annual_freight_tons
    if tons is None:
        tons = estimate_freight_tons(jsic_code, revenue_jpy)
        if tons is not None:
            is_estimate = True
    if tons is None or tons <= 0:
        raise ValueError(
            f"年間取扱量を確定できません（jsic_code={jsic_code} は推計対象外、"
            "annual_freight_tons を指定してください）"
        )

    measures = [
        _simulate_modal_shift(tons, avg_distance_km, long_distance_share_pct),
        _simulate_load_factor(tons, avg_distance_km),
        _simulate_joint_delivery(tons, avg_distance_km),
        _simulate_relay_transport(tons, avg_distance_km, long_distance_share_pct),
        _simulate_berth_booking(tons),
    ]

    # 出典の重複排除
    seen_urls: set[str] = set()
    citations: list[Citation] = []
    for m in measures:
        if m.citation.url not in seen_urls:
            citations.append(m.citation)
            seen_urls.add(m.citation.url)

    return SimulationResult(
        jsic_code=jsic_code,
        jsic_name=entry.name,
        prefecture=prefecture,
        revenue_jpy=revenue_jpy,
        annual_freight_tons=tons,
        is_estimate=is_estimate,
        avg_distance_km=avg_distance_km,
        long_distance_share_pct=long_distance_share_pct,
        measures=measures,
        citations=citations,
        freshness_warnings=all_warnings(),
    )


def _format_yen(amount_jpy: float) -> str:
    """円を読みやすい単位に整形する（億円 / 万円）。"""
    if amount_jpy >= 100_000_000:
        return f"{amount_jpy / 100_000_000:.1f}億円"
    if amount_jpy >= 10_000:
        return f"{amount_jpy / 10_000:,.0f}万円"
    return f"{amount_jpy:,.0f}円"


def _format_co2_kg(kg: float) -> str:
    """CO2 削減量を読みやすい単位に整形する（1万トン以上 / 1トン以上 / kg）。"""
    # 1 万トン = 10,000,000 kg
    if kg >= 10_000_000:
        return f"{kg / 10_000_000:.2f}万トン-CO2"
    # 1 トン = 1,000 kg
    if kg >= 1_000:
        return f"{kg / 1_000:,.1f}トン-CO2"
    return f"{kg:,.0f}kg-CO2"


def build_simulation_summary(r: SimulationResult) -> str:
    """SimulationResult から CLO 計画書用サマリーテキストを生成する。"""
    tons_label = "推計" if r.is_estimate else "実測"
    lines: list[str] = [
        "=== 施策効果シミュレーション（5施策同時試算）===",
        f"業種: {r.jsic_name}（{r.jsic_code}）",
        f"都道府県: {r.prefecture}",
        f"年間売上: {r.revenue_jpy / 1e8:.1f}億円",
        f"年間取扱量: 約 {r.annual_freight_tons:,.0f} トン（{tons_label}）",
        f"想定平均輸送距離: {r.avg_distance_km:.0f}km / "
        f"中長距離比率: {r.long_distance_share_pct:.0f}%",
        "",
    ]

    for i, m in enumerate(r.measures, start=1):
        lines += [
            f"【施策{i}: {m.name}】",
            f"  概要: {m.description}",
        ]
        if m.co2_reduction_kg_per_year is not None:
            lines.append(f"  CO2削減: 約 {_format_co2_kg(m.co2_reduction_kg_per_year)}/年")
        if m.cost_saving_jpy_per_year is not None:
            lines.append(f"  コスト削減: 約 {_format_yen(m.cost_saving_jpy_per_year)}/年")
        if m.driver_hours_saving_per_year is not None:
            lines.append(f"  ドライバー時間削減: 約 {m.driver_hours_saving_per_year:,.0f} h/年")
        lines.append(f"  必要投資（概算）: 約 {_format_yen(m.investment_jpy)}")
        if m.payback_years is not None:
            lines.append(f"  単純回収期間: 約 {m.payback_years:.1f} 年")
        lines += [
            f"  根拠: {m.rationale}",
            f"  出典: {m.citation.label}",
            "",
        ]

    lines += [
        "【総合効果（参考・施策間で対象が重複するため過大評価注意）】",
        f"  CO2削減 合算最大: 約 {_format_co2_kg(r.total_co2_reduction_kg)}/年",
        f"  コスト削減 合算最大: 約 {_format_yen(r.total_cost_saving_jpy)}/年",
        f"  必要投資 合計: 約 {_format_yen(r.total_investment_jpy)}",
        "",
        "  ※ 実効値は施策間相殺で合算最大の 70-80% 程度になることが業界事例で報告。"
        "正確な見積もりは Step 7（計画書ドラフト統合生成）で施策組合せシナリオを作成。",
        "",
        "【CLO 計画書への反映】",
        "  ・様式第3別紙「実施措置／計画内容」欄に上記施策をそのまま転記可能",
        "  ・「実施時期」は投資回収期間と整合的に2026〜2030年で段階配置を推奨",
        "  ・経営会議では「投資 vs リターン」と「CO2削減目標▲23.4%への寄与度」をセット提示",
    ]

    return "\n".join(lines)
