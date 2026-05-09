"""自社プロフィール入力 Excel テンプレートの生成（フェーズ4.0「実データ入力フォーム」）。

CLO 担当者が DL → 自社情報を記入 → Excel ローダーで取込、というフローの起点。

フェーズ4.5 B 軸で **用途別 3 種類** のテンプレに分割した:

- ``annual``  : 計画策定用（現行 6 シート完全互換、年 1 回更新の網羅版・既定）
- ``monthly`` : 月次集計用（KPI 中心・月次レビュー向け、handling/kpi_history を残す）
- ``daily``   : 日次運用入力用（wait_time のみ・site×日付×slot の軽量版）

いずれの用途も同じローダー（``core/io/company_loader``）で取込可能で、
スキーマ（``CompanyProfile`` / ``WaitTimeRow`` 等）は共通。違いは

- 含めるシート（daily は handling/kpi_history を省略）
- ``wait_time.bucket_label`` のサンプル値（daily は日付＋時間帯、monthly は月集計）
- daily のみ ``site_name`` / ``time_slot`` 列を埋めた状態で配布

annual は既定値のため、引数を渡さない既存呼び出しの挙動は完全互換。

各シートのフォーマット:
    1 行目: 列ヘッダ（必須は [必須]、任意は [任意]）
    2 行目: 各列の説明
    3 行目以降: サンプル記入値（薄いグレーで参考）
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

TemplatePurpose = Literal["daily", "monthly", "annual"]
"""テンプレートの利用用途:
- ``daily``   : 日次運用入力（wait_time のみの軽量版・site×日付×slot）
- ``monthly`` : 月次集計（wait_time は月集計ラベル、handling_time / kpi_history を残す）
- ``annual``  : 計画策定（現行 6 シート互換、年 1 回更新の網羅版）— **既定**
"""

VALID_PURPOSES: tuple[TemplatePurpose, ...] = ("daily", "monthly", "annual")

DEFAULT_TEMPLATE_PATH = (
    Path(os.environ.get("LOGI_OUTPUTS_DIR", "outputs"))
    / "templates"
    / "sample_company_template.xlsx"
)

# 視覚スタイル
_HEADER_FONT = Font(bold=True, color="FFFFFF")
_HEADER_FILL = PatternFill("solid", fgColor="2F5496")  # ロイヤルブルー
_DESCRIPTION_FONT = Font(italic=True, color="595959", size=10)
_DESCRIPTION_FILL = PatternFill("solid", fgColor="F2F2F2")  # 薄グレー
_SAMPLE_FONT = Font(color="A6A6A6")  # 薄グレー（サンプル値であることを示す）


def write_company_template(
    path: Path = DEFAULT_TEMPLATE_PATH,
    *,
    purpose: TemplatePurpose = "annual",
) -> Path:
    """自社プロフィール入力テンプレ Excel を書き出す。

    Args:
        path: 出力先パス（親ディレクトリは自動作成）
        purpose: 利用用途。``annual`` は現行 6 シート互換（既定）、
            ``monthly`` は wait_time を月集計ラベルにした KPI 中心構成、
            ``daily`` は wait_time のみの軽量構成（site×日付×slot）。

    Returns:
        書き出したファイルのパス

    Raises:
        ValueError: ``purpose`` が ``daily`` / ``monthly`` / ``annual`` 以外の場合
    """
    if purpose not in VALID_PURPOSES:
        raise ValueError(
            f"purpose は {list(VALID_PURPOSES)} のいずれかを指定してください: '{purpose}'"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()

    # デフォルトシート削除（Workbook 初期化時の "Sheet"）
    default = wb.active
    if default is not None:
        wb.remove(default)

    # profile / sites / _jsic_reference は全用途共通
    _build_profile_sheet(wb)
    _build_sites_sheet(wb)

    if purpose == "daily":
        # 日次運用: wait_time のみ（site×日付×slot の軽量版）
        _build_wait_time_daily_sheet(wb)
    elif purpose == "monthly":
        # 月次集計: wait_time(月集計) + handling_time + kpi_history
        _build_wait_time_monthly_sheet(wb)
        _build_handling_time_sheet(wb)
        _build_kpi_history_sheet(wb)
    else:  # annual（既定・現行互換）
        _build_wait_time_sheet(wb)
        _build_handling_time_sheet(wb)
        _build_kpi_history_sheet(wb)

    _build_jsic_reference_sheet(wb)

    wb.save(path)
    return path


# --- 各シートビルダー -----------------------------------------------------


def _build_profile_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("profile")
    columns: list[tuple[str, str, str | int | float | bool]] = [
        (
            "company_id [必須]",
            "内部ID（英数字とアンダースコア・ファイル名にも使用）",
            "logi_shoji_01",
        ),
        ("name [必須]", "会社名（漢字可）", "ロジ商事株式会社"),
        ("jsic_code [必須]", "JSIC 細分類4桁（_jsic_reference シート参照）", "5514"),
        ("main_business [必須]", "主たる事業の名称", "産業機械卸売業"),
        ("annual_revenue_jpy [必須]", "年間売上（円・整数）", 50_000_000_000),
        (
            "annual_freight_tons_total [必須]",
            "年間取扱貨物量 合計（トン）— 9万トン判定用",
            150_000.0,
        ),
        ("operating_profit_jpy [必須]", "年間営業利益（円）", 1_500_000_000),
        ("cost_of_goods_sold_jpy [必須]", "年間売上原価（円）", 42_000_000_000),
        ("is_chain_franchise [必須]", "連鎖化事業者か（TRUE / FALSE）", False),
        ("fleet_count_owned [任意]", "自社保有車両数（整数・未指定なら 0）", 5),
        ("fleet_count_outsourced [任意]", "委託車両数（整数・未指定なら 0）", 200),
        ("clo_name [必須]", "CLO の役職・氏名", "専務執行役員 鈴木 太郎"),
        ("plan_period_start_fy [必須]", "計画期間 開始年度（西暦・例 2026）", 2026),
        ("plan_period_end_fy [必須]", "計画期間 終了年度（西暦・例 2030）", 2030),
        (
            "data_source [任意]",
            "プロフィール数値の出所（'estimated' or 'actual'・空欄なら 'actual'）",
            "actual",
        ),
        (
            "load_factor_actual_pct [任意]",
            "積載率実績（%・0-100・空欄なら未指定）",
            42.0,
        ),
        (
            "annual_fuel_liters [任意]",
            "年間燃料消費量（L・空欄なら未指定）",
            1_500_000.0,
        ),
        (
            "annual_co2_emissions_kg [任意]",
            "年間 CO2 排出量実績（kg-CO2・空欄なら未指定）",
            4_200_000.0,
        ),
    ]
    _write_columnar_template(ws, columns)


def _build_sites_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("sites")
    columns: list[tuple[str, str, str | int | float]] = [
        ("name [必須]", "拠点名", "本社物流センター"),
        ("site_type [必須]", "factory / dc / store / office / warehouse のいずれか", "dc"),
        ("prefecture [必須]", "都道府県名（正式名称・例: 東京都）", "千葉県"),
        ("annual_freight_tons [必須]", "年間取扱貨物量（トン・整数 or 小数）", 80_000),
    ]
    sample_rows: list[list[str | int | float]] = [
        ["関東センター", "dc", "千葉県", 80_000],
        ["関西センター", "dc", "大阪府", 50_000],
        ["九州センター", "dc", "福岡県", 20_000],
    ]
    _write_tabular_template(ws, columns, sample_rows)


def _build_wait_time_sheet(wb: Workbook) -> None:
    """annual 用 wait_time シート（年集計の bucket_label・現行互換）。"""
    ws = wb.create_sheet("wait_time")
    columns: list[tuple[str, str, str | int | float]] = [
        ("bucket_label [必須]", "集計区分（例: '全体', '関東センター'）", "全体"),
        ("measured_count [必須]", "計測便数（整数・0以上）", 5000),
        ("average_minutes [必須]", "平均荷待ち時間（分・0以上）", 28),
        ("max_minutes [必須]", "最大荷待ち時間（分・0以上）", 110),
        ("over_2h_count [必須]", "2時間超 件数（整数・0以上）", 4),
    ]
    sample_rows: list[list[str | int | float]] = [
        ["全体", 5000, 28, 110, 4],
        ["関東センター", 3000, 25, 90, 1],
        ["関西センター", 2000, 32, 110, 3],
    ]
    _write_tabular_template(ws, columns, sample_rows)


def _build_wait_time_monthly_sheet(wb: Workbook) -> None:
    """monthly 用 wait_time シート（月集計ラベル・スキーマは annual と同一）。

    bucket_label を「YYYY-MM 集計区分」の月次集計形式にしたサンプルを配布する。
    handling_time / kpi_history と組合せて月次レビューの起点に使う想定。
    """
    ws = wb.create_sheet("wait_time")
    columns: list[tuple[str, str, str | int | float]] = [
        (
            "bucket_label [必須]",
            "月集計区分（例: '2026-04 全体', '2026-04 関東センター'）",
            "2026-04 全体",
        ),
        ("measured_count [必須]", "計測便数（整数・0以上・当月実績）", 4200),
        ("average_minutes [必須]", "平均荷待ち時間（分・0以上）", 26),
        ("max_minutes [必須]", "最大荷待ち時間（分・0以上）", 105),
        ("over_2h_count [必須]", "2時間超 件数（整数・0以上）", 2),
    ]
    sample_rows: list[list[str | int | float]] = [
        ["2026-04 全体", 4200, 26, 105, 2],
        ["2026-04 関東センター", 2500, 24, 88, 1],
        ["2026-04 関西センター", 1700, 28, 105, 1],
        ["2026-05 全体", 4350, 25, 95, 1],
        ["2026-05 関東センター", 2600, 23, 80, 0],
        ["2026-05 関西センター", 1750, 27, 95, 1],
    ]
    _write_tabular_template(ws, columns, sample_rows)


def _build_wait_time_daily_sheet(wb: Workbook) -> None:
    """daily 用 wait_time シート（site×日付×slot の軽量版）。

    bucket_label を「YYYY-MM-DD <時間帯>」形式にし、site_name と time_slot 列を
    埋めた状態で配布する（ヒートマップ系・コックピット系で日次粒度の入力を促す）。

    site_name / time_slot は WaitTimeRow の Optional フィールドで、ローダー側も
    空欄を許容するため annual / monthly と同じローダーで取込可能。
    """
    ws = wb.create_sheet("wait_time")
    columns: list[tuple[str, str, str | int | float]] = [
        (
            "bucket_label [必須]",
            "日次区分（例: '2026-05-01 朝便', '2026-05-01 昼便'）",
            "2026-05-01 朝便",
        ),
        ("measured_count [必須]", "当該便の計測件数（整数・0以上）", 35),
        ("average_minutes [必須]", "平均荷待ち時間（分・0以上）", 42),
        ("max_minutes [必須]", "最大荷待ち時間（分・0以上）", 95),
        ("over_2h_count [必須]", "2時間超 件数（整数・0以上）", 0),
        (
            "site_name [任意]",
            "拠点名（sites シートと一致させる・空欄可）",
            "関東センター",
        ),
        (
            "time_slot [任意]",
            "時間帯（morning=6-10 / midday=10-15 / evening=15-19 / night=19-翌6）",
            "morning",
        ),
    ]
    sample_rows: list[list[str | int | float]] = [
        ["2026-05-01 朝便", 35, 42, 95, 0, "関東センター", "morning"],
        ["2026-05-01 昼便", 50, 28, 70, 0, "関東センター", "midday"],
        ["2026-05-01 夕便", 25, 32, 80, 0, "関東センター", "evening"],
        ["2026-05-01 夜便", 8, 18, 40, 0, "関東センター", "night"],
        ["2026-05-02 朝便", 38, 45, 110, 0, "関東センター", "morning"],
        ["2026-05-02 昼便", 48, 26, 65, 0, "関東センター", "midday"],
        ["2026-05-01 朝便", 20, 30, 65, 0, "関西センター", "morning"],
        ["2026-05-01 昼便", 28, 22, 55, 0, "関西センター", "midday"],
    ]
    _write_tabular_template(ws, columns, sample_rows)


def _build_handling_time_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("handling_time")
    columns: list[tuple[str, str, str | int | float]] = [
        ("bucket_label [必須]", "納品形態（例: 'パレット納品', 'バラ納品'）", "パレット納品"),
        ("measured_count [必須]", "計測便数（整数・0以上）", 3500),
        ("average_minutes [必須]", "平均荷役時間（分・0以上）", 30),
        ("max_minutes [必須]", "最大荷役時間（分・0以上）", 95),
        ("over_1h_pct [必須]", "1時間超 割合（%・0-100）", 5.0),
    ]
    sample_rows: list[list[str | int | float]] = [
        ["パレット納品", 3500, 30, 95, 5.0],
        ["バラ納品", 600, 75, 130, 14.0],
    ]
    # 注記: 連鎖化事業者は荷役等時間が法令上対象外のため、サンプル行を全て削除して
    # シートを空にして取込してよい（詳細は docs/data_input_guide.md 参照）
    _write_tabular_template(ws, columns, sample_rows)


def _build_kpi_history_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("kpi_history")
    columns: list[tuple[str, str, str | int | float]] = [
        ("fy [必須]", "年度（西暦・例 2024）", 2024),
        (
            "metric [必須]",
            "KPI 識別子（例: 'load_factor_pct' / 'co2_intensity_g_per_tonkm' / "
            "'wait_time_avg_minutes' / 'fuel_liters'）",
            "load_factor_pct",
        ),
        ("value [必須]", "値（unit に従う）", 40.0),
        ("unit [必須]", "単位（例: '%', 'g/トンキロ', '分', 'L'）", "%"),
    ]
    sample_rows: list[list[str | int | float]] = [
        [2023, "load_factor_pct", 39.5, "%"],
        [2024, "load_factor_pct", 40.5, "%"],
        [2025, "load_factor_pct", 41.0, "%"],
    ]
    # 注記: 任意シート — 入力なしの場合は 3 行目以降を空にする
    # （詳細は docs/data_input_guide.md 参照）
    _write_tabular_template(ws, columns, sample_rows)


def _build_jsic_reference_sheet(wb: Workbook) -> None:
    """JSIC 主要業種の参照シート（記入時の補助）。"""
    ws = wb.create_sheet("_jsic_reference")
    rows: list[tuple[str, str]] = [
        ("3159", "その他の電子部品・デバイス製造業（製造業 例）"),
        ("5411", "農畜産物・水産物卸売業（卸売業 例）"),
        ("5514", "室内装飾繊維品卸売業（卸売業 例）"),
        ("5891", "コンビニエンスストア（連鎖化 例）"),
        ("6021", "鉄道貨物運送業（運輸業 例）"),
        ("6411", "一般貨物自動車運送業（運輸業 例）"),
        ("8311", "総合スーパー（小売業 例）"),
    ]
    ws.cell(row=1, column=1).value = "jsic_code"
    ws.cell(row=1, column=2).value = "業種名（例）"
    for c in (1, 2):
        ws.cell(row=1, column=c).font = _HEADER_FONT
        ws.cell(row=1, column=c).fill = _HEADER_FILL
    for idx, (code, label) in enumerate(rows, start=2):
        ws.cell(row=idx, column=1).value = code
        ws.cell(row=idx, column=2).value = label
    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 50
    note_cell = ws.cell(row=len(rows) + 3, column=1)
    note_cell.value = "※ 上記は代表例。完全な JSIC コードは総務省「日本標準産業分類」を参照。"
    note_cell.font = _DESCRIPTION_FONT


# --- 共通ヘルパー ---------------------------------------------------------


def _write_columnar_template(
    ws: Worksheet,
    columns: list[tuple[str, str, str | int | float | bool]],
) -> None:
    """profile シート用 — 縦に並ぶ単一行入力（A列: 項目名 / B列: 値 / C列: 説明）。"""
    ws.cell(row=1, column=1).value = "項目"
    ws.cell(row=1, column=2).value = "値（ここに記入）"
    ws.cell(row=1, column=3).value = "説明"
    for c in (1, 2, 3):
        ws.cell(row=1, column=c).font = _HEADER_FONT
        ws.cell(row=1, column=c).fill = _HEADER_FILL
    for idx, (name, desc, sample) in enumerate(columns, start=2):
        ws.cell(row=idx, column=1).value = name
        ws.cell(row=idx, column=2).value = sample
        ws.cell(row=idx, column=2).font = _SAMPLE_FONT
        ws.cell(row=idx, column=3).value = desc
        ws.cell(row=idx, column=3).font = _DESCRIPTION_FONT
    ws.column_dimensions["A"].width = 35
    ws.column_dimensions["B"].width = 25
    ws.column_dimensions["C"].width = 70


def _write_tabular_template(
    ws: Worksheet,
    columns: list[tuple[str, str, str | int | float]],
    sample_rows: list[list[str | int | float]],
) -> None:
    """sites/wait_time/handling_time/kpi_history シート用 — 横並びの表形式。

    1 行目: ヘッダ
    2 行目: 列の説明
    3 行目以降: サンプル行（薄いグレー文字・記入時に置換）

    注: ノート/警告は docs/data_input_guide.md に集約してシート上には書かない。
    シート上に書くと loader が表データとして誤読する可能性があるため。
    """
    # 1 行目: ヘッダ
    for col_idx, (name, _desc, _sample) in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.value = name
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(wrap_text=True, vertical="center")

    # 2 行目: 説明
    for col_idx, (_name, desc, _sample) in enumerate(columns, start=1):
        cell = ws.cell(row=2, column=col_idx)
        cell.value = desc
        cell.font = _DESCRIPTION_FONT
        cell.fill = _DESCRIPTION_FILL
        cell.alignment = Alignment(wrap_text=True, vertical="center")

    # 3 行目以降: サンプル行（薄いグレー文字）
    for row_offset, row_values in enumerate(sample_rows, start=3):
        for col_idx, value in enumerate(row_values, start=1):
            cell = ws.cell(row=row_offset, column=col_idx)
            cell.value = value
            cell.font = _SAMPLE_FONT

    # 列幅
    for col_idx in range(1, len(columns) + 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 24
