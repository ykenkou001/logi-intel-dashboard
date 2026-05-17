"""core/io/facility_store.py の単体テスト（Tier S3）。

カバレッジ:
    1. save/load round-trip — 保存した施設が完全に復元できる
    2. 未登録 company_id は空リストを返す
    3. load_facility — 単一施設の取得（存在）
    4. load_facility — 単一施設の取得（不在）
    5. upsert_facility — 新規追加
    6. upsert_facility — 同一 facility_id の上書き + updated_at 更新
    7. upsert_facility — created_at は既存値を保持
    8. 別 company_id のファイル分離（混在しない）
    9. measurement_period の妥当性（end_on < start_on は ValueError）
    10. facility_id の文字種チェック（日本語混入で ValidationError）
    11. base_dir 実行時解決（DEFAULT を汚染しない）
    12. JSON 直接編集に対する model_validate（前方互換）

Tier S3 フォロー PR（Codex §8.4 反映）:
    13. facility_control_type 未指定で is_consigned=True → 'consigned' に同期
    14. facility_control_type 未指定で is_consigned=False → 'owned' に同期
    15. facility_control_type='consigned' → is_consigned_warehouse=True に同期
    16. 既存 JSON（control_type フィールドなし）の前方互換マイグレーション
    17. default_consigned_disclaimer — 標準文言（partner 名あり/なし）
    18. upsert_facility — 寄託先 + conditions 空で自動付与
    19. upsert_facility — 寄託先 + conditions 入力済では自動付与しない
    20. is_consigned_for_aggregation プロパティの判定
"""

from __future__ import annotations

import json
import time
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from core.io.facility_store import (
    Facility,
    FacilityMeasurementPeriod,
    default_consigned_disclaimer,
    load_facilities,
    load_facility,
    save_facilities,
    upsert_facility,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_facility(
    *,
    facility_id: str = "fac_tokyo_dc",
    company_id: str = "sample_retail_01",
    name: str = "東京流通センター",
    site_name: str | None = "関東地域DC",
    is_consigned_warehouse: bool = False,
) -> Facility:
    return Facility(
        facility_id=facility_id,
        company_id=company_id,
        name=name,
        address="東京都江東区豊洲 1-1-1",
        prefecture="東京都",
        industry_code="5411",
        site_name=site_name,
        measurement_period=FacilityMeasurementPeriod(
            start_on=date(2025, 4, 1),
            end_on=date(2026, 3, 31),
            unit_label="月次",
        ),
        measurement_conditions=["ドライバー手動計測", "パレット便のみ対象"],
        exclusion_reasons=["2025-08 改修工事中"],
        is_consigned_warehouse=is_consigned_warehouse,
        notes=None,
    )


# ---------------------------------------------------------------------------
# 1. save/load round-trip
# ---------------------------------------------------------------------------


def test_save_load_round_trip(tmp_path: Path) -> None:
    facility = _make_facility()
    save_facilities("sample_retail_01", [facility], base_dir=tmp_path)
    loaded = load_facilities("sample_retail_01", base_dir=tmp_path)

    assert len(loaded) == 1
    assert loaded[0].facility_id == facility.facility_id
    assert loaded[0].name == facility.name
    assert loaded[0].site_name == "関東地域DC"
    assert loaded[0].measurement_period.start_on == date(2025, 4, 1)
    assert loaded[0].measurement_period.unit_label == "月次"
    assert loaded[0].measurement_conditions == ["ドライバー手動計測", "パレット便のみ対象"]


# ---------------------------------------------------------------------------
# 2. 未登録 company_id は空リスト
# ---------------------------------------------------------------------------


def test_load_returns_empty_when_no_file(tmp_path: Path) -> None:
    assert load_facilities("never_registered", base_dir=tmp_path) == []


# ---------------------------------------------------------------------------
# 3. load_facility — 存在する施設
# ---------------------------------------------------------------------------


def test_load_facility_finds_existing(tmp_path: Path) -> None:
    f1 = _make_facility(facility_id="fac_a", name="施設A")
    f2 = _make_facility(facility_id="fac_b", name="施設B", site_name="中部地域DC")
    save_facilities("sample_retail_01", [f1, f2], base_dir=tmp_path)

    got = load_facility("fac_b", company_id="sample_retail_01", base_dir=tmp_path)
    assert got is not None
    assert got.name == "施設B"
    assert got.site_name == "中部地域DC"


# ---------------------------------------------------------------------------
# 4. load_facility — 不在
# ---------------------------------------------------------------------------


def test_load_facility_returns_none_when_missing(tmp_path: Path) -> None:
    save_facilities("sample_retail_01", [_make_facility()], base_dir=tmp_path)
    assert (
        load_facility("nope", company_id="sample_retail_01", base_dir=tmp_path)
        is None
    )


# ---------------------------------------------------------------------------
# 5. upsert_facility — 新規追加
# ---------------------------------------------------------------------------


def test_upsert_facility_inserts_new(tmp_path: Path) -> None:
    f = _make_facility(facility_id="fac_new")
    upsert_facility(f, base_dir=tmp_path)
    loaded = load_facilities("sample_retail_01", base_dir=tmp_path)
    assert len(loaded) == 1
    assert loaded[0].facility_id == "fac_new"


# ---------------------------------------------------------------------------
# 6. upsert_facility — 同一 facility_id の上書き + updated_at 更新
# ---------------------------------------------------------------------------


def test_upsert_facility_updates_existing(tmp_path: Path) -> None:
    f1 = _make_facility(facility_id="fac_same", name="旧名")
    upsert_facility(f1, base_dir=tmp_path)
    first_loaded = load_facility("fac_same", "sample_retail_01", base_dir=tmp_path)
    assert first_loaded is not None
    initial_updated = first_loaded.updated_at

    # 1 ミリ秒以上の差を確実につける（OS の時刻解像度依存を避ける）
    time.sleep(0.01)

    f2 = _make_facility(facility_id="fac_same", name="新名")
    upsert_facility(f2, base_dir=tmp_path)
    second_loaded = load_facility("fac_same", "sample_retail_01", base_dir=tmp_path)
    assert second_loaded is not None
    assert second_loaded.name == "新名"
    assert second_loaded.updated_at > initial_updated


# ---------------------------------------------------------------------------
# 7. upsert_facility — created_at は既存値を保持
# ---------------------------------------------------------------------------


def test_upsert_facility_preserves_created_at(tmp_path: Path) -> None:
    original_created = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
    f = _make_facility(facility_id="fac_keep")
    f_with_old = f.model_copy(update={"created_at": original_created})
    upsert_facility(f_with_old, base_dir=tmp_path)

    # 別の更新を入れる
    f2 = _make_facility(facility_id="fac_keep", name="改名")
    upsert_facility(f2, base_dir=tmp_path)

    loaded = load_facility("fac_keep", "sample_retail_01", base_dir=tmp_path)
    assert loaded is not None
    assert loaded.created_at == original_created
    assert loaded.name == "改名"


# ---------------------------------------------------------------------------
# 8. 別 company_id のファイル分離
# ---------------------------------------------------------------------------


def test_company_ids_are_isolated(tmp_path: Path) -> None:
    f_a = _make_facility(facility_id="fac_a", company_id="company_a")
    f_b = _make_facility(facility_id="fac_b", company_id="company_b")
    save_facilities("company_a", [f_a], base_dir=tmp_path)
    save_facilities("company_b", [f_b], base_dir=tmp_path)

    loaded_a = load_facilities("company_a", base_dir=tmp_path)
    loaded_b = load_facilities("company_b", base_dir=tmp_path)
    assert len(loaded_a) == 1 and loaded_a[0].facility_id == "fac_a"
    assert len(loaded_b) == 1 and loaded_b[0].facility_id == "fac_b"


# ---------------------------------------------------------------------------
# 9. measurement_period の妥当性（end_on < start_on は ValidationError）
# ---------------------------------------------------------------------------


def test_measurement_period_rejects_inverted_dates() -> None:
    with pytest.raises(ValidationError):
        FacilityMeasurementPeriod(
            start_on=date(2026, 3, 31),
            end_on=date(2025, 4, 1),
            unit_label="月次",
        )


# ---------------------------------------------------------------------------
# 10. facility_id の文字種チェック
# ---------------------------------------------------------------------------


def test_facility_id_rejects_japanese() -> None:
    with pytest.raises(ValidationError):
        _make_facility(facility_id="施設_A")


# ---------------------------------------------------------------------------
# 11. base_dir 実行時解決（LOGI_OUTPUTS_DIR の monkeypatch で切替できる）
# ---------------------------------------------------------------------------


def test_base_dir_resolved_at_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    custom = tmp_path / "custom_outputs"
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(custom))
    save_facilities("env_company", [_make_facility(company_id="env_company")])

    # 環境変数経由のパス配下にファイルが生成されている
    assert (custom / "facilities" / "env_company.json").is_file()
    loaded = load_facilities("env_company")
    assert len(loaded) == 1


# ---------------------------------------------------------------------------
# 12. JSON 直接編集後の model_validate（前方互換 / 未知フィールド許容）
# ---------------------------------------------------------------------------


def test_load_ignores_unknown_field_in_json(tmp_path: Path) -> None:
    """将来追加されたフィールドが入った JSON も既存バージョンで読める。"""
    facility = _make_facility()
    save_facilities("sample_retail_01", [facility], base_dir=tmp_path)
    path = tmp_path / "sample_retail_01.json"

    raw = json.loads(path.read_text(encoding="utf-8"))
    raw[0]["future_field_for_v2"] = "some_value"
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")

    loaded = load_facilities("sample_retail_01", base_dir=tmp_path)
    assert len(loaded) == 1
    assert loaded[0].facility_id == facility.facility_id


# ---------------------------------------------------------------------------
# 13-20. Tier S3 フォロー PR — Codex §8.4 反映の拡張テスト
# ---------------------------------------------------------------------------


def test_control_type_defaults_to_consigned_when_is_consigned_true() -> None:
    """facility_control_type 未指定で is_consigned_warehouse=True → 'consigned' に同期。"""
    f = _make_facility(is_consigned_warehouse=True)
    assert f.facility_control_type == "consigned"
    assert f.is_consigned_warehouse is True
    assert f.is_consigned_for_aggregation is True


def test_control_type_defaults_to_owned_when_is_consigned_false() -> None:
    """facility_control_type 未指定で is_consigned_warehouse=False → 'owned' に同期。"""
    f = _make_facility(is_consigned_warehouse=False)
    assert f.facility_control_type == "owned"
    assert f.is_consigned_warehouse is False
    assert f.is_consigned_for_aggregation is False


def test_control_type_consigned_forces_is_consigned_flag() -> None:
    """facility_control_type='consigned' 指定で is_consigned_warehouse=True に同期。"""
    f = Facility(
        facility_id="fac_sync",
        company_id="sample_retail_01",
        name="同期検証施設",
        prefecture="東京都",
        industry_code="5411",
        site_name="関東地域DC",
        facility_control_type="consigned",
        is_consigned_warehouse=False,  # 矛盾を入力 → control_type 側に揃う
        measurement_period=FacilityMeasurementPeriod(
            start_on=date(2025, 4, 1),
            end_on=date(2026, 3, 31),
            unit_label="月次",
        ),
        measurement_conditions=["test"],
    )
    assert f.is_consigned_warehouse is True
    assert f.facility_control_type == "consigned"


def test_legacy_json_without_control_type_is_migrated(tmp_path: Path) -> None:
    """既存 JSON（facility_control_type フィールドなし）も読み込み時に同期される。"""
    # フィールドなしの JSON を直書きする
    raw_payload = [
        {
            "facility_id": "legacy_fac",
            "company_id": "legacy_co",
            "name": "旧形式施設",
            "address": "",
            "prefecture": "東京都",
            "industry_code": "5411",
            "site_name": "関東",
            "measurement_period": {
                "start_on": "2025-04-01",
                "end_on": "2026-03-31",
                "unit_label": "月次",
            },
            "measurement_conditions": ["legacy"],
            "exclusion_reasons": [],
            "is_consigned_warehouse": True,
            "notes": None,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
            # facility_control_type / measurement_source 等は欠落
        },
    ]
    path = tmp_path / "legacy_co.json"
    path.write_text(json.dumps(raw_payload, ensure_ascii=False), encoding="utf-8")

    loaded = load_facilities("legacy_co", base_dir=tmp_path)
    assert len(loaded) == 1
    assert loaded[0].facility_control_type == "consigned"
    assert loaded[0].is_consigned_warehouse is True


def test_default_consigned_disclaimer_with_partner_name() -> None:
    """partner_name 指定で文言が差し込まれる。"""
    text = default_consigned_disclaimer("○○倉庫株式会社")
    assert "○○倉庫株式会社から提供を受けた参考値" in text
    assert "自社直接計測外" in text


def test_default_consigned_disclaimer_without_partner_name() -> None:
    """partner_name 省略時は汎用 '寄託先' 表記。"""
    text = default_consigned_disclaimer()
    assert "寄託先から提供を受けた参考値" in text
    assert "自社直接計測外" in text


def test_upsert_facility_auto_injects_disclaimer_for_empty_conditions(
    tmp_path: Path,
) -> None:
    """寄託先 + measurement_conditions 空 → default_consigned_disclaimer が自動付与。"""
    f = Facility(
        facility_id="fac_consigned_blank",
        company_id="sample_retail_01",
        name="寄託先DC（条件未入力）",
        prefecture="東京都",
        industry_code="5411",
        site_name="関東地域DC",
        is_consigned_warehouse=True,
        consigned_partner_name="○○物流",
        measurement_period=FacilityMeasurementPeriod(
            start_on=date(2025, 4, 1),
            end_on=date(2026, 3, 31),
            unit_label="月次",
        ),
        measurement_conditions=[],
        exclusion_reasons=[],
    )
    upsert_facility(f, base_dir=tmp_path)
    loaded = load_facility(
        "fac_consigned_blank", "sample_retail_01", base_dir=tmp_path
    )
    assert loaded is not None
    assert len(loaded.measurement_conditions) == 1
    assert "○○物流から提供を受けた参考値" in loaded.measurement_conditions[0]


def test_upsert_facility_skips_disclaimer_when_conditions_filled(
    tmp_path: Path,
) -> None:
    """寄託先 + measurement_conditions 入力済 → 自動付与しない（ユーザー入力を尊重）。"""
    f = _make_facility(
        facility_id="fac_consigned_filled",
        is_consigned_warehouse=True,
    )
    # _make_facility は measurement_conditions に値を入れている
    upsert_facility(f, base_dir=tmp_path)
    loaded = load_facility(
        "fac_consigned_filled", "sample_retail_01", base_dir=tmp_path
    )
    assert loaded is not None
    assert loaded.measurement_conditions == ["ドライバー手動計測", "パレット便のみ対象"]
