"""自社プロフィール仮データ（フェーズ4 まで使用するサンプル3社）。

注意:
    - フェーズ4 で実データアップロード機能を実装するまでの暫定。
    - サンプル企業名・数値は架空であり、実在する企業とは無関係。
    - 公式記載事例集（core/templates/clo_plan_examples/）と業種コードを揃えてある。
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SiteType = Literal["factory", "dc", "store", "office", "warehouse"]


class CompanySite(BaseModel):
    """自社拠点。"""

    name: str = Field(..., description="拠点名")
    site_type: SiteType = Field(..., description="拠点種別")
    prefecture: str = Field(..., description="都道府県名（正式名称）")
    annual_freight_tons: float = Field(..., ge=0, description="年間取扱貨物量（トン）")


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
    is_chain_franchise: bool = Field(False, description="連鎖化事業者か")
    fleet_count_owned: int = Field(0, ge=0, description="自社保有車両数")
    fleet_count_outsourced: int = Field(0, ge=0, description="委託車両数（おおよそ）")
    sites: list[CompanySite] = Field(default_factory=list, description="拠点リスト")
    clo_name: str = Field(..., description="CLO 役職・氏名")
    plan_period_start_fy: int = Field(..., ge=2026, description="計画期間 開始年度")
    plan_period_end_fy: int = Field(..., ge=2026, description="計画期間 終了年度")


# サンプル1: 製造業（電子部品）— 特定第一種荷主想定
SAMPLE_MANUFACTURING = CompanyProfile(
    company_id="sample_mfg_01",
    name="テクノパーツ製造株式会社（架空）",
    jsic_code="3159",
    main_business="その他の電子部品・デバイス製造業",
    annual_revenue_jpy=85_000_000_000,    # 850 億円
    annual_freight_tons_total=120_000.0,  # 12 万トン（特定第一種荷主該当）
    is_chain_franchise=False,
    fleet_count_owned=12,
    fleet_count_outsourced=180,
    sites=[
        CompanySite(name="本社工場", site_type="factory",
                    prefecture="愛知県", annual_freight_tons=70_000),
        CompanySite(name="東日本物流センター", site_type="dc",
                    prefecture="埼玉県", annual_freight_tons=30_000),
        CompanySite(name="西日本物流センター", site_type="dc",
                    prefecture="兵庫県", annual_freight_tons=20_000),
    ],
    clo_name="専務執行役員 田中 雄一",
    plan_period_start_fy=2026,
    plan_period_end_fy=2030,
)

# サンプル2: 卸売業（インテリア）— 特定第一種・第二種荷主想定
SAMPLE_WHOLESALE = CompanyProfile(
    company_id="sample_wholesale_01",
    name="株式会社インテリアリンク商事（架空）",
    jsic_code="5514",
    main_business="室内装飾繊維品卸売業",
    annual_revenue_jpy=42_000_000_000,    # 420 億円
    annual_freight_tons_total=180_000.0,  # 18 万トン（第一種・第二種双方該当）
    is_chain_franchise=False,
    fleet_count_owned=8,
    fleet_count_outsourced=240,
    sites=[
        CompanySite(name="関東センター", site_type="dc",
                    prefecture="千葉県", annual_freight_tons=70_000),
        CompanySite(name="関西センター", site_type="dc",
                    prefecture="大阪府", annual_freight_tons=55_000),
        CompanySite(name="九州センター", site_type="dc",
                    prefecture="福岡県", annual_freight_tons=30_000),
        CompanySite(name="東北センター", site_type="dc",
                    prefecture="宮城県", annual_freight_tons=25_000),
    ],
    clo_name="専務執行役員 佐藤 一郎",
    plan_period_start_fy=2026,
    plan_period_end_fy=2030,
)

# サンプル3: 連鎖化事業者（コンビニ本部）
SAMPLE_CHAIN = CompanyProfile(
    company_id="sample_chain_01",
    name="スマートマート株式会社（架空）",
    jsic_code="5891",
    main_business="コンビニエンスストア",
    annual_revenue_jpy=320_000_000_000,   # 3,200 億円
    annual_freight_tons_total=450_000.0,  # 45 万トン
    is_chain_franchise=True,
    fleet_count_owned=0,
    fleet_count_outsourced=850,
    sites=[
        CompanySite(name="関東第一センター", site_type="dc",
                    prefecture="埼玉県", annual_freight_tons=180_000),
        CompanySite(name="関東第二センター", site_type="dc",
                    prefecture="神奈川県", annual_freight_tons=120_000),
        CompanySite(name="関西センター", site_type="dc",
                    prefecture="大阪府", annual_freight_tons=100_000),
        CompanySite(name="九州センター", site_type="dc",
                    prefecture="福岡県", annual_freight_tons=50_000),
    ],
    clo_name="専務執行役員 佐藤 一郎",
    plan_period_start_fy=2026,
    plan_period_end_fy=2030,
)


# サンプル一覧
ALL_SAMPLES: dict[str, CompanyProfile] = {
    SAMPLE_MANUFACTURING.company_id: SAMPLE_MANUFACTURING,
    SAMPLE_WHOLESALE.company_id: SAMPLE_WHOLESALE,
    SAMPLE_CHAIN.company_id: SAMPLE_CHAIN,
}


def get_sample(company_id: str) -> CompanyProfile | None:
    """サンプル企業を ID で取得する。"""
    return ALL_SAMPLES.get(company_id)
