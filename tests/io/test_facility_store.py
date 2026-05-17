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
