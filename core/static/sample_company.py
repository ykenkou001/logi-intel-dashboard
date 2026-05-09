"""自社プロフィール仮データ（フェーズ4 まで使用するサンプル3社）+ 実データ取込用スキーマ。

フェーズ4.0「実データ入力フォーム」（Codex 4 フル版）では、Excel/CSV から
CompanyProfile を構築してサンプル3社と同じインターフェースで使えるようにする。

設計方針:
    - 既存サンプル3社の数値挙動は完全互換（既存テスト/verify-clo-step が通ること）
    - 拡張フィールドはすべて Optional / デフォルト空 list / None
    - WaitTimeRow / HandlingTimeRow は CompanyProfile が保持する値オブジェクト
      （以前は core/export/docx_form5_writer.py に dataclass として定義していたが
      Pydantic に統一して Excel 取込時のバリデーションに乗せる）
    - data_source フラグで「推計値（estimated）」と「実測値（actual）」を区別

注意:
    - サンプル企業名・数値は架空であり、実在する企業とは無関係。
    - 公式記載事例集（core/templates/clo_plan_examples/）と業種コードを揃えてある。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SiteType = Literal["factory", "dc", "store", "office", "warehouse"]
DataSource = Literal["sample", "estimated", "actual"]
"""データの出所:
- "sample"   : デモ用架空企業のデータ（経営判断には使わない）
- "estimated": ユーザー入力 + 業界統計推計（一部実測なし）
- "actual"   : 自社実測データに基づく
"""

TimeSlot = Literal["morning", "midday", "evening", "night"]
"""時間帯区分（拠点別待機時間ヒートマップ用、フェーズ4.1 a.1 で導入）:
- "morning" : 6:00-10:00 朝便（始業前後の納品集中）
- "midday"  : 10:00-15:00 昼便（センター向け定期便中心）
- "evening" : 15:00-19:00 夕便（夕方ピーク・店舗納品）
- "night"   : 19:00-翌6:00 夜間便（深夜配送・関東〜関西幹線）
None の場合は "時間帯不明" として集計時 'all_day' レーンへ振り分け。
"""


class CompanySite(BaseModel):
    """自社拠点。"""

    name: str = Field(..., description="拠点名")
    site_type: SiteType = Field(..., description="拠点種別")
    prefecture: str = Field(..., description="都道府県名（正式名称）")
    annual_freight_tons: float = Field(..., ge=0, description="年間取扱貨物量（トン）")


class WaitTimeRow(BaseModel):
    """荷待ち時間 計測実績の 1 行（様式第5 Ⅳ セクションの計測データ単位）。"""

    model_config = ConfigDict(frozen=True)

    bucket_label: str = Field(..., description="集計区分（例: '全体', '都市部拠点'）")
    measured_count: int = Field(..., ge=0, description="計測便数")
    average_minutes: float = Field(..., ge=0, description="平均荷待ち時間（分）")
    max_minutes: float = Field(..., ge=0, description="最大荷待ち時間（分）")
    over_2h_count: int = Field(..., ge=0, description="2時間超 件数（基準超過の有無）")
    site_name: str | None = Field(
        default=None,
        description=(
            "拠点名（heatmap 集計の縦軸キー）。指定なしは「全体」扱い。"
            "site_name 指定時は CompanyProfile.sites のいずれかと一致することが望ましい。"
        ),
    )
    time_slot: TimeSlot | None = Field(
        default=None,
        description=(
            "時間帯区分（heatmap 集計の横軸キー）。"
            "morning/midday/evening/night のいずれか、または None（時間帯不明）。"
        ),
    )


class HandlingTimeRow(BaseModel):
    """荷役等時間 計測実績の 1 行。"""

    model_config = ConfigDict(frozen=True)

    bucket_label: str = Field(..., description="納品形態（例: 'パレット納品', 'バラ納品'）")
    measured_count: int = Field(..., ge=0)
    average_minutes: float = Field(..., ge=0, description="平均荷役時間（分）")
    max_minutes: float = Field(..., ge=0, description="最大荷役時間（分）")
    over_1h_pct: float = Field(..., ge=0, le=100, description="1時間超 割合（%）")


class KpiHistoryEntry(BaseModel):
    """直近期の KPI 履歴 1 行（trend 検出・実績ベースライン構築用）。"""

    model_config = ConfigDict(frozen=True)

    fy: int = Field(..., ge=2000, le=2100, description="年度（西暦・例: 2024）")
    metric: str = Field(
        ...,
        description=(
            "KPI 識別子（例: 'load_factor_pct' / 'co2_intensity_g_per_tonkm' / "
            "'wait_time_avg_minutes' / 'fuel_liters' 等）"
        ),
    )
    value: float = Field(..., description="値（unit に従う）")
    unit: str = Field(..., description="単位（例: '%', 'g/トンキロ', '分', 'L'）")


class CompanyProfile(BaseModel):
    """自社プロフィール（CLO 計画書ドラフト生成の入力）。"""

    company_id: str = Field(..., description="内部ID（ファイル名にも使用、英数字のみ）")
    name: str = Field(..., description="会社名")
    jsic_code: str = Field(..., min_length=4, max_length=4, description="JSIC 細分類4桁")
    main_business: str = Field(..., description="主たる事業の名称")
    annual_revenue_jpy: int = Field(..., ge=0, description="年間売上（円）")
    annual_freight_tons_total: float = Field(
        ...,
        ge=0,
        description="年間取扱貨物量 合計（トン）— 9万トン判定用",
    )
    operating_profit_jpy: int = Field(
        ...,
        description=(
            "年間営業利益（円）— 財務翻訳レイヤで施策効果を P&L インパクトに換算する基準。"
            "業界平均営業利益率を参考に設定（実データはフェーズ4 で取込予定）"
        ),
    )
    cost_of_goods_sold_jpy: int = Field(
        ...,
        ge=0,
        description="年間売上原価（円）— 物流コスト削減を売上原価減として反映する基準",
    )
    is_chain_franchise: bool = Field(False, description="連鎖化事業者か")
    fleet_count_owned: int = Field(0, ge=0, description="自社保有車両数")
    fleet_count_outsourced: int = Field(0, ge=0, description="委託車両数（おおよそ）")
    sites: list[CompanySite] = Field(default_factory=list, description="拠点リスト")
    clo_name: str = Field(..., description="CLO 役職・氏名")
    plan_period_start_fy: int = Field(..., ge=2026, description="計画期間 開始年度")
    plan_period_end_fy: int = Field(..., ge=2026, description="計画期間 終了年度")
    data_source: DataSource = Field(
        "estimated",
        description=(
            "プロフィール数値の出所。'sample' はデモ用架空企業（PoC のみ）、"
            "'estimated' はユーザー入力 + 業界統計推計、'actual' は自社実測データ。"
            "経営会議での defensibility のため、出力サマリー先頭で明示する。"
        ),
    )

    # --- フェーズ4.0 追加: 実測値フィールド（全 Optional / 未指定時は推計挙動） ---
    load_factor_actual_pct: float | None = Field(
        None,
        ge=0,
        le=100,
        description=(
            "積載率実績（%）— feasibility_check の現状値として使用。"
            "未指定時は業界平均（38%）にフォールバック"
        ),
    )
    annual_fuel_liters: float | None = Field(
        None,
        ge=0,
        description="年間燃料消費量（L）— CO2 ベースライン整合性検証用",
    )
    annual_co2_emissions_kg: float | None = Field(
        None,
        ge=0,
        description="年間 CO2 排出量実績（kg-CO2）",
    )
    wait_time_rows: list[WaitTimeRow] = Field(
        default_factory=list,
        description=(
            "荷待ち時間 計測実績（拠点別/集計区分別）。"
            "様式第5 Ⅳ セクションに直接反映され、改善基準告示の遵守判定に使われる"
        ),
    )
    handling_time_rows: list[HandlingTimeRow] = Field(
        default_factory=list,
        description="荷役等時間 計測実績（連鎖化事業者は対象外で空 list でよい）",
    )
    kpi_history: list[KpiHistoryEntry] = Field(
        default_factory=list,
        description="直近 3 期の KPI 履歴（trend 検出と実績ベースライン構築用）",
    )


# サンプル1: 製造業（電子部品）— 特定第一種荷主想定
# 財務想定: 営業利益率 7%（電子部品業界中央値）/ 売上原価率 75%
# 計測値: 国交省 様式第5 記載見本集（manufacturing_report_advanced.md）の数値レンジ
SAMPLE_MANUFACTURING = CompanyProfile(
    company_id="sample_mfg_01",
    name="テクノパーツ製造株式会社（架空）",
    jsic_code="3159",
    main_business="その他の電子部品・デバイス製造業",
    annual_revenue_jpy=85_000_000_000,  # 850 億円
    annual_freight_tons_total=120_000.0,  # 12 万トン（特定第一種荷主該当）
    operating_profit_jpy=5_950_000_000,  # 59.5 億円（営業利益率 7%）
    cost_of_goods_sold_jpy=63_750_000_000,  # 637.5 億円（売上原価率 75%）
    is_chain_franchise=False,
    fleet_count_owned=12,
    fleet_count_outsourced=180,
    sites=[
        CompanySite(
            name="本社工場", site_type="factory", prefecture="愛知県", annual_freight_tons=70_000
        ),
        CompanySite(
            name="東日本物流センター",
            site_type="dc",
            prefecture="埼玉県",
            annual_freight_tons=30_000,
        ),
        CompanySite(
            name="西日本物流センター",
            site_type="dc",
            prefecture="兵庫県",
            annual_freight_tons=20_000,
        ),
    ],
    clo_name="専務執行役員 田中 雄一",
    plan_period_start_fy=2026,
    plan_period_end_fy=2030,
    data_source="sample",
    load_factor_actual_pct=None,
    annual_fuel_liters=None,
    annual_co2_emissions_kg=None,
    wait_time_rows=[
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
    handling_time_rows=[
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
)

# サンプル2: 卸売業（インテリア）— 特定第一種・第二種荷主想定
# 財務想定: 営業利益率 2%（卸売業界中央値）/ 売上原価率 85%
SAMPLE_WHOLESALE = CompanyProfile(
    company_id="sample_wholesale_01",
    name="株式会社インテリアリンク商事（架空）",
    jsic_code="5514",
    main_business="室内装飾繊維品卸売業",
    annual_revenue_jpy=42_000_000_000,  # 420 億円
    annual_freight_tons_total=180_000.0,  # 18 万トン（第一種・第二種双方該当）
    operating_profit_jpy=840_000_000,  # 8.4 億円（営業利益率 2%）
    cost_of_goods_sold_jpy=35_700_000_000,  # 357 億円（売上原価率 85%）
    is_chain_franchise=False,
    fleet_count_owned=8,
    fleet_count_outsourced=240,
    sites=[
        CompanySite(
            name="関東センター", site_type="dc", prefecture="千葉県", annual_freight_tons=70_000
        ),
        CompanySite(
            name="関西センター", site_type="dc", prefecture="大阪府", annual_freight_tons=55_000
        ),
        CompanySite(
            name="九州センター", site_type="dc", prefecture="福岡県", annual_freight_tons=30_000
        ),
        CompanySite(
            name="東北センター", site_type="dc", prefecture="宮城県", annual_freight_tons=25_000
        ),
    ],
    clo_name="専務執行役員 佐藤 一郎",
    plan_period_start_fy=2026,
    plan_period_end_fy=2030,
    data_source="sample",
    load_factor_actual_pct=None,
    annual_fuel_liters=None,
    annual_co2_emissions_kg=None,
    wait_time_rows=[
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
    handling_time_rows=[
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
)

# サンプル3: 連鎖化事業者（コンビニ本部）
# 財務想定: 営業利益率 3.5%（コンビニ本部・加盟金収入主体で高め）/ 売上原価率 70%
SAMPLE_CHAIN = CompanyProfile(
    company_id="sample_chain_01",
    name="スマートマート株式会社（架空）",
    jsic_code="5891",
    main_business="コンビニエンスストア",
    annual_revenue_jpy=320_000_000_000,  # 3,200 億円
    annual_freight_tons_total=450_000.0,  # 45 万トン
    operating_profit_jpy=11_200_000_000,  # 112 億円（営業利益率 3.5%）
    cost_of_goods_sold_jpy=224_000_000_000,  # 2,240 億円（売上原価率 70%）
    is_chain_franchise=True,
    fleet_count_owned=0,
    fleet_count_outsourced=850,
    sites=[
        CompanySite(
            name="関東第一センター",
            site_type="dc",
            prefecture="埼玉県",
            annual_freight_tons=180_000,
        ),
        CompanySite(
            name="関東第二センター",
            site_type="dc",
            prefecture="神奈川県",
            annual_freight_tons=120_000,
        ),
        CompanySite(
            name="関西センター", site_type="dc", prefecture="大阪府", annual_freight_tons=100_000
        ),
        CompanySite(
            name="九州センター", site_type="dc", prefecture="福岡県", annual_freight_tons=50_000
        ),
    ],
    clo_name="専務執行役員 佐藤 一郎",
    plan_period_start_fy=2026,
    plan_period_end_fy=2030,
    data_source="sample",
    load_factor_actual_pct=None,
    annual_fuel_liters=None,
    annual_co2_emissions_kg=None,
    wait_time_rows=[
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
    # 連鎖化（コンビニ）は荷役等時間が法令上対象外
    handling_time_rows=[],
)

# サンプル4: 小売業（食料品スーパーマーケット）— 特定第一種・第二種荷主想定
# 財務想定: 営業利益率 3%（食料品スーパー業界中央値）/ 売上原価率 75%
# 計測値: 国交省 様式第5 記載見本集（retail_advanced.md）の数値レンジ
# c 段階で4業種パッケージ検証時に必須となる小売単独 fixture（Codex 勧告）
SAMPLE_RETAIL = CompanyProfile(
    company_id="sample_retail_01",
    name="ライフスマート小売株式会社（架空）",
    jsic_code="5811",
    main_business="食料品スーパーマーケット",
    annual_revenue_jpy=120_000_000_000,  # 1,200 億円
    annual_freight_tons_total=100_000.0,  # 10 万トン（特定第一種・第二種双方該当）
    operating_profit_jpy=3_600_000_000,  # 36 億円（営業利益率 3%）
    cost_of_goods_sold_jpy=90_000_000_000,  # 900 億円（売上原価率 75%）
    is_chain_franchise=False,
    fleet_count_owned=15,
    fleet_count_outsourced=320,
    sites=[
        CompanySite(
            name="関東地域DC", site_type="dc", prefecture="埼玉県", annual_freight_tons=45_000
        ),
        CompanySite(
            name="中部地域DC", site_type="dc", prefecture="愛知県", annual_freight_tons=30_000
        ),
        CompanySite(
            name="関西地域DC", site_type="dc", prefecture="大阪府", annual_freight_tons=25_000
        ),
    ],
    clo_name="取締役執行役員 鈴木 誠",
    plan_period_start_fy=2026,
    plan_period_end_fy=2030,
    data_source="sample",
    load_factor_actual_pct=42.0,  # 業界平均（38%）よりやや上
    annual_fuel_liters=None,
    annual_co2_emissions_kg=None,
    wait_time_rows=[
        WaitTimeRow(
            bucket_label="全体",
            measured_count=18500,
            average_minutes=28,
            max_minutes=125,
            over_2h_count=2,
        ),
        # 拠点 × 時間帯 の詳細（a.1 ヒートマップ用）
        # 関東地域DC（埼玉）：朝便集中で待機が伸びる典型パターン
        WaitTimeRow(
            bucket_label="関東地域DC・朝便",
            measured_count=2400,
            average_minutes=42,
            max_minutes=125,
            over_2h_count=2,
            site_name="関東地域DC",
            time_slot="morning",
        ),
        WaitTimeRow(
            bucket_label="関東地域DC・昼便",
            measured_count=3200,
            average_minutes=28,
            max_minutes=85,
            over_2h_count=0,
            site_name="関東地域DC",
            time_slot="midday",
        ),
        WaitTimeRow(
            bucket_label="関東地域DC・夕便",
            measured_count=2000,
            average_minutes=32,
            max_minutes=95,
            over_2h_count=0,
            site_name="関東地域DC",
            time_slot="evening",
        ),
        WaitTimeRow(
            bucket_label="関東地域DC・夜便",
            measured_count=600,
            average_minutes=18,
            max_minutes=45,
            over_2h_count=0,
            site_name="関東地域DC",
            time_slot="night",
        ),
        # 中部地域DC（愛知）：相対的に待機が短い
        WaitTimeRow(
            bucket_label="中部地域DC・朝便",
            measured_count=1800,
            average_minutes=28,
            max_minutes=85,
            over_2h_count=0,
            site_name="中部地域DC",
            time_slot="morning",
        ),
        WaitTimeRow(
            bucket_label="中部地域DC・昼便",
            measured_count=2400,
            average_minutes=22,
            max_minutes=60,
            over_2h_count=0,
            site_name="中部地域DC",
            time_slot="midday",
        ),
        WaitTimeRow(
            bucket_label="中部地域DC・夕便",
            measured_count=1300,
            average_minutes=24,
            max_minutes=70,
            over_2h_count=0,
            site_name="中部地域DC",
            time_slot="evening",
        ),
        WaitTimeRow(
            bucket_label="中部地域DC・夜便",
            measured_count=300,
            average_minutes=15,
            max_minutes=35,
            over_2h_count=0,
            site_name="中部地域DC",
            time_slot="night",
        ),
        # 関西地域DC（大阪）：朝・夕は中程度
        WaitTimeRow(
            bucket_label="関西地域DC・朝便",
            measured_count=1400,
            average_minutes=32,
            max_minutes=95,
            over_2h_count=0,
            site_name="関西地域DC",
            time_slot="morning",
        ),
        WaitTimeRow(
            bucket_label="関西地域DC・昼便",
            measured_count=1900,
            average_minutes=22,
            max_minutes=60,
            over_2h_count=0,
            site_name="関西地域DC",
            time_slot="midday",
        ),
        WaitTimeRow(
            bucket_label="関西地域DC・夕便",
            measured_count=900,
            average_minutes=26,
            max_minutes=70,
            over_2h_count=0,
            site_name="関西地域DC",
            time_slot="evening",
        ),
        WaitTimeRow(
            bucket_label="関西地域DC・夜便",
            measured_count=300,
            average_minutes=16,
            max_minutes=40,
            over_2h_count=0,
            site_name="関西地域DC",
            time_slot="night",
        ),
    ],
    handling_time_rows=[
        HandlingTimeRow(
            bucket_label="パレット納品（チルド）",
            measured_count=6800,
            average_minutes=35,
            max_minutes=70,
            over_1h_pct=2.0,
        ),
        HandlingTimeRow(
            bucket_label="パレット納品（常温）",
            measured_count=8200,
            average_minutes=28,
            max_minutes=55,
            over_1h_pct=0.0,
        ),
        HandlingTimeRow(
            bucket_label="バラ納品（生鮮）",
            measured_count=2500,
            average_minutes=58,
            max_minutes=110,
            over_1h_pct=18.0,
        ),
    ],
    kpi_history=[
        KpiHistoryEntry(fy=2023, metric="load_factor_pct", value=39.0, unit="%"),
        KpiHistoryEntry(fy=2024, metric="load_factor_pct", value=41.0, unit="%"),
        KpiHistoryEntry(fy=2025, metric="load_factor_pct", value=42.0, unit="%"),
        KpiHistoryEntry(fy=2023, metric="wait_time_avg_minutes", value=34.0, unit="分"),
        KpiHistoryEntry(fy=2024, metric="wait_time_avg_minutes", value=30.0, unit="分"),
        KpiHistoryEntry(fy=2025, metric="wait_time_avg_minutes", value=28.0, unit="分"),
    ],
)


# サンプル一覧
ALL_SAMPLES: dict[str, CompanyProfile] = {
    SAMPLE_MANUFACTURING.company_id: SAMPLE_MANUFACTURING,
    SAMPLE_WHOLESALE.company_id: SAMPLE_WHOLESALE,
    SAMPLE_CHAIN.company_id: SAMPLE_CHAIN,
    SAMPLE_RETAIL.company_id: SAMPLE_RETAIL,
}


def list_sample_ids() -> tuple[str, ...]:
    """登録済みサンプル企業 ID をタプルで返す。

    エラーメッセージや API バリデーションで参照する単一情報源。
    """
    return tuple(ALL_SAMPLES.keys())


def format_sample_ids(separator: str = " / ") -> str:
    """サンプル企業 ID を separator で連結して返す（エラーメッセージ用）。"""
    return separator.join(ALL_SAMPLES.keys())


def get_sample(company_id: str) -> CompanyProfile | None:
    """企業プロフィールを ID で取得する。

    優先順位:
        1. 実データ JSON（outputs/profiles/<company_id>.json）— フェーズ4.0 で取込
        2. サンプル辞書（ALL_SAMPLES）

    Args:
        company_id: 企業 ID

    Returns:
        CompanyProfile（実データ優先）、未登録なら None
    """
    # 循環 import 回避のため遅延 import
    from core.io.company_store import load_company_profile_from_json

    loaded = load_company_profile_from_json(company_id)
    if loaded is not None:
        return loaded
    return ALL_SAMPLES.get(company_id)
