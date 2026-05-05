"""自社プロフィール入力テンプレ Excel 生成のテスト。

フェーズ4.5 B 軸で **用途別 3 種類**（daily / monthly / annual）に拡張。
annual は現行互換のため引数なし呼び出しでも 6 シートが揃うことを担保する。
"""
from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import load_workbook

from core.io.company_loader import load_company_profile_from_excel
from core.io.template_writer import write_company_template


def test_template_creates_all_sheets(tmp_path: Path) -> None:
    """テンプレ生成（既定=annual）で 6 シートすべてが作られる。"""
    out = write_company_template(tmp_path / "template.xlsx")
    assert out.is_file()

    wb = load_workbook(out, read_only=True)
    expected = {
        "profile",
        "sites",
        "wait_time",
        "handling_time",
        "kpi_history",
        "_jsic_reference",
    }
    assert set(wb.sheetnames) == expected


def test_profile_sheet_has_required_keys(tmp_path: Path) -> None:
    """profile シートに必須項目（company_id / jsic_code / annual_revenue_jpy）が含まれる。"""
    out = write_company_template(tmp_path / "template.xlsx")
    wb = load_workbook(out, read_only=True)
    ws = wb["profile"]
    keys = [row[0].value for row in ws.iter_rows() if row[0].value]
    must_have = (
        "company_id",
        "jsic_code",
        "annual_revenue_jpy",
        "annual_freight_tons_total",
        "operating_profit_jpy",
        "cost_of_goods_sold_jpy",
        "is_chain_franchise",
        "clo_name",
        "plan_period_start_fy",
        "plan_period_end_fy",
    )
    for key in must_have:
        assert any(
            isinstance(k, str) and k.startswith(key) for k in keys
        ), f"profile シートに {key} が存在しない（取得 keys: {keys}）"


def test_tabular_sheets_have_header_and_sample_rows(tmp_path: Path) -> None:
    """sites/wait_time/handling_time/kpi_history はヘッダ + 説明 + サンプル行を持つ。"""
    out = write_company_template(tmp_path / "template.xlsx")
    wb = load_workbook(out, read_only=True)
    for sheet_name in ("sites", "wait_time", "handling_time", "kpi_history"):
        ws = wb[sheet_name]
        # 1 行目: ヘッダ（少なくとも 4 列）
        header = [c.value for c in ws[1]]
        assert any(v for v in header), f"{sheet_name} ヘッダ行が空"
        assert len(header) >= 4

        # 3 行目: サンプル行（少なくとも 1 行）
        sample = [c.value for c in ws[3]]
        assert any(v is not None for v in sample), f"{sheet_name} サンプル行が空"


def test_jsic_reference_has_known_codes(tmp_path: Path) -> None:
    """_jsic_reference に主要業種コードが含まれる。"""
    out = write_company_template(tmp_path / "template.xlsx")
    wb = load_workbook(out, read_only=True)
    ws = wb["_jsic_reference"]
    codes = [
        ws.cell(row=row_idx, column=1).value
        for row_idx in range(2, 10)
    ]
    # サンプル3社で使っている業種が含まれる
    assert "3159" in codes  # 製造業
    assert "5514" in codes  # 卸売業
    assert "5891" in codes  # 連鎖化


# ─── フェーズ4.5 B: 用途別テンプレ ─────────────────────────────────


def test_default_purpose_is_annual_and_backwards_compatible(tmp_path: Path) -> None:
    """purpose 未指定 = 'annual' = 現行互換（6 シート）。"""
    default_out = write_company_template(tmp_path / "default.xlsx")
    annual_out = write_company_template(tmp_path / "annual.xlsx", purpose="annual")
    default_sheets = set(load_workbook(default_out, read_only=True).sheetnames)
    annual_sheets = set(load_workbook(annual_out, read_only=True).sheetnames)
    assert default_sheets == annual_sheets
    assert default_sheets == {
        "profile",
        "sites",
        "wait_time",
        "handling_time",
        "kpi_history",
        "_jsic_reference",
    }


def test_monthly_purpose_keeps_kpi_and_handling(tmp_path: Path) -> None:
    """monthly は wait_time(月集計) + handling_time + kpi_history を残す。"""
    out = write_company_template(tmp_path / "monthly.xlsx", purpose="monthly")
    wb = load_workbook(out, read_only=True)
    assert set(wb.sheetnames) == {
        "profile",
        "sites",
        "wait_time",
        "handling_time",
        "kpi_history",
        "_jsic_reference",
    }
    # bucket_label が月次集計形式（「YYYY-MM ...」）になっている
    ws = wb["wait_time"]
    sample_label = ws.cell(row=3, column=1).value
    assert isinstance(sample_label, str)
    assert sample_label.startswith("2026-")
    assert "-" in sample_label.split()[0]  # YYYY-MM 形式


def test_daily_purpose_only_has_wait_time(tmp_path: Path) -> None:
    """daily は wait_time のみの軽量版（handling_time / kpi_history を含めない）。"""
    out = write_company_template(tmp_path / "daily.xlsx", purpose="daily")
    wb = load_workbook(out, read_only=True)
    sheets = set(wb.sheetnames)
    assert sheets == {"profile", "sites", "wait_time", "_jsic_reference"}
    assert "handling_time" not in sheets
    assert "kpi_history" not in sheets


def test_daily_wait_time_includes_site_and_slot_columns(tmp_path: Path) -> None:
    """daily の wait_time は site_name と time_slot 列を含み、サンプル行で埋まっている。"""
    out = write_company_template(tmp_path / "daily.xlsx", purpose="daily")
    wb = load_workbook(out, read_only=True)
    ws = wb["wait_time"]
    headers = [str(c.value or "") for c in ws[1]]
    assert any(h.startswith("site_name") for h in headers)
    assert any(h.startswith("time_slot") for h in headers)

    # サンプル 1 行目: 日付ラベル + site_name + time_slot が埋まっている
    row3 = [c.value for c in ws[3]]
    bucket_label = row3[0]
    assert isinstance(bucket_label, str)
    # 「YYYY-MM-DD 朝便」のような形式（- が 2 つ含まれる）
    assert bucket_label.count("-") >= 2
    # site_name 列・time_slot 列にサンプル値
    site_col = next(i for i, h in enumerate(headers) if h.startswith("site_name"))
    slot_col = next(i for i, h in enumerate(headers) if h.startswith("time_slot"))
    assert isinstance(row3[site_col], str) and row3[site_col]
    assert row3[slot_col] in {"morning", "midday", "evening", "night"}


@pytest.mark.parametrize("purpose", ["daily", "monthly", "annual"])
def test_each_purpose_roundtrips_through_loader(tmp_path: Path, purpose: str) -> None:
    """各用途のサンプル付きテンプレが、そのまま既存ローダーで取込めることを保証する。

    シート/列構成が変わっても CompanyProfile に組み立てられないと意味がない。
    daily の wait_time に追加した site_name/time_slot も含めて検証する。
    """
    out = write_company_template(tmp_path / f"{purpose}.xlsx", purpose=purpose)  # type: ignore[arg-type]
    profile = load_company_profile_from_excel(out)

    # サンプル profile 行が読めて、必須項目が埋まる
    assert profile.company_id
    assert profile.name
    assert profile.jsic_code and len(profile.jsic_code) == 4
    assert len(profile.sites) >= 1
    # wait_time は全用途でサンプル行が入っている
    assert len(profile.wait_time_rows) >= 1

    if purpose == "daily":
        # daily は site_name / time_slot がサンプルで埋まる
        assert any(
            r.site_name and r.time_slot is not None for r in profile.wait_time_rows
        )
        # daily は handling/kpi は空
        assert profile.handling_time_rows == []
        assert profile.kpi_history == []
    else:
        # monthly / annual は handling/kpi のサンプル行も組み立てられる
        assert len(profile.handling_time_rows) >= 1
        assert len(profile.kpi_history) >= 1


def test_invalid_purpose_raises(tmp_path: Path) -> None:
    """不正な purpose は ValueError。"""
    with pytest.raises(ValueError, match="purpose"):
        write_company_template(tmp_path / "bad.xlsx", purpose="weekly")  # type: ignore[arg-type]
