# 自社データ入力ガイド（フェーズ4.0「実データ入力フォーム」）

**責任範囲**: サンプル4社からの脱却と実データ取込の手順。CLO 担当者向けの記入ガイドラインも兼ねる。

> ⚠️ 本機能は **2026-10 末の初回中長期計画提出**に直接効く機能。サンプル4社で生成した計画書は内容が架空なので、本番提出には自社実データを取り込む必要がある。
>
> 📘 自社プロフィール入力画面そのものの使い方（テンプレ用途・読み方）は [docs/dashboard_feature_guide.md §4.2](dashboard_feature_guide.md#42-自社プロフィール入力) を参照。本ガイドは Excel シート単位の項目仕様を扱う。

---

## 全体フロー

```
1. テンプレ Excel を生成 (logi_clo_generate_template)
       ↓
2. CLO 担当者が自社データを記入
       ↓
3. 取込 (logi_clo_load_company)
       ↓ outputs/profiles/<company_id>.json に永続化
       ↓
4. 既存 CLO ツール群（plan_draft / periodic_report 等）が
   サンプル3社と同じ company_id 引数で実データを参照
```

---

## Step 1: テンプレ Excel を生成

Claude Desktop / Code から:

```
logi_clo_generate_template
```

→ 既定（`purpose="annual"`）で `outputs/templates/sample_company_template.xlsx` に生成される。

カスタムパスを指定する場合:

```
logi_clo_generate_template(output_path="C:/work/my_company.xlsx")
```

### 用途別 3 種類のテンプレ（フェーズ4.5 B）

「何を・どの粒度で・いつ入力するか」を明確にするため、用途別 3 種類のテンプレを生成できる。
スキーマ（`CompanyProfile` / `WaitTimeRow` 等）はすべて共通なので、いずれの用途で記入しても
同じ `logi_clo_load_company` で取込可能。

| `purpose` | 用途 | 含まれるシート | 想定運用頻度 |
|-----------|------|----------------|------------|
| `annual`（既定） | 計画策定（中長期計画） | profile / sites / wait_time(年集計) / handling_time / kpi_history / _jsic_reference | 年 1 回 |
| `monthly` | 月次レビュー | profile / sites / wait_time(月集計) / handling_time / kpi_history / _jsic_reference | 月 1 回 |
| `daily` | 日次運用入力（コックピット／ヒートマップ） | profile / sites / wait_time(日次・site×slot) / _jsic_reference | 日次 |

`monthly` の `wait_time.bucket_label` は「`2026-04 全体`」「`2026-04 関東センター`」のような月集計形式で配布。
`daily` の `wait_time` は `bucket_label`（例 `2026-05-01 朝便`）に加えて `site_name` と `time_slot`
（`morning` / `midday` / `evening` / `night`）列にサンプル値を埋めた状態で配布する。

呼び出し例:

```
logi_clo_generate_template(purpose="daily")        # 日次運用用
logi_clo_generate_template(purpose="monthly")      # 月次レビュー用
logi_clo_generate_template(purpose="annual")       # 計画策定用（既定）
```

REST API では `POST /api/v1/company/template?purpose=daily` のようにクエリパラメータで指定する。
Web UI では「自社プロフィール入力」画面の Step 1 で 3 用途のラジオから選択する。

---

## Step 2: シート別記入ガイド

### `profile` シート（縦並びの単一行）

A 列が項目名、B 列が値、C 列が説明。**B 列のサンプル値（薄いグレー）を自社の値に置換**する。

| 項目 | 必須/任意 | 例 | 注意点 |
|------|---------|----|------|
| `company_id` | 必須 | `logi_shoji_01` | 英数字とアンダースコアのみ。**JSON ファイル名にも使う** |
| `name` | 必須 | `ロジ商事株式会社` | 漢字可 |
| `jsic_code` | 必須 | `5514` | 4桁。`_jsic_reference` シート参照 |
| `main_business` | 必須 | `産業機械卸売業` | 様式第3 「主たる事業」欄に流用 |
| `annual_revenue_jpy` | 必須 | `50000000000` | **円・整数**（億円ではない） |
| `annual_freight_tons_total` | 必須 | `150000` | トン。**9万トン超で特定第一種荷主**判定 |
| `operating_profit_jpy` | 必須 | `1500000000` | 円。財務翻訳レイヤの基準 |
| `cost_of_goods_sold_jpy` | 必須 | `42000000000` | 円。物流コスト削減を売上原価減として反映 |
| `is_chain_franchise` | 必須 | `FALSE` | TRUE / FALSE。コンビニ本部等のフランチャイズ展開のみ TRUE |
| `fleet_count_owned` | 任意 | `5` | 自社保有車両数 |
| `fleet_count_outsourced` | 任意 | `200` | 委託車両数 |
| `clo_name` | 必須 | `専務執行役員 鈴木 太郎` | 役職 + 氏名 |
| `plan_period_start_fy` | 必須 | `2026` | 西暦・計画期間開始年度 |
| `plan_period_end_fy` | 必須 | `2030` | 西暦・終了年度 |
| `data_source` | 任意 | `actual` | 既定 `actual`。推計値混在時のみ `estimated` に変更 |
| `load_factor_actual_pct` | 任意 | `42.0` | **積載率実績（%）**。空欄なら未指定で業界平均 38% にフォールバック |
| `annual_fuel_liters` | 任意 | `1500000` | 年間燃料消費量（L） |
| `annual_co2_emissions_kg` | 任意 | `4200000` | 年間 CO2 排出量実績（kg-CO2） |

### `sites` シート（拠点ごと 1 行）

| 列 | 必須/任意 | 例 | 注意点 |
|----|--------|----|------|
| `name` | 必須 | `関東センター` | 拠点名 |
| `site_type` | 必須 | `dc` | `factory` / `dc` / `store` / `office` / `warehouse` のいずれか |
| `prefecture` | 必須 | `千葉県` | 正式名称（「都道府県」を含む） |
| `annual_freight_tons` | 必須 | `80000` | 拠点単位の年間取扱量（トン） |

> **注**: `sites` は最低 1 拠点必須。`annual_freight_tons` の合計が `profile.annual_freight_tons_total` と概ね一致するように記入する。

### `wait_time` シート（荷待ち時間 計測実績）

様式第5 Ⅳ セクションに直接反映され、**改善基準告示の遵守判定**（最大 120 分基準）にも使われる。

| 列 | 必須/任意 | 例 | 注意点 |
|----|--------|----|------|
| `bucket_label` | 必須 | `全体` | 集計区分（例: `全体`, `関東センター`, `都市部拠点`） |
| `measured_count` | 必須 | `5000` | 計測便数（整数・0以上） |
| `average_minutes` | 必須 | `28` | 平均荷待ち時間（分・小数可） |
| `max_minutes` | 必須 | `110` | 最大荷待ち時間（分） |
| `over_2h_count` | 必須 | `4` | 2時間超 件数 |

> **計測体制が無い場合**: シートを空（3 行目以降を全削除）にして取込。loader は空リストとして扱う。様式第5 Ⅲ「追加措置」欄に「計測体制整備」が自動的に記載される。

### `handling_time` シート（荷役等時間 計測実績）

| 列 | 必須/任意 | 例 | 注意点 |
|----|--------|----|------|
| `bucket_label` | 必須 | `パレット納品` | 納品形態（例: `パレット納品`, `バラ納品`, `かご車納品`） |
| `measured_count` | 必須 | `3500` | 計測便数 |
| `average_minutes` | 必須 | `30` | 平均荷役時間（分） |
| `max_minutes` | 必須 | `95` | 最大荷役時間（分） |
| `over_1h_pct` | 必須 | `5.0` | 1時間超 割合（%・0-100） |

> **連鎖化事業者は荷役等時間が法令上対象外**。`handling_time` シートを空（3 行目以降を全削除）にして取込してよい。様式第5 出力時に Ⅳ-2 セクション全体が自動省略される。

### `kpi_history` シート（任意 — 直近 3 期 KPI 履歴）

trend 検出と実績ベースライン構築用。**未入力でも計画書ドラフトは生成可能**。

| 列 | 例 | 注意点 |
|----|----|------|
| `fy` | `2024` | 年度（西暦） |
| `metric` | `load_factor_pct` | KPI 識別子（推奨: `load_factor_pct` / `co2_intensity_g_per_tonkm` / `wait_time_avg_minutes` / `fuel_liters`） |
| `value` | `40.5` | 値（unit に従う） |
| `unit` | `%` | 単位 |

---

## Step 3: 取込

```
logi_clo_load_company(file_path="outputs/templates/sample_company_template.xlsx")
```

成功すると:
- `outputs/profiles/<company_id>.json` に保存される
- 取込サマリー（拠点数・計測値件数・data_source 等）が表示される

エラー例:
- `必須シートが欠落しています` → profile / sites シートを必ず含めること
- `company_id: Field required` → profile シートで company_id を空欄にしないこと
- `jsic_code: String should have at least 4 characters` → 4 桁の業種コードを記入

---

## Step 4: 実データで CLO ツール群を実行

取込が成功すると、**サンプル3社と同じ company_id 引数**で全 CLO ツールが実データで動作:

```
logi_clo_plan_draft(company_id="logi_shoji_01")
logi_clo_periodic_report_draft(company_id="logi_shoji_01")
logi_clo_submission_validate(company_id="logi_shoji_01")
```

実データ経由の場合、出力サマリーに `data_source: actual` が反映され、経営会議での defensibility が機械的に担保される。

---

## CSV 経路（補助）

CSV ファイル群を 1 ディレクトリに配置する形でも取込可能:

```
my_company/
├── profile.csv         # 必須（item, value 形式）
├── sites.csv           # 必須（横並び）
├── wait_time.csv       # 任意
├── handling_time.csv   # 任意
└── kpi_history.csv     # 任意
```

```
logi_clo_load_company(file_path="my_company/")
```

> 各 CSV は **1 行目がヘッダ・2 行目以降がデータ**（Excel と異なり**説明行は不要**）。ヘッダから `[必須]` `[任意]` マーカーは自動除去される。

---

## ID 解決の優先順位

`get_sample(company_id)` は以下の順で解決:

1. `outputs/profiles/<company_id>.json`（実データ・取込済み）
2. サンプル3社（`sample_mfg_01` / `sample_wholesale_01` / `sample_chain_01`）

→ サンプル ID と同じ ID で実データを取込すると**実データが優先**される。サンプルに戻したい場合は JSON ファイルを削除する。

---

## サンプル3社からの移行手順

1. テンプレ Excel を生成（`logi_clo_generate_template`）
2. 自社の決算書（売上・営業利益・売上原価）から `profile` シートを記入
3. 拠点リストを `sites` シートに転記
4. 動態管理システム（TMS）から荷待ち時間を `wait_time` シートに転記
5. 取込（`logi_clo_load_company`）
6. `logi_clo_plan_draft(company_id="<your_id>")` で実データ計画書を生成
7. `logi_clo_submission_validate(company_id="<your_id>")` で**準拠率レポート**を確認
8. 警告ゼロになるまで修正 → 様式第3別紙 Word を国交省提出

---

## トラブルシューティング

| エラー | 原因 | 対処 |
|--------|------|------|
| `必須シートが欠落` | profile / sites シートが無い | テンプレ Excel から再生成して記入し直す |
| `company_id: Field required` | profile シートの company_id 空欄 | 英数字 + アンダースコアの ID を記入 |
| `jsic_code: String should have at least 4 characters` | JSIC が 3 桁以下 | `_jsic_reference` シートから 4 桁コードを選ぶ |
| `annual_revenue_jpy: Input should be greater than or equal to 0` | 売上が負 or 文字列 | 数値（整数）として記入 |
| `シート 'sites' 行 N のバリデーションに失敗` | sites シート N 行目に不正値 | site_type が `factory` / `dc` / `store` / `office` / `warehouse` のいずれかか確認 |
| 取込後 plan_draft が空のまま | `outputs/profiles/` が読み込まれていない | `core/io/company_store.py` の `DEFAULT_PROFILES_DIR` が `outputs/profiles` を指していることを確認 |

---

最終更新: 2026-05-06（フェーズ4.5 B 軸 用途別テンプレ拡張：daily / monthly / annual の 3 種類対応）
