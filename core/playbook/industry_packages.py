"""業種別 CLO 標準パッケージ（フェーズ5.0 段階 c の中核）。

CLO ごとに「ゼロから設計」していた KPI / 施策 / 会議体 / レポート / データ収集を
業種別に「標準型」として固定し、個社の差分（Override）だけを管理する仕組み。

設計方針:
    - 4 業種（manufacturing / wholesale / retail / chain_franchise）× 5 要素の
      標準パッケージを定数として保持（IndustryPackage）
    - 標準値の根拠は **国の制度・公表値** に限定し、自社実証なき野心目標は載せない
    - 推測で埋めない（target_value=None）方針を厳守。CLO 計画書での defensibility 担保
    - 個社差分は CompanyPackageOverride で別管理し、Override 4 分類で減点制御
      （unmanaged のみ減点・F2 単調性確保 / Codex 勧告④）

Codex レビュー反映（2026-05-06）:
    Codex 業種別 KPI 数値妥当性レビューで以下の修正を反映済:
    - 積載率全業種: 38→44%（国の 2028 年度全体目標に合わせる）
      旧案 manufacturing 55% / wholesale 52% は業界実績 1.5-3pp/年 を超え
      根拠不足のため取下げ。実装事例ある企業は Override で挑戦値を積む
    - 在庫回転数 / 共配率 / 配送便数削減 等は target_value=None
      （標準値の根拠が国・JILS で確認できないため）
    - Codex 単独提案「荷待ち+荷役等 ≤60 分/回」「物流コスト/売上比率」を全業種に追加

出典の信頼性ヒエラルキー（経営会議 defensibility 順）:
    1. 告示・省令（厚労省告示第367号、物流効率化法 第46条/第65条）
    2. 公表ガイドライン（共同ガイドライン Ver.3.2 等）
    3. 業界統計（JILS物流コスト調査・自動車輸送統計年報）
    4. 政府試算（国交省2030年試算）

plan: plans/b-c-flickering-pixel.md §段階 c
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from core.static.industry_benchmarks import LOGISTICS_COST_RATIO
from core.static.jsic import JsicCategory

# ---------------------------------------------------------------------------
# 型エイリアス
# ---------------------------------------------------------------------------

KpiFrequency = Literal["daily", "weekly", "monthly", "quarterly", "annual"]
MeetingFrequency = Literal[
    "weekly", "biweekly", "monthly", "quarterly", "annual",
]
ReportFrequency = Literal["weekly", "monthly", "quarterly", "annual"]
ReportAudience = Literal["board", "clo", "operation", "external_partner"]
OutputFormat = Literal["ppt", "docx", "excel", "markdown"]
DataItemSource = Literal["tms", "wms", "manual", "gps", "pos", "edi"]
RefreshCadence = Literal["realtime", "daily", "weekly", "monthly"]

OverrideCategory = Literal[
    "unmanaged_deviation",       # 管理されていない逸脱（減点対象）
    "approved_better_practice",  # 承認済の良い差別化（減点なし、bonus 候補）
    "required_localization",     # 立地・規模特性で必要な調整（減点なし）
    "temporary_exception",       # 期限付き例外（減点緩和、期限超過で減点）
]
"""Codex 勧告④: F2 標準化スコアの単調性破壊を避けるため、override 4 分類で
減点対象を unmanaged のみに限定する。
"""

OverrideTargetKind = Literal["kpi", "measure", "meeting", "report", "data_item"]


# ---------------------------------------------------------------------------
# 標準定義モデル群（Pydantic v2）
# ---------------------------------------------------------------------------


class StandardKpiDef(BaseModel):
    """業種別 標準 KPI 1 件分の定義。"""

    model_config = ConfigDict(frozen=True)

    metric_id: str = Field(description="snake_case 内部識別子")
    label: str = Field(description="表示名（日本語）")
    target_value: float | None = Field(
        default=None,
        description=(
            "標準目標値。国・JILS 等で根拠が確認できない場合は None で残す。"
            "自社実証ある企業は Override で挑戦値を積み上げる"
        ),
    )
    unit: str = Field(description="単位（例: '%', '分', 'g/トンキロ', '円/SKU'）")
    baseline_value: float | None = Field(
        default=None,
        description="業界平均ベースライン値（None なら未設定）",
    )
    frequency: KpiFrequency = Field(description="計測・報告頻度")
    owner_role: str = Field(description="主管部門・役職（日本語）")
    legal_basis: str | None = Field(
        default=None,
        description="法令・告示・公表ガイドライン等の根拠 URL もしくは文書名",
    )
    related_measure_ids: list[str] = Field(
        default_factory=list,
        description="この KPI に紐付く施策の measure_id（measures.ALL_MEASURES に存在）",
    )


class StandardMeetingDef(BaseModel):
    """業種別 標準会議体 1 件分の定義。"""

    model_config = ConfigDict(frozen=True)

    meeting_id: str
    name: str
    frequency: MeetingFrequency
    participants: list[str] = Field(default_factory=list)
    agenda_items: list[str] = Field(default_factory=list)
    standard_duration_min: int = Field(ge=15)
    output_artifact: str = Field(description="会議のアウトプット（議事録/承認書等）")


class StandardReportDef(BaseModel):
    """業種別 標準レポート 1 件分の定義。"""

    model_config = ConfigDict(frozen=True)

    report_id: str
    name: str
    audience: ReportAudience
    frequency: ReportFrequency
    source_kpi_ids: list[str] = Field(default_factory=list)
    output_format: OutputFormat
    related_meeting_ids: list[str] = Field(default_factory=list)


class StandardDataItemDef(BaseModel):
    """業種別 標準データ項目 1 件分の定義（収集すべきデータ）。"""

    model_config = ConfigDict(frozen=True)

    data_item_id: str
    label: str
    source: DataItemSource
    refresh_cadence: RefreshCadence
    used_by_kpi_ids: list[str] = Field(default_factory=list)


class IndustryPackage(BaseModel):
    """業種別 CLO 標準パッケージ（4 業種 × 5 要素マトリクス）。"""

    model_config = ConfigDict(frozen=True)

    category: JsicCategory
    label: str = Field(description="表示名（例: '製造業 標準パッケージ v1'）")
    version: str = Field(description="バージョン（例: '2026.04'）")
    kpis: list[StandardKpiDef]
    measure_ids: list[str] = Field(
        description="measures.ALL_MEASURES に存在する measure_id のサブセット",
    )
    meetings: list[StandardMeetingDef] = Field(default_factory=list)
    reports: list[StandardReportDef] = Field(default_factory=list)
    data_items: list[StandardDataItemDef] = Field(default_factory=list)
    plan_template_paths: dict[str, str] = Field(
        default_factory=dict,
        description="starter/advanced -> templates/clo_plan_examples/<file> パス",
    )
    benchmark_refs: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Override モデル（個社差分）
# ---------------------------------------------------------------------------


class OverrideEntry(BaseModel):
    """1 件の個社差分。Override 4 分類で減点制御する。"""

    model_config = ConfigDict(frozen=True)

    target_kind: OverrideTargetKind
    target_id: str = Field(description="metric_id / measure_id / meeting_id 等")
    category: OverrideCategory
    rationale: str = Field(description="差分の理由（経営層への説明文）")
    approved_by: str | None = Field(
        default=None, description="CLO 名（approved_better_practice / temporary_exception 必須）",
    )
    expires_at: date | None = Field(
        default=None, description="temporary_exception のみ必須",
    )
    diff: dict[str, object] = Field(
        default_factory=dict,
        description="元 vs 上書き値の差分（target_value: 50.0 等）",
    )


class CompanyPackageOverride(BaseModel):
    """企業ごとの差分集合。outputs/profiles/<id>_override.json に永続化。"""

    model_config = ConfigDict(frozen=True)

    company_id: str
    base_industry: JsicCategory
    entries: list[OverrideEntry] = Field(default_factory=list)
    last_reviewed: date


# ---------------------------------------------------------------------------
# 4 業種の標準パッケージ定義（Codex レビュー反映済）
# ---------------------------------------------------------------------------

# 出典 URL の頻出表現（DRY）
_PORTAL_SHIPPER = (
    "https://www.revised-logistics-act-portal.mlit.go.jp/sippers/judgment-criteria/"
)
_PORTAL_CHAIN = (
    "https://www.revised-logistics-act-portal.mlit.go.jp/chained/judgment-criteria/"
)
_PORTAL_METHOD = (
    "https://www.revised-logistics-act-portal.mlit.go.jp/method/"
)
_METI_BASIC_POLICY = (
    "https://www.meti.go.jp/shingikai/sankoshin/shomu_ryutsu/distribution/"
    "pdf/001_02_00.pdf"
)
_MLIT_TRANSPORT_POLICY = (
    "https://www.mlit.go.jp/sogoseisaku/transport/sosei_transport_tk_000146.html"
)
_GREEN_GUIDELINE = (
    "https://www.greenpartnership.jp/co2/guidelinev3.1.pdf"
)
_JILS_COST_SURVEY = (
    "https://www1.logistics.or.jp/wp-content/uploads/2025/03/"
    "3f8d0e0cf2fc5ee6bf95df2731cf078e.pdf"
)


def _common_kpis(industry: JsicCategory) -> list[StandardKpiDef]:
    """全業種共通の追加 KPI 2 件（Codex 単独提案）。

    - wait_handling_per_run_max_minutes: 物流効率化法ポータル判断基準
    - logistics_cost_revenue_ratio_pct  : JILS 物流コスト調査
    """
    cost_baseline = LOGISTICS_COST_RATIO.get(industry)
    return [
        StandardKpiDef(
            metric_id="wait_handling_per_run_max_minutes",
            label="1回受渡し当たり 荷待ち+荷役等時間（最大）",
            target_value=60.0,
            unit="分",
            baseline_value=None,
            frequency="monthly",
            owner_role="物流部",
            legal_basis=_PORTAL_METHOD,
            related_measure_ids=["berth_booking_vbs", "delivery_time_distribution"],
        ),
        StandardKpiDef(
            metric_id="logistics_cost_revenue_ratio_pct",
            label="物流コスト売上高比率",
            target_value=None,  # JILS 調査は実績値ベース、目標は自社前年比で管理
            unit="%",
            baseline_value=(cost_baseline * 100.0) if cost_baseline else None,
            frequency="annual",
            owner_role="物流部・経営企画",
            legal_basis=_JILS_COST_SURVEY,
            related_measure_ids=[
                "load_factor_tms", "joint_delivery_competitor", "warehouse_dx_wms",
            ],
        ),
    ]


# 製造業 ─────────────────────────────────────────────────────────────
_MANUFACTURING_PACKAGE = IndustryPackage(
    category="manufacturing",
    label="製造業 標準パッケージ v1（Codex レビュー反映済）",
    version="2026.05",
    kpis=[
        StandardKpiDef(
            metric_id="load_factor_pct",
            label="積載率",
            target_value=44.0,  # 国の 2028 年度全体目標（Codex 修正：旧案 55% は根拠不足）
            unit="%",
            baseline_value=38.0,
            frequency="monthly",
            owner_role="物流部",
            legal_basis=_METI_BASIC_POLICY,
            related_measure_ids=["load_factor_tms", "modal_shift_to_rail"],
        ),
        StandardKpiDef(
            metric_id="co2_intensity_reduction_pct",
            label="CO2 排出原単位削減率（2013 年比）",
            target_value=23.4,  # 国家目標と整合
            unit="%",
            baseline_value=None,
            frequency="annual",
            owner_role="物流部・サステナビリティ部",
            legal_basis=_MLIT_TRANSPORT_POLICY,
            related_measure_ids=["modal_shift_to_rail", "load_factor_tms"],
        ),
        StandardKpiDef(
            metric_id="wait_time_avg_minutes",
            label="荷待ち時間 平均",
            target_value=30.0,  # WAIT_TIME_STANDARD.avg_target_minutes と整合
            unit="分",
            baseline_value=None,
            frequency="monthly",
            owner_role="物流部",
            legal_basis=_PORTAL_METHOD,
            related_measure_ids=["berth_booking_vbs", "delivery_time_distribution"],
        ),
        *_common_kpis("manufacturing"),
    ],
    measure_ids=[
        "modal_shift_to_rail",
        "load_factor_tms",
        "relay_transport",
        "warehouse_dx_wms",
        "pallet_standardization",
        "visualization_baseline",
    ],
    meetings=[
        StandardMeetingDef(
            meeting_id="monthly_logistics_efficiency",
            name="月次 物流効率化委員会",
            frequency="monthly",
            participants=["CLO", "物流部長", "情報システム部", "調達部"],
            agenda_items=[
                "KPI 月次進捗（積載率・CO2 原単位・荷待ち平均）",
                "施策実装ステータス（TMS / モーダルシフト）",
                "改善基準告示遵守状況の確認",
            ],
            standard_duration_min=90,
            output_artifact="議事録 + 月次 KPI レポート",
        ),
        StandardMeetingDef(
            meeting_id="quarterly_executive",
            name="四半期 経営会議（物流アジェンダ）",
            frequency="quarterly",
            participants=["代表取締役", "CLO", "CFO", "事業部長"],
            agenda_items=[
                "中長期計画進捗",
                "投資判断（次四半期）",
                "リスクレビュー（荷主取引・ドライバー需給）",
            ],
            standard_duration_min=60,
            output_artifact="決議書",
        ),
        StandardMeetingDef(
            meeting_id="annual_partner_summit",
            name="年次 取引先合同会議",
            frequency="annual",
            participants=["CLO", "取引先 物流責任者", "運送会社"],
            agenda_items=[
                "次年度 共配・モーダルシフト計画",
                "パレット標準化進捗",
            ],
            standard_duration_min=180,
            output_artifact="協定書 / MOU",
        ),
    ],
    reports=[
        StandardReportDef(
            report_id="monthly_kpi",
            name="月次 KPI レポート",
            audience="clo",
            frequency="monthly",
            source_kpi_ids=["load_factor_pct", "wait_time_avg_minutes"],
            output_format="excel",
            related_meeting_ids=["monthly_logistics_efficiency"],
        ),
        StandardReportDef(
            report_id="quarterly_board",
            name="四半期 取締役会レポート",
            audience="board",
            frequency="quarterly",
            source_kpi_ids=[
                "load_factor_pct", "co2_intensity_reduction_pct",
                "logistics_cost_revenue_ratio_pct",
            ],
            output_format="ppt",
            related_meeting_ids=["quarterly_executive"],
        ),
        StandardReportDef(
            report_id="annual_form5",
            name="年次 様式第5（定期報告書／第46条）",
            audience="external_partner",
            frequency="annual",
            source_kpi_ids=[
                "load_factor_pct", "wait_time_avg_minutes",
                "co2_intensity_reduction_pct",
            ],
            output_format="docx",
            related_meeting_ids=[],
        ),
    ],
    data_items=[
        StandardDataItemDef(
            data_item_id="load_factor_by_site",
            label="拠点別積載率",
            source="tms",
            refresh_cadence="daily",
            used_by_kpi_ids=["load_factor_pct"],
        ),
        StandardDataItemDef(
            data_item_id="truck_gps_log",
            label="トラック別 GPS ログ",
            source="gps",
            refresh_cadence="realtime",
            used_by_kpi_ids=["load_factor_pct", "wait_time_avg_minutes"],
        ),
        StandardDataItemDef(
            data_item_id="tms_dispatch",
            label="TMS 配車データ",
            source="tms",
            refresh_cadence="daily",
            used_by_kpi_ids=["load_factor_pct"],
        ),
    ],
    plan_template_paths={
        "starter": "core/templates/clo_plan_examples/manufacturing_report_starter.md",
        "advanced": "core/templates/clo_plan_examples/manufacturing_report_advanced.md",
    },
    benchmark_refs=[
        "industry_benchmarks.LOGISTICS_COST_RATIO['manufacturing']",
        "industry_benchmarks.LOAD_FACTOR_INDUSTRY_AVG_PCT",
    ],
    notes=[
        "積載率目標 44% は国の 2028 年度全体目標。"
        "55% を狙う企業は Override（approved_better_practice）で個別管理する",
        "様式第5 は物流効率化法 第46条（特定荷主の中長期計画作成義務）",
    ],
)


# 卸売業 ──────────────────────────────────────────────────────────────
_WHOLESALE_PACKAGE = IndustryPackage(
    category="wholesale",
    label="卸売業 標準パッケージ v1（Codex レビュー反映済）",
    version="2026.05",
    kpis=[
        StandardKpiDef(
            metric_id="load_factor_pct",
            label="積載率",
            target_value=44.0,  # 国の 2028 年度全体目標（Codex 修正：旧案 52% は根拠不足）
            unit="%",
            baseline_value=38.0,
            frequency="monthly",
            owner_role="物流部",
            legal_basis=_METI_BASIC_POLICY,
            related_measure_ids=["joint_delivery_competitor", "load_factor_tms"],
        ),
        StandardKpiDef(
            metric_id="inventory_turnover_improvement_pct",
            label="在庫回転数 自社前年比",
            target_value=None,  # 標準値は国・JILS 未確認のため None（Codex 修正）
            unit="%",
            baseline_value=None,
            frequency="quarterly",
            owner_role="物流部・営業部",
            legal_basis=None,
            related_measure_ids=["warehouse_dx_wms", "lead_time_review"],
        ),
        StandardKpiDef(
            metric_id="wait_time_avg_minutes",
            label="荷待ち時間 平均",
            target_value=45.0,  # 物流効率化法ポータル「荷待ち+荷役等1時間以内」整合
            unit="分",
            baseline_value=None,
            frequency="monthly",
            owner_role="物流部",
            legal_basis=_PORTAL_SHIPPER,
            related_measure_ids=["berth_booking_vbs"],
        ),
        StandardKpiDef(
            metric_id="joint_delivery_target_route_share_pct",
            label="共同配送 対象ルート比率",
            target_value=None,  # Codex 修正：30% 標準値は国・JILS 未確認のため None
            unit="%",
            baseline_value=None,
            frequency="quarterly",
            owner_role="物流部・営業部",
            legal_basis=None,
            related_measure_ids=["joint_delivery_competitor"],
        ),
        *_common_kpis("wholesale"),
    ],
    measure_ids=[
        "joint_delivery_competitor",
        "pallet_standardization",
        "berth_booking_vbs",
        "warehouse_dx_wms",
        "load_factor_tms",
        "visualization_baseline",
    ],
    meetings=[
        StandardMeetingDef(
            meeting_id="monthly_joint_delivery",
            name="月次 共同配送パートナー会議",
            frequency="monthly",
            participants=["CLO", "物流部長", "共配パートナー"],
            agenda_items=["共配便数進捗", "個建運賃精算", "新規ルート提案"],
            standard_duration_min=60,
            output_artifact="議事録",
        ),
        StandardMeetingDef(
            meeting_id="monthly_logistics_cost",
            name="月次 物流コスト会議",
            frequency="monthly",
            participants=["CLO", "CFO", "物流部長", "情報システム部"],
            agenda_items=["物流コスト/売上比率", "WMS 投資 ROI", "在庫回転数"],
            standard_duration_min=60,
            output_artifact="月次コスト分析",
        ),
    ],
    reports=[
        StandardReportDef(
            report_id="monthly_joint_progress",
            name="月次 共配進捗レポート",
            audience="external_partner",
            frequency="monthly",
            source_kpi_ids=["joint_delivery_target_route_share_pct"],
            output_format="excel",
            related_meeting_ids=["monthly_joint_delivery"],
        ),
        StandardReportDef(
            report_id="monthly_profit_contribution",
            name="月次 利益貢献レポート",
            audience="board",
            frequency="monthly",
            source_kpi_ids=[
                "logistics_cost_revenue_ratio_pct",
                "inventory_turnover_improvement_pct",
            ],
            output_format="ppt",
            related_meeting_ids=["monthly_logistics_cost"],
        ),
        StandardReportDef(
            report_id="annual_form5",
            name="年次 様式第5（定期報告書／第46条）",
            audience="external_partner",
            frequency="annual",
            source_kpi_ids=[
                "load_factor_pct", "wait_time_avg_minutes",
            ],
            output_format="docx",
            related_meeting_ids=[],
        ),
    ],
    data_items=[
        StandardDataItemDef(
            data_item_id="vendor_arrival_time",
            label="仕入先別到着時刻",
            source="manual",
            refresh_cadence="daily",
            used_by_kpi_ids=["wait_time_avg_minutes"],
        ),
        StandardDataItemDef(
            data_item_id="joint_delivery_partner_runs",
            label="共配相手便数",
            source="edi",
            refresh_cadence="weekly",
            used_by_kpi_ids=["joint_delivery_target_route_share_pct"],
        ),
        StandardDataItemDef(
            data_item_id="wms_inventory",
            label="WMS 在庫データ",
            source="wms",
            refresh_cadence="daily",
            used_by_kpi_ids=["inventory_turnover_improvement_pct"],
        ),
    ],
    plan_template_paths={
        "starter": "core/templates/clo_plan_examples/wholesale_starter.md",
        "advanced": "core/templates/clo_plan_examples/wholesale_advanced.md",
    },
    benchmark_refs=[
        "industry_benchmarks.LOGISTICS_COST_RATIO['wholesale']",
    ],
    notes=[
        "卸売業の物流コスト/売上比率は 4.8%（JILS 2021）— 製造業より高く、改善レバレッジ大",
        "共配率の標準値は未確定。Override approved_better_practice で個別管理推奨",
    ],
)


# 小売業 ──────────────────────────────────────────────────────────────
_RETAIL_PACKAGE = IndustryPackage(
    category="retail",
    label="小売業 標準パッケージ v1（Codex レビュー反映済）",
    version="2026.05",
    kpis=[
        StandardKpiDef(
            metric_id="delivery_trip_reduction_pct",
            label="配送便数削減率（自社前年比）",
            # Codex 修正：20% 標準値は事例水準のみ、標準パッケージ値としては None
            target_value=None,
            unit="%",
            baseline_value=None,
            frequency="quarterly",
            owner_role="物流部・営業部",
            legal_basis=None,
            related_measure_ids=["delivery_time_distribution", "lead_time_review"],
        ),
        StandardKpiDef(
            metric_id="store_delivery_appropriate_lead_time_compliance_pct",
            label="店舗納品 適正リードタイム遵守率",
            target_value=None,  # Codex 修正：「短縮」より「適正遵守」に変更し target=None
            unit="%",
            baseline_value=None,
            frequency="monthly",
            owner_role="物流部・営業部",
            legal_basis=_PORTAL_SHIPPER,
            related_measure_ids=["lead_time_review", "delivery_time_distribution"],
        ),
        StandardKpiDef(
            metric_id="logistics_cost_per_sku",
            label="SKU 当たり物流コスト",
            target_value=None,  # Codex 修正：JILS は売上比率ベースのため SKU 当たりは None
            unit="円/SKU",
            baseline_value=None,
            frequency="quarterly",
            owner_role="物流部",
            legal_basis=_JILS_COST_SURVEY,
            related_measure_ids=["warehouse_dx_wms"],
        ),
        StandardKpiDef(
            metric_id="load_factor_pct",
            label="積載率",
            target_value=44.0,  # 国の 2028 年度全体目標
            unit="%",
            baseline_value=38.0,
            frequency="monthly",
            owner_role="物流部",
            legal_basis=_METI_BASIC_POLICY,
            related_measure_ids=["load_factor_tms", "delivery_time_distribution"],
        ),
        *_common_kpis("retail"),
    ],
    measure_ids=[
        "berth_booking_vbs",
        "delivery_time_distribution",
        "lead_time_review",
        "load_factor_tms",
        "warehouse_dx_wms",
        "visualization_baseline",
    ],
    meetings=[
        StandardMeetingDef(
            meeting_id="monthly_store_ops",
            name="月次 店舗オペ会議",
            frequency="monthly",
            participants=["CLO", "店舗運営部", "物流部"],
            agenda_items=["店舗納品遵守率", "配送便数進捗", "SKU 削減レビュー"],
            standard_duration_min=60,
            output_artifact="議事録",
        ),
        StandardMeetingDef(
            meeting_id="quarterly_unloading_partner",
            name="四半期 着荷主合同会議",
            frequency="quarterly",
            participants=["CLO", "着荷主", "運送会社"],
            agenda_items=["納品時間帯分散", "リードタイム協議"],
            standard_duration_min=120,
            output_artifact="協定改定",
        ),
    ],
    reports=[
        StandardReportDef(
            report_id="monthly_store_delivery",
            name="月次 店舗別配送レポート",
            audience="operation",
            frequency="monthly",
            source_kpi_ids=[
                "store_delivery_appropriate_lead_time_compliance_pct",
                "delivery_trip_reduction_pct",
            ],
            output_format="excel",
            related_meeting_ids=["monthly_store_ops"],
        ),
        StandardReportDef(
            report_id="quarterly_executive",
            name="四半期 経営層レポート",
            audience="board",
            frequency="quarterly",
            source_kpi_ids=[
                "load_factor_pct",
                "logistics_cost_revenue_ratio_pct",
                "logistics_cost_per_sku",
            ],
            output_format="ppt",
            related_meeting_ids=[],
        ),
        StandardReportDef(
            report_id="annual_form5",
            name="年次 様式第5（定期報告書／第46条）",
            audience="external_partner",
            frequency="annual",
            source_kpi_ids=[
                "load_factor_pct", "wait_handling_per_run_max_minutes",
            ],
            output_format="docx",
            related_meeting_ids=[],
        ),
    ],
    data_items=[
        StandardDataItemDef(
            data_item_id="store_delivery_actual",
            label="店舗別納品実績",
            source="manual",
            refresh_cadence="daily",
            used_by_kpi_ids=["store_delivery_appropriate_lead_time_compliance_pct"],
        ),
        StandardDataItemDef(
            data_item_id="vehicle_uptime",
            label="配送車両稼働ログ",
            source="gps",
            refresh_cadence="daily",
            used_by_kpi_ids=["load_factor_pct", "delivery_trip_reduction_pct"],
        ),
        StandardDataItemDef(
            data_item_id="ecr_signals",
            label="ECR シグナル（売上連動の発注情報）",
            source="pos",
            refresh_cadence="daily",
            used_by_kpi_ids=["delivery_trip_reduction_pct"],
        ),
    ],
    plan_template_paths={
        "starter": "core/templates/clo_plan_examples/retail_starter.md",
        "advanced": "core/templates/clo_plan_examples/retail_advanced.md",
    },
    benchmark_refs=[
        "industry_benchmarks.LOGISTICS_COST_RATIO['retail']",
    ],
    notes=[
        "小売の物流コスト/売上比率は 3.1%（JILS 2021）",
        "配送便数削減 20% 等は事例値のため、各社の実証根拠ある場合のみ Override で目標値を設定",
    ],
)


# 連鎖化事業者（コンビニ本部・FC本部） ──────────────────────────────
_CHAIN_FRANCHISE_PACKAGE = IndustryPackage(
    category="chain_franchise",
    label="連鎖化事業者（FC本部）標準パッケージ v1（Codex レビュー反映済）",
    version="2026.05",
    kpis=[
        StandardKpiDef(
            metric_id="joint_delivery_target_route_share_pp",
            label="共同配送 対象ルート比率（pp 改善）",
            target_value=None,  # Codex 修正：「率」を「対象ルート比率」に再定義し target=None
            unit="pp",
            baseline_value=None,
            frequency="quarterly",
            owner_role="物流部・加盟店本部",
            legal_basis=_PORTAL_CHAIN,
            related_measure_ids=["joint_delivery_competitor"],
        ),
        StandardKpiDef(
            metric_id="store_delivery_window_compliance_pct",
            label="店舗納品 指定時間枠内納品率",
            target_value=None,  # Codex 修正：95% は SLA 一般値で公的根拠未確認のため None
            unit="%",
            baseline_value=None,
            frequency="monthly",
            owner_role="物流部",
            legal_basis=_PORTAL_CHAIN,
            related_measure_ids=["delivery_time_distribution", "berth_booking_vbs"],
        ),
        StandardKpiDef(
            metric_id="load_factor_by_temperature_zone_pct",
            label="温度帯別 積載率",
            target_value=None,  # Codex 評価：方向性 green、温度帯別の標準数値は未確認のため None
            unit="%",
            baseline_value=None,
            frequency="monthly",
            owner_role="物流部",
            legal_basis=_PORTAL_CHAIN,
            related_measure_ids=["load_factor_tms"],
        ),
        StandardKpiDef(
            metric_id="load_factor_pct",
            label="積載率（総合）",
            target_value=44.0,  # 国の 2028 年度全体目標
            unit="%",
            baseline_value=38.0,
            frequency="monthly",
            owner_role="物流部",
            legal_basis=_METI_BASIC_POLICY,
            related_measure_ids=["load_factor_tms", "joint_delivery_competitor"],
        ),
        *_common_kpis("chain_franchise"),
    ],
    measure_ids=[
        # Codex 勧告: 連鎖化は loading セクション施策（warehouse_dx_wms / pallet_standardization）
        # を必須から除外。様式第3「第5条関係」では荷役等時間短縮の記載は不要
        "joint_delivery_competitor",
        "berth_booking_vbs",
        "load_factor_tms",
        "delivery_time_distribution",
        "visualization_baseline",
    ],
    meetings=[
        StandardMeetingDef(
            meeting_id="monthly_franchise_logistics",
            name="月次 加盟店物流連絡会議",
            frequency="monthly",
            participants=["CLO", "加盟店代表", "物流部"],
            agenda_items=["納品遵守率", "共配進捗", "ベンダー納入時刻"],
            standard_duration_min=90,
            output_artifact="議事録 + 月次配信",
        ),
        StandardMeetingDef(
            meeting_id="monthly_vendor",
            name="月次 ベンダー会議",
            frequency="monthly",
            participants=["CLO", "ベンダー代表", "物流部"],
            agenda_items=["納入時刻調整", "温度帯別積載率"],
            standard_duration_min=60,
            output_artifact="議事録",
        ),
    ],
    reports=[
        StandardReportDef(
            report_id="monthly_franchise",
            name="月次 加盟店向けレポート",
            audience="external_partner",
            frequency="monthly",
            source_kpi_ids=["store_delivery_window_compliance_pct"],
            output_format="markdown",
            related_meeting_ids=["monthly_franchise_logistics"],
        ),
        StandardReportDef(
            report_id="monthly_vendor",
            name="月次 ベンダーレポート",
            audience="external_partner",
            frequency="monthly",
            source_kpi_ids=["load_factor_by_temperature_zone_pct"],
            output_format="excel",
            related_meeting_ids=["monthly_vendor"],
        ),
        StandardReportDef(
            report_id="annual_form5_chain",
            name="年次 様式第5（定期報告書／第65条）",
            audience="external_partner",
            frequency="annual",
            source_kpi_ids=[
                "load_factor_pct",
                "joint_delivery_target_route_share_pp",
                "store_delivery_window_compliance_pct",
            ],
            output_format="docx",
            related_meeting_ids=[],
        ),
    ],
    data_items=[
        StandardDataItemDef(
            data_item_id="temperature_zone_runs",
            label="温度帯別便数",
            source="tms",
            refresh_cadence="daily",
            used_by_kpi_ids=["load_factor_by_temperature_zone_pct"],
        ),
        StandardDataItemDef(
            data_item_id="store_pos",
            label="店舗別 POS",
            source="pos",
            refresh_cadence="realtime",
            used_by_kpi_ids=["store_delivery_window_compliance_pct"],
        ),
        StandardDataItemDef(
            data_item_id="vendor_invoice",
            label="ベンダー請求データ",
            source="edi",
            refresh_cadence="monthly",
            used_by_kpi_ids=["logistics_cost_revenue_ratio_pct"],
        ),
    ],
    plan_template_paths={
        "starter": "core/templates/clo_plan_examples/chain_starter.md",
        "advanced": "core/templates/clo_plan_examples/chain_advanced.md",
    },
    benchmark_refs=[
        "industry_benchmarks.LOGISTICS_COST_RATIO['chain_franchise']",
    ],
    notes=[
        "連鎖化事業者は様式第3「第5条関係」 — 荷役等時間短縮セクションは記載不要",
        "様式第5 は物流効率化法 第65条（特定連鎖化事業者の中長期計画作成義務）",
        "warehouse_dx_wms / pallet_standardization 等の loading 系施策は measure_ids から除外",
    ],
)


# ---------------------------------------------------------------------------
# パッケージ辞書 + 公開関数
# ---------------------------------------------------------------------------


ALL_PACKAGES: dict[JsicCategory, IndustryPackage] = {
    "manufacturing": _MANUFACTURING_PACKAGE,
    "wholesale": _WHOLESALE_PACKAGE,
    "retail": _RETAIL_PACKAGE,
    "chain_franchise": _CHAIN_FRANCHISE_PACKAGE,
}


def get_package(category: JsicCategory) -> IndustryPackage | None:
    """カテゴリ指定で標準パッケージを返す。未対応カテゴリは None。"""
    return ALL_PACKAGES.get(category)


def list_packages() -> list[IndustryPackage]:
    """全標準パッケージを順序固定で返す。"""
    return list(ALL_PACKAGES.values())


def build_industry_package_summary(
    package: IndustryPackage,
    override: CompanyPackageOverride | None = None,
) -> str:
    """経営層・CLO 向けの 1 段落サマリー（MCP / REST 共通）。

    package は resolve_company_package 適用後の状態を渡す前提。
    override は元の差分件数表示用に別途受け取り、4 分類別に件数を表示する。
    """
    kpi_count = len(package.kpis)
    measure_count = len(package.measure_ids)
    meeting_count = len(package.meetings)
    report_count = len(package.reports)
    data_item_count = len(package.data_items)
    lines = [
        f"業種パッケージ: {package.label}（version {package.version}）",
        (
            f"標準 KPI {kpi_count} 件 / 施策 {measure_count} 件 / "
            f"会議 {meeting_count} 件 / レポート {report_count} 件 / "
            f"データ項目 {data_item_count} 件"
        ),
    ]
    if override is None or not override.entries:
        lines.append("Override: なし（base パッケージそのまま）")
        return " / ".join(lines)

    counts: dict[OverrideCategory, int] = {
        "unmanaged_deviation": 0,
        "approved_better_practice": 0,
        "required_localization": 0,
        "temporary_exception": 0,
    }
    for entry in override.entries:
        counts[entry.category] = counts.get(entry.category, 0) + 1
    lines.append(
        f"Override 計 {len(override.entries)} 件: "
        f"unmanaged {counts['unmanaged_deviation']} / "
        f"承認済差別化 {counts['approved_better_practice']} / "
        f"必要ローカル {counts['required_localization']} / "
        f"期限付き例外 {counts['temporary_exception']}"
    )
    return " / ".join(lines)


def resolve_company_package(
    base_industry: JsicCategory,
    override: CompanyPackageOverride | None = None,
) -> IndustryPackage:
    """base + override を合成して個社向けパッケージを返す。

    現在の実装では Override 4 分類のうち以下のみが値の上書き対象:
        - approved_better_practice : KPI の target_value 上書きを許容
        - required_localization    : KPI の target_value 上書きを許容
        - temporary_exception      : 期限内のみ上書きを許容（期限後は base に戻る）
        - unmanaged_deviation      : 上書きせず、F2 標準化スコア側で減点される

    Args:
        base_industry: 業種カテゴリ（CompanyProfile.jsic_code から派生）
        override: 個社差分。None なら base パッケージそのまま

    Returns:
        IndustryPackage: 上書き反映済みのパッケージ（frozen）

    Raises:
        ValueError: base_industry が ALL_PACKAGES に存在しない
    """
    base = get_package(base_industry)
    if base is None:
        raise ValueError(
            f"未対応の業種カテゴリ: {base_industry!r}。"
            f"利用可能: {list(ALL_PACKAGES)}"
        )
    if override is None or not override.entries:
        return base

    today = date.today()
    new_kpis = list(base.kpis)
    for entry in override.entries:
        if entry.target_kind != "kpi":
            continue  # measure / meeting / report / data_item の上書きは未実装
        if entry.category == "unmanaged_deviation":
            continue  # 標準化スコアで減点する側
        if (
            entry.category == "temporary_exception"
            and entry.expires_at is not None
            and entry.expires_at < today
        ):
            continue  # 期限切れは base に戻す

        new_value = entry.diff.get("target_value")
        if not isinstance(new_value, (int, float)):
            continue  # target_value 以外の差分は未対応

        new_kpis = [
            kpi.model_copy(update={"target_value": float(new_value)})
            if kpi.metric_id == entry.target_id
            else kpi
            for kpi in new_kpis
        ]

    return base.model_copy(update={"kpis": new_kpis})


# ---------------------------------------------------------------------------
# 連鎖化事業者の強制ガード（c.8）
# ---------------------------------------------------------------------------

CHAIN_FRANCHISE_FORBIDDEN_KPI_PREFIXES: tuple[str, ...] = ("handling_",)
"""連鎖化事業者で禁止する KPI metric_id プレフィックス。
様式第3 第5条関係では荷役等時間短縮セクションが不要のため、
handling_* KPI は連鎖化パッケージに混入してはならない。"""

CHAIN_FRANCHISE_FORBIDDEN_FORM3_SECTIONS: tuple[str, ...] = ("loading",)
"""連鎖化事業者で禁止する form3_section。loading 系施策（warehouse_dx_wms,
pallet_standardization, relay_transport 等）は連鎖化の様式第3「第5条関係」では
記載しないため measure_ids から除外する。"""

CHAIN_FRANCHISE_REQUIRED_LEGAL_ARTICLE: str = "第65条"
"""連鎖化事業者の様式第5 報告書の法令根拠。第46条（特定荷主）ではなく
第65条（特定連鎖化事業者）を必ず使う。"""


def validate_chain_franchise_constraints(
    package: IndustryPackage,
) -> list[str]:
    """連鎖化パッケージの強制ガード違反を返す（c.8）。

    package.category != 'chain_franchise' の場合は空リスト。違反 0 件なら
    空リスト、違反があれば内容ごとに 1 行返す。モジュール load 時の sanity
    check + Override 適用後の再検証両方に使う。
    """
    if package.category != "chain_franchise":
        return []

    # 循環 import 回避のため遅延 import
    from core.playbook.measures import get_measure

    errors: list[str] = []

    for kpi in package.kpis:
        for prefix in CHAIN_FRANCHISE_FORBIDDEN_KPI_PREFIXES:
            if kpi.metric_id.startswith(prefix):
                errors.append(
                    f"連鎖化パッケージに禁止 KPI prefix {prefix!r} を持つ "
                    f"metric_id={kpi.metric_id!r} が含まれている",
                )

    for mid in package.measure_ids:
        measure = get_measure(mid)
        if measure is None:
            continue  # ALL_MEASURES 整合性は別テストで検証
        if measure.form3_section in CHAIN_FRANCHISE_FORBIDDEN_FORM3_SECTIONS:
            errors.append(
                f"連鎖化パッケージに form3_section={measure.form3_section!r} の "
                f"施策 {mid!r} が含まれている（様式第3 第5条関係 違反）",
            )

    for report in package.reports:
        if (
            "様式第5" in report.name
            and CHAIN_FRANCHISE_REQUIRED_LEGAL_ARTICLE not in report.name
        ):
            errors.append(
                f"連鎖化の様式第5 レポート {report.report_id!r} は "
                f"{CHAIN_FRANCHISE_REQUIRED_LEGAL_ARTICLE} を name に含む必要が"
                f"ある（現在: {report.name!r}）",
            )

    return errors


# モジュール load 時の sanity check — 連鎖化パッケージの違反は import を失敗させる
_chain_franchise_violations = validate_chain_franchise_constraints(
    _CHAIN_FRANCHISE_PACKAGE,
)
if _chain_franchise_violations:
    raise ValueError(
        "連鎖化パッケージの c.8 強制ガード違反:\n  - "
        + "\n  - ".join(_chain_franchise_violations),
    )


__all__ = [
    "ALL_PACKAGES",
    "CHAIN_FRANCHISE_FORBIDDEN_FORM3_SECTIONS",
    "CHAIN_FRANCHISE_FORBIDDEN_KPI_PREFIXES",
    "CHAIN_FRANCHISE_REQUIRED_LEGAL_ARTICLE",
    "CompanyPackageOverride",
    "IndustryPackage",
    "OverrideCategory",
    "OverrideEntry",
    "OverrideTargetKind",
    "StandardDataItemDef",
    "StandardKpiDef",
    "StandardMeetingDef",
    "StandardReportDef",
    "build_industry_package_summary",
    "get_package",
    "list_packages",
    "resolve_company_package",
    "validate_chain_franchise_constraints",
]
