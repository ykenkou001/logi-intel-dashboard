"""施策プレイブックの標準施策セット。

各施策に以下のメタデータを保持:
    - 適用業種・最小規模（適合判定の前提）
    - 投資レンジ（low/high）
    - 期待効果（CO2 削減率・コスト削減率）
    - 実装難易度（1-5）
    - 適用補助金リスト
    - 成功事例参照（efficiency_law_certified の case_id）
    - 失敗パターン（common_pitfalls）
    - 様式第3 セクション分類（load / wait / loading）
"""
from __future__ import annotations

from dataclasses import dataclass

from core.export.citation import Citation, logistics_efficiency_law_citation
from core.static.efficiency_law_certified import IndustryCategory, MeasureType

# 様式第3 必須3項目に対応するセクションキー
Form3Section = str  # "load" | "wait" | "loading"

# 必要リソース（自社プロフィールのフィット判定で使用）
RequiredResource = str
# 実例:
#   "multi_site"             — 複数拠点を持つ
#   "long_distance_transport" — 長距離輸送（500km超）が一定割合
#   "warehouse_management"   — 自社倉庫管理オペレーション
#   "fleet_owned"            — 自社車両保有
#   "joint_partner_network"  — 同業他社との連携素地
#   "it_capability"          — IT 部門・システム導入余力


@dataclass(frozen=True)
class PlaybookMeasure:
    """プレイブックに登録する単一施策。

    Step 2（評価エンジン）が自社プロフィールと照合してスコアリングする際の入力。
    Step 5（実現可能性チェッカー）が `required_resources` で適合性を判定する際の入力。
    """

    measure_id: str
    """内部識別子（snake_case・例: 'modal_shift_to_rail'）。"""

    name: str
    """様式第3 風の短い見出し。"""

    description: str
    """経営層向けの 1-2 文要約。"""

    # 分類
    measure_type: MeasureType
    """efficiency_law_certified.MeasureType と整合（マッチング用）。"""

    form3_section: Form3Section
    """様式第3 のセクションキー（"load" / "wait" / "loading"）。"""

    # 適用条件
    applicable_industries: list[IndustryCategory]
    """適用可能な業種カテゴリ。空リストなら全業種対象。"""

    min_revenue_jpy: int | None
    """最小推奨売上（円）。これ未満は規模不適合警告対象。None なら制約なし。"""

    min_freight_tons: float | None
    """最小推奨年間取扱量（トン）。"""

    required_resources: list[RequiredResource]
    """前提リソース（自社プロフィールに揃っていることが望ましい）。"""

    # 投資・効果
    typical_investment_jpy_low: int
    """投資額レンジ low（円）。"""

    typical_investment_jpy_high: int
    """投資額レンジ high（円）。"""

    expected_co2_reduction_pct: float | None
    """対象トンキロに対する CO2 削減率（%）。試算対象外なら None。"""

    expected_cost_reduction_pct: float | None
    """対象コストに対する削減率（%）。"""

    # 実装難易度・期間
    implementation_difficulty: int
    """1（容易）〜5（最困難）。経営判断・取引先調整・IT 投資の総合評価。"""

    typical_payback_years: float | None
    """標準回収期間（年）。コスト削減を目的としない施策は None。"""

    # 補助金・前例・失敗
    eligible_subsidies: list[str]
    """適用可能な補助金（短文ラベル）。"""

    success_case_ids: list[str]
    """efficiency_law_certified.CertifiedCase.case_id への参照。"""

    common_pitfalls: list[str]
    """失敗パターン（経営会議で「気を付けるポイント」として提示）。"""

    # 法令・出典
    relevant_law_articles: list[str]
    """関連法令条文（改善基準告示・物流効率化法 等）。"""

    citation: Citation
    """出典。"""


# 法令出典の共通参照
_EFFICIENCY_LAW_CITATION = logistics_efficiency_law_citation()
_PORTAL_URL = "https://www.revised-logistics-act-portal.mlit.go.jp/planning/"


# ============================================================
# 標準施策セット（10 件）
# ============================================================

ALL_MEASURES: list[PlaybookMeasure] = [
    # ---------- 積載率向上カテゴリ（form3_section="load"）----------
    PlaybookMeasure(
        measure_id="modal_shift_to_rail",
        name="鉄道貨物へのモーダルシフト",
        description=(
            "中長距離（500km超）幹線輸送をトラックから鉄道貨物に切替え、"
            "ラウンドユース化で空コンテナ回送も削減する。"
        ),
        measure_type="modal_shift",
        form3_section="load",
        applicable_industries=["manufacturing", "wholesale", "chain_franchise"],
        min_revenue_jpy=10_000_000_000,  # 100 億円
        min_freight_tons=30_000.0,
        required_resources=["long_distance_transport"],
        typical_investment_jpy_low=3_000_000,
        typical_investment_jpy_high=20_000_000,
        expected_co2_reduction_pct=72.0,  # トラック 76→鉄道 21 g/トンキロ
        expected_cost_reduction_pct=15.0,
        implementation_difficulty=4,
        typical_payback_years=0.5,
        eligible_subsidies=[
            "国交省 モーダルシフト等推進事業費補助金",
            "経産省 省エネルギー設備投資支援",
        ],
        success_case_ids=["MODAL-FOOD-RAIL"],
        common_pitfalls=[
            "鉄道ダイヤと出荷タイミングの整合性確保が困難",
            "JR 貨物コンテナ対応の積込設備整備が必要",
            "災害時のリスケジュール余地が小さい",
        ],
        relevant_law_articles=[
            "物流効率化法 第3条（基本方針）",
            "第3次交通政策基本計画（モーダルシフト目標）",
        ],
        citation=_EFFICIENCY_LAW_CITATION,
    ),
    PlaybookMeasure(
        measure_id="load_factor_tms",
        name="積載率向上（TMS 配車最適化）",
        description=(
            "TMS（輸配送管理システム）導入と全拠点出荷データ一元管理により、"
            "全国平均 38% から目指すべき水準 50% へ積載率を引き上げる。"
        ),
        measure_type="load_factor",
        form3_section="load",
        applicable_industries=[
            "manufacturing", "wholesale", "retail", "chain_franchise",
        ],
        min_revenue_jpy=5_000_000_000,  # 50 億円
        min_freight_tons=20_000.0,
        required_resources=["multi_site", "it_capability"],
        typical_investment_jpy_low=2_000_000,
        typical_investment_jpy_high=15_000_000,
        expected_co2_reduction_pct=24.0,  # 38→50% で必要稼働量 24% 減
        expected_cost_reduction_pct=24.0,
        implementation_difficulty=3,
        typical_payback_years=0.1,
        eligible_subsidies=[
            "経産省 IT 導入補助金",
            "国交省 物流効率化法 認定事業者支援",
        ],
        success_case_ids=[],
        common_pitfalls=[
            "拠点ごとの運用慣行差異により全社一元化に時間がかかる",
            "委託運送事業者との実績データ共有が拒否される",
            "繁忙期の積載率向上は需要平準化と組み合わせる必要",
        ],
        relevant_law_articles=[
            "物流効率化法 省令 第5条（積載率向上の措置）",
        ],
        citation=_EFFICIENCY_LAW_CITATION,
    ),
    PlaybookMeasure(
        measure_id="joint_delivery_competitor",
        name="同業他社との共同配送",
        description=(
            "同一エリアへの配送先が重複する競合他社・荷主団体と協議し、"
            "WMS 連携で配送計画を統合。配送便数 30% 削減・コスト 20% 削減を狙う。"
        ),
        measure_type="joint_delivery",
        form3_section="load",
        # 連鎖化事業者（コンビニ本部・FC 本部）の共同配送は JOINT-CONVENIENCE
        # 等の認定事例があり、industry_packages.chain_franchise でも標準採用済。
        # c.4 で逆検証テスト（ALL_MEASURES 側からの整合確認）を追加した際に検出。
        applicable_industries=[
            "manufacturing", "wholesale", "retail", "chain_franchise",
        ],
        min_revenue_jpy=20_000_000_000,  # 200 億円
        min_freight_tons=50_000.0,
        required_resources=["joint_partner_network", "warehouse_management"],
        typical_investment_jpy_low=3_000_000,
        typical_investment_jpy_high=20_000_000,
        expected_co2_reduction_pct=30.0,
        expected_cost_reduction_pct=20.0,
        implementation_difficulty=5,
        typical_payback_years=0.2,
        eligible_subsidies=[
            "国交省 物流総合効率化法 認定事業者支援",
            "経産省 共同配送実証事業",
        ],
        success_case_ids=["JOINT-DAILY-DRINK", "JOINT-CONVENIENCE"],
        common_pitfalls=[
            "競合他社との情報共有合意形成に時間がかかる（独禁法考慮）",
            "請求・コスト按分ロジックの設計が複雑",
            "離脱時の運用継続リスク（共同 WMS 依存）",
        ],
        relevant_law_articles=[
            "物流効率化法 第15条（総合効率化計画）",
        ],
        citation=_EFFICIENCY_LAW_CITATION,
    ),
    PlaybookMeasure(
        measure_id="pallet_standardization",
        name="パレット標準化（T11／T12）",
        description=(
            "業界標準パレット（T11/T12）への切替えとユニットロード化で、"
            "荷役効率と積載効率を同時改善。発注ユニット化で小口多頻度を抑制。"
        ),
        measure_type="load_factor",
        form3_section="load",
        applicable_industries=["manufacturing", "wholesale", "retail"],
        min_revenue_jpy=3_000_000_000,  # 30 億円
        min_freight_tons=10_000.0,
        required_resources=["warehouse_management"],
        typical_investment_jpy_low=1_000_000,
        typical_investment_jpy_high=8_000_000,
        expected_co2_reduction_pct=8.0,
        expected_cost_reduction_pct=10.0,
        implementation_difficulty=2,
        typical_payback_years=1.0,
        eligible_subsidies=[
            "経産省 サプライチェーン強化補助金",
        ],
        success_case_ids=[],
        common_pitfalls=[
            "取引先と異なる規格を使用していると切替コストが発生",
            "パレット紛失・破損リスクへの対応スキーム必要",
        ],
        relevant_law_articles=[
            "物流効率化法 省令 第5条（積載率向上の措置）",
        ],
        citation=_EFFICIENCY_LAW_CITATION,
    ),

    # ---------- 荷待ち時間短縮カテゴリ（form3_section="wait"）----------
    PlaybookMeasure(
        measure_id="berth_booking_vbs",
        name="バース予約受付システム（VBS）",
        description=(
            "トラック予約受付システムを導入し、入出荷時間スロットを管理。"
            "平均荷待ち時間 1.5h/便を 50% 削減し、ドライバー拘束時間を大幅短縮。"
        ),
        measure_type="berth_booking",
        form3_section="wait",
        applicable_industries=[
            "manufacturing", "wholesale", "retail", "chain_franchise",
        ],
        min_revenue_jpy=3_000_000_000,
        min_freight_tons=10_000.0,
        required_resources=["warehouse_management", "it_capability"],
        typical_investment_jpy_low=1_000_000,
        typical_investment_jpy_high=10_000_000,
        expected_co2_reduction_pct=None,  # CO2 への直接効果は限定的
        expected_cost_reduction_pct=8.0,
        implementation_difficulty=2,
        typical_payback_years=1.5,
        eligible_subsidies=[
            "経産省 IT 導入補助金",
            "国交省 トラック輸送における取引環境・労働時間改善補助金",
        ],
        success_case_ids=[],
        common_pitfalls=[
            "システム未導入の運送事業者が多数残ると効果半減",
            "予約遵守率の KPI モニタリング体制が必要",
            "繁忙期のスロット争奪戦への対応設計",
        ],
        relevant_law_articles=[
            "改善基準告示（厚労省告示第367号）",
            "物流効率化法 省令 第6条（荷待ち時間短縮の措置）",
        ],
        citation=_EFFICIENCY_LAW_CITATION,
    ),
    PlaybookMeasure(
        measure_id="delivery_time_distribution",
        name="納入時間帯の分散・拡大",
        description=(
            "朝集中の納入時間帯を午後・夜間にも分散。納入予約制と組合せで"
            "ピーク時の荷待ち時間を構造的に削減する。"
        ),
        measure_type="berth_booking",
        form3_section="wait",
        # 連鎖化事業者（コンビニ本部・FC 本部）の店舗納品時間帯分散は典型施策。
        # c.4 で逆検証テスト（industry_packages 側からの整合確認）を追加した際に検出。
        applicable_industries=[
            "manufacturing", "wholesale", "retail", "chain_franchise",
        ],
        min_revenue_jpy=1_000_000_000,
        min_freight_tons=5_000.0,
        required_resources=["warehouse_management"],
        typical_investment_jpy_low=500_000,
        typical_investment_jpy_high=3_000_000,
        expected_co2_reduction_pct=None,
        expected_cost_reduction_pct=5.0,
        implementation_difficulty=3,
        typical_payback_years=2.0,
        eligible_subsidies=[],
        success_case_ids=[],
        common_pitfalls=[
            "店舗オペレーションとの調整負荷大",
            "夜間納入は人件費増・防犯コストとのトレードオフ",
        ],
        relevant_law_articles=[
            "改善基準告示（厚労省告示第367号）",
        ],
        citation=_EFFICIENCY_LAW_CITATION,
    ),

    # ---------- 荷役等時間短縮カテゴリ（form3_section="loading"）----------
    PlaybookMeasure(
        measure_id="relay_transport",
        name="中継輸送（長距離運行の分割）",
        description=(
            "長距離幹線（500km超）の中間地点に中継拠点を設置し、"
            "ドライバー交代制を導入。1運行あたり拘束時間を約 2.5h 削減。"
        ),
        measure_type="relay_transport",
        form3_section="loading",
        applicable_industries=["manufacturing", "wholesale"],
        min_revenue_jpy=30_000_000_000,  # 300 億円
        min_freight_tons=80_000.0,
        required_resources=["long_distance_transport", "fleet_owned"],
        typical_investment_jpy_low=5_000_000,
        typical_investment_jpy_high=30_000_000,
        expected_co2_reduction_pct=None,
        expected_cost_reduction_pct=3.0,
        implementation_difficulty=4,
        typical_payback_years=5.0,
        eligible_subsidies=[
            "国交省 トラック中継輸送導入支援補助金",
        ],
        success_case_ids=[],
        common_pitfalls=[
            "中継拠点の確保（用地取得・リース契約）に時間がかかる",
            "ドライバーの労使協定の見直しが必要",
            "繁忙期の中継スケジュール調整が複雑",
        ],
        relevant_law_articles=[
            "改善基準告示（厚労省告示第367号）— 拘束時間 13h/日",
        ],
        citation=_EFFICIENCY_LAW_CITATION,
    ),
    PlaybookMeasure(
        measure_id="warehouse_dx_wms",
        name="WMS 導入による倉庫オペレーション DX",
        description=(
            "倉庫管理システム（WMS）を導入し、入出庫・在庫・ピッキングを統合管理。"
            "荷役時間と検品時間を削減し、ドライバー待機時間を構造的に短縮。"
        ),
        measure_type="warehouse_dx",
        form3_section="loading",
        applicable_industries=[
            "manufacturing", "wholesale", "retail", "chain_franchise",
        ],
        min_revenue_jpy=5_000_000_000,
        min_freight_tons=15_000.0,
        required_resources=["warehouse_management", "it_capability"],
        typical_investment_jpy_low=3_000_000,
        typical_investment_jpy_high=30_000_000,
        expected_co2_reduction_pct=None,
        expected_cost_reduction_pct=10.0,
        implementation_difficulty=3,
        typical_payback_years=2.5,
        eligible_subsidies=[
            "経産省 IT 導入補助金",
            "中小企業庁 ものづくり補助金",
        ],
        success_case_ids=[],
        common_pitfalls=[
            "既存基幹システムとの連携カスタマイズコスト",
            "現場オペレーションへの定着に時間がかかる",
        ],
        relevant_law_articles=[
            "物流効率化法 省令 第7条（荷役等時間短縮の措置）",
        ],
        citation=_EFFICIENCY_LAW_CITATION,
    ),

    # ---------- 横断系（form3_section="load" を主とする）----------
    PlaybookMeasure(
        measure_id="visualization_baseline",
        name="物流実態の把握・可視化",
        description=(
            "全拠点の積載率・荷待ち時間・荷役等時間を委託運送事業者と連携して計測。"
            "改善対象拠点を特定する出発点となる前提施策。"
        ),
        measure_type="warehouse_dx",
        form3_section="load",
        applicable_industries=[
            "manufacturing", "wholesale", "retail", "chain_franchise",
        ],
        min_revenue_jpy=None,
        min_freight_tons=None,
        required_resources=[],
        typical_investment_jpy_low=500_000,
        typical_investment_jpy_high=3_000_000,
        expected_co2_reduction_pct=None,
        expected_cost_reduction_pct=None,
        implementation_difficulty=1,
        typical_payback_years=None,
        eligible_subsidies=[],
        success_case_ids=[],
        common_pitfalls=[
            "委託運送事業者からの実績データ提供拒否",
            "拠点間で計測手法がバラバラだと比較困難",
        ],
        relevant_law_articles=[
            "物流効率化法 省令 第4条（実態把握の努力義務）",
        ],
        citation=_EFFICIENCY_LAW_CITATION,
    ),
    PlaybookMeasure(
        measure_id="lead_time_review",
        name="発注頻度・リードタイム見直し（着荷主側）",
        description=(
            "翌日配送依頼や発注締切時間延長依頼を見直し、十分なリードタイムを確保。"
            "発荷主の積載効率向上に協力する着荷主としての施策。"
        ),
        measure_type="load_factor",
        form3_section="load",
        applicable_industries=["manufacturing", "wholesale", "retail"],
        min_revenue_jpy=None,
        min_freight_tons=None,
        required_resources=[],
        typical_investment_jpy_low=0,
        typical_investment_jpy_high=2_000_000,
        expected_co2_reduction_pct=10.0,
        expected_cost_reduction_pct=5.0,
        implementation_difficulty=3,
        typical_payback_years=1.0,
        eligible_subsidies=[],
        success_case_ids=[],
        common_pitfalls=[
            "営業部門の慣行変更に対する社内抵抗",
            "急な発注変更に対応できる体制の維持が困難",
        ],
        relevant_law_articles=[
            "物流効率化法 第46条（特定第二種荷主の責務）",
        ],
        citation=_EFFICIENCY_LAW_CITATION,
    ),
]


def get_measure(measure_id: str) -> PlaybookMeasure | None:
    """measure_id で施策を取得する。"""
    for m in ALL_MEASURES:
        if m.measure_id == measure_id:
            return m
    return None


def measures_by_section(section: Form3Section) -> list[PlaybookMeasure]:
    """様式第3 セクション（load/wait/loading）に属する施策を返す。"""
    return [m for m in ALL_MEASURES if m.form3_section == section]


__all__ = [
    "ALL_MEASURES",
    "Form3Section",
    "PlaybookMeasure",
    "RequiredResource",
    "get_measure",
    "measures_by_section",
]
