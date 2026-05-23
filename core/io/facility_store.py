"""報告単位 Facility（施設マスタ）の永続化（outputs/facilities/<company_id>.json）。

様式第5 定期報告の Ⅳ セクション（荷待ち時間/荷役等時間の計測実績）で求められる
「測定対象施設・測定期間・把握条件・除外理由」を構造化して管理するレイヤ。

設計方針:
    - company_store.py / measure_run_store.py と同じ永続化 pattern
      （base_dir は実行時解決、LOGI_STORAGE_BACKEND=s3 で S3 にも複製）
    - 1 ファイル = 1 社の全施設リスト（list[Facility]）
    - 同一 facility_id は upsert（updated_at が更新される）
    - WaitTimeRow.site_name と Facility.site_name の連結で wait_time_heatmap を
      施設粒度でフィルタ可能にする（CompanyProfile を破壊変更しない）

寄託先施設（facility_control_type="consigned"）の公式出典:
    - 様式第5 IV-4: 貨物に係る寄託契約等を締結した者が管理する施設における
      寄託契約の締結先との連携状況等について
    - 様式第5 IV-5: 同施設における荷待ち時間等の状況に関する参考情報
    - 国交省「特定荷主の物流効率化法への対応の手引き」第1.1版（2026年4月）
      https://www.mlit.go.jp/seisakutokatsu/freight/content/001984872.pdf
    - 経産省「様式第5 定期報告書」
      https://www.meti.go.jp/policy/economy/distribution/250829_ninushi.pdf

公式定型語として確認できなかった用語（Codex 二次調査 2026-05-23）:
    - 「測定実施者」「責任主体」「自社直接計測外」「3-5-3」
      → アプリ内の説明文では使うが、公式 citation のラベル/必須文言としては扱わない

plan: plans/facility_store.md（Tier S3）
詳細レポート: docs/facility_citation_research.md（Codex 確定値 2026-05-23）
"""

from __future__ import annotations

import json
import os
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DEFAULT_FACILITIES_DIR = Path(os.environ.get("LOGI_OUTPUTS_DIR", "outputs")) / "facilities"

FacilityControlType = Literal["owned", "leased", "operated_by_3pl", "consigned"]
"""施設管理形態（責任境界）:

- "owned":          自社所有・自社運用
- "leased":         自社賃借・自社運用（賃借契約あり）
- "operated_by_3pl": 自社所有/賃借だが運用は 3PL に委託（自社測定可）
- "consigned":      寄託先（特定倉庫業者等）に管理を委ね、自社直接計測外
"""


# ---------------------------------------------------------------------------
# 型定義
# ---------------------------------------------------------------------------


class FacilityMeasurementPeriod(BaseModel):
    """測定期間（様式第5 Ⅳ で必須）。

    start_on <= end_on を強制。unit_label は集計粒度のラベル（"月次"/"四半期"/"年次" 等）で
    法令フォームには注記として転記される。
    """

    model_config = ConfigDict(frozen=True)

    start_on: date
    end_on: date
    unit_label: str = Field(
        ...,
        description="集計粒度ラベル（例: '月次', '四半期', '年次', '通期'）",
    )

    @field_validator("end_on")
    @classmethod
    def _end_after_start(cls, v: date, info) -> date:  # type: ignore[no-untyped-def]
        start = info.data.get("start_on")
        if start is not None and v < start:
            raise ValueError("end_on は start_on 以降である必要があります")
        return v


class Facility(BaseModel):
    """報告単位 1 施設。

    様式第5 Ⅳ の測定実績を施設ごとに紐付け、提出時に「どの施設の・いつの・
    どの条件の」測定値かを defensibility 担保レベルで残す。

    is_consigned_warehouse=True は寄託先（特定倉庫業者・物流子会社）を表す。
    寄託先は自社測定外であり、集計時には「自社測定外」バナー付きで表示する
    （Codex 二者議論で確定: plans/facility_store.md §8）。
    """

    model_config = ConfigDict(frozen=False)  # updated_at を内部で書き換えるため

    facility_id: str = Field(
        ...,
        min_length=1,
        pattern=r"^[A-Za-z0-9_\-]+$",
        description="施設 ID（英数字・アンダースコア・ハイフンのみ。例: 'fac_mfg01_tokyo_dc'）",
    )
    company_id: str = Field(..., min_length=1, description="所属する企業の company_id")
    name: str = Field(..., min_length=1, description="施設名（例: '東京流通センター'）")
    address: str = Field("", description="住所（任意精度。空文字許容）")
    prefecture: str = Field(..., min_length=1, description="都道府県名（正式名称）")
    industry_code: str = Field(
        ...,
        min_length=4,
        max_length=4,
        description="JSIC 4 桁（施設単位で別業種となる場合に備える）",
    )
    site_name: str | None = Field(
        default=None,
        description=(
            "CompanyProfile.sites[].name および WaitTimeRow.site_name の連結キー。"
            "wait_time_heatmap を施設単位でフィルタする際に使用する。"
        ),
    )
    measurement_period: FacilityMeasurementPeriod = Field(
        ...,
        description="測定期間（start_on / end_on / unit_label）",
    )
    measurement_conditions: list[str] = Field(
        default_factory=list,
        description=(
            "把握条件（例: 'ドライバー手動計測', 'パレット便のみ対象', "
            "'バース予約システム連携'）"
        ),
    )
    exclusion_reasons: list[str] = Field(
        default_factory=list,
        description=(
            "除外理由（例: '2025-04 改修工事中', '夜間便は対象外', "
            "'1 ヶ月未満の試験運用は除外'）"
        ),
    )
    is_consigned_warehouse: bool = Field(
        False,
        description=(
            "寄託先（特定倉庫業者・物流子会社）か。True なら自社測定外として "
            "wait_time_heatmap 上でバナー表示し、責任主体を明示する。"
            "facility_control_type='consigned' と等価で、後方互換のため両方残す。"
        ),
    )
    facility_control_type: FacilityControlType | None = Field(
        default=None,
        description=(
            "施設管理形態（責任境界）。owned/leased/operated_by_3pl/consigned。"
            "未指定なら is_consigned_warehouse から逆算（True→consigned, False→owned）。"
            "Codex 二者議論で追加（plans/facility_store.md §8.4）。"
        ),
    )
    measurement_source: str | None = Field(
        default=None,
        description=(
            "測定主体名（例: '自社ドライバー手動', '寄託先WMS自動連携', '3PL報告書'）。"
            "様式第5 Ⅳ で「誰が計測したか」を明示するための補助項目。"
        ),
    )
    consigned_partner_name: str | None = Field(
        default=None,
        description=(
            "寄託契約相手の事業者名（facility_control_type='consigned' のとき必須的）。"
            "標準ディスクレーマー文言の差込にも使う。"
        ),
    )
    contract_scope_note: str | None = Field(
        default=None,
        description=(
            "寄託契約のスコープ注記（例: 'パレット便のみ寄託・バラ便は自社運用'）。"
            "様式第5 で連携状況・把握範囲を説明する根拠として使う。"
        ),
    )
    notes: str | None = Field(default=None, description="補足（個別事情）")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def _sync_control_type_and_consigned_flag(self) -> Facility:
        """facility_control_type と is_consigned_warehouse を同期する。

        後方互換ルール:
            1. facility_control_type が None なら is_consigned_warehouse から逆算
               （True→'consigned', False→'owned'）
            2. facility_control_type が指定済なら is_consigned_warehouse を上書き
               （control_type='consigned' ⇒ is_consigned_warehouse=True）
            3. 既存 JSON（facility_control_type フィールドなし）も model_validate で
               自動的に正しい値に同期される（マイグレーション）
        """
        if self.facility_control_type is None:
            self.facility_control_type = (
                "consigned" if self.is_consigned_warehouse else "owned"
            )
        else:
            # control_type が指定済 → is_consigned_warehouse を制御値に揃える
            self.is_consigned_warehouse = self.facility_control_type == "consigned"
        return self

    @property
    def is_consigned_for_aggregation(self) -> bool:
        """全社集計時に寄託先として扱うべきか。

        facility_control_type='consigned' または旧 is_consigned_warehouse=True なら True。
        集計分離（include_consigned 引数）の判定に使う。
        """
        return (
            self.facility_control_type == "consigned" or self.is_consigned_warehouse
        )


# ---------------------------------------------------------------------------
# 永続化ヘルパー
# ---------------------------------------------------------------------------


def _resolve_facilities_dir(base_dir: Path | None) -> Path:
    """base_dir が None なら**実行時に** LOGI_OUTPUTS_DIR を再評価する。

    デフォルト引数は関数定義時にバインドされるため、テストや実行時に
    LOGI_OUTPUTS_DIR を差し替えても反映されない。None sentinel で実行時解決。
    """
    if base_dir is not None:
        return base_dir
    return Path(os.environ.get("LOGI_OUTPUTS_DIR", "outputs")) / "facilities"


def _facilities_path(company_id: str, base_dir: Path) -> Path:
    return base_dir / f"{company_id}.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def default_consigned_disclaimer(partner_name: str | None = None) -> str:
    """寄託先施設の標準ディスクレーマー文言を返す。

    様式第5 Ⅳ で「寄託先提供値」を扱う際の防御的注記。Codex 二者議論 §8.4-3
    で確定した推奨文言（plans/facility_store.md）。

    Codex 二次調査（2026-05-23）の注記:
        本文言はアプリ側の説明文であり、様式第5 の「公式必須文言」として
        登録されたものではない。「自社直接計測外」は公式定型語ではないが、
        様式第5 IV-4/IV-5 の「参考情報」の意図と整合する説明文として使う。
        詳細は docs/facility_citation_research.md を参照。

    Args:
        partner_name: 寄託契約相手の事業者名。None なら "寄託先" と汎用表記。

    Returns:
        "{partner}から提供を受けた参考値。計測期間・対象運行・計測方法は
        寄託先記録に基づく（自社直接計測外）。"
    """
    partner_label = partner_name if partner_name else "寄託先"
    return (
        f"{partner_label}から提供を受けた参考値。計測期間・対象運行・"
        "計測方法は寄託先記録に基づく（自社直接計測外）。"
    )


def save_facilities(
    company_id: str,
    facilities: list[Facility],
    base_dir: Path | None = None,
) -> Path:
    """指定企業の施設リストを JSON ファイルに上書き保存する。

    既存ファイルを完全に置き換える。upsert したい場合は upsert_facility を使う。
    """
    resolved = _resolve_facilities_dir(base_dir)
    resolved.mkdir(parents=True, exist_ok=True)
    path = _facilities_path(company_id, resolved)
    payload = [f.model_dump(mode="json") for f in facilities]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _maybe_publish_to_s3(path)
    return path


def load_facilities(
    company_id: str,
    base_dir: Path | None = None,
) -> list[Facility]:
    """指定企業の施設一覧を返す。ファイルが存在しない場合は空リスト。"""
    s3_data = _maybe_fetch_from_s3(company_id)
    if s3_data is not None:
        return _parse_facilities(s3_data)

    resolved = _resolve_facilities_dir(base_dir)
    path = _facilities_path(company_id, resolved)
    if not path.is_file():
        return []
    return _parse_facilities(path.read_text(encoding="utf-8"))


def load_facility(
    facility_id: str,
    company_id: str,
    base_dir: Path | None = None,
) -> Facility | None:
    """単一施設をロードする。見つからなければ None。

    company_id とのペアで検索する（facility_id だけだと社横断スキャンが必要になり、
    S3 backend で非効率になるため意図的に required）。
    """
    facilities = load_facilities(company_id, base_dir)
    for f in facilities:
        if f.facility_id == facility_id:
            return f
    return None


def upsert_facility(
    facility: Facility,
    base_dir: Path | None = None,
) -> Path:
    """施設マスタを upsert する。同一 facility_id があれば updated_at を更新して上書き。

    寄託先施設（is_consigned_for_aggregation=True）かつ measurement_conditions が
    空の場合、default_consigned_disclaimer() を自動付与する（Codex §8.4-3 反映）。
    """
    existing = load_facilities(facility.company_id, base_dir)
    now = datetime.now(UTC)

    # Codex §8.4-3: 寄託先施設で計測条件未入力なら標準文言を自動付与
    incoming = facility
    if incoming.is_consigned_for_aggregation and not incoming.measurement_conditions:
        disclaimer = default_consigned_disclaimer(incoming.consigned_partner_name)
        incoming = incoming.model_copy(update={"measurement_conditions": [disclaimer]})

    # 既存検索
    found_idx: int | None = None
    for idx, f in enumerate(existing):
        if f.facility_id == incoming.facility_id:
            found_idx = idx
            break

    if found_idx is None:
        # 新規追加。created_at は incoming のものを尊重、未指定なら now
        new_record = incoming.model_copy(update={"updated_at": now})
        existing.append(new_record)
    else:
        # 上書き。created_at は既存を尊重、updated_at は now
        prior = existing[found_idx]
        new_record = incoming.model_copy(
            update={"created_at": prior.created_at, "updated_at": now}
        )
        existing[found_idx] = new_record

    return save_facilities(incoming.company_id, existing, base_dir)


# ---------------------------------------------------------------------------
# 内部関数
# ---------------------------------------------------------------------------


def _parse_facilities(raw: str) -> list[Facility]:
    data = json.loads(raw)
    return [Facility.model_validate(item) for item in data]


def _maybe_publish_to_s3(path: Path) -> None:
    """S3 backend 利用時はローカル書出後に複製。それ以外は no-op。"""
    if os.environ.get("LOGI_STORAGE_BACKEND", "local").lower() != "s3":
        return
    import contextlib

    from core.storage import get_storage

    with contextlib.suppress(Exception):
        get_storage().publish(path)


def _maybe_fetch_from_s3(company_id: str) -> str | None:
    """S3 backend 利用時は facilities/<company_id>.json を S3 から取得。"""
    if os.environ.get("LOGI_STORAGE_BACKEND", "local").lower() != "s3":
        return None
    from core.storage import get_storage

    storage = get_storage()
    data = storage.read_bytes(f"facilities/{company_id}.json")
    return data.decode("utf-8") if data is not None else None


__all__ = [
    "DEFAULT_FACILITIES_DIR",
    "Facility",
    "FacilityControlType",
    "FacilityMeasurementPeriod",
    "default_consigned_disclaimer",
    "load_facilities",
    "load_facility",
    "save_facilities",
    "upsert_facility",
]
