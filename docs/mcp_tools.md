# MCP ツール命名規則・設計指針

**責任範囲**: `mcp_server/tools/` 配下のツール定義の命名・実装方針。新しいツールを追加する前の必読ドキュメント。

---

## プレフィックス規則

全ツール名は `logi_` で始める。

命名パターン: `logi_{datasource_or_purpose}_{action}`

> **重要**: CLO 計画策定の文脈で使うツール（業界ベンチマーク・ドライバーギャップ・施策評価等）は **すべて `logi_clo_*` に統一**する。旧表記 `logi_analyze_*` は廃止。

---

## データソース別プレフィックス

| プレフィックス | 用途 | ツール例 |
|--------------|------|----|
| `logi_estat_*` | e-Stat 単独 | `logi_estat_search`, `logi_estat_get_data` |
| `logi_corp_*` | 国税庁法人番号 単独 | `logi_corp_search`, `logi_corp_by_pref` |
| `logi_traffic_*` | xROAD 交通量 単独 | `logi_traffic_realtime`, `logi_traffic_by_bbox` |
| `logi_weather_*` | 気象庁 単独 | `logi_weather_forecast`, `logi_weather_warning` |
| `logi_fuel_*` | 燃料価格 単独 | `logi_fuel_price`, `logi_fuel_history` |
| `logi_macro_*` | 都道府県マクロ統合 | `logi_macro_overview` |
| `logi_clo_*` | **CLO 計画策定支援（複合分析・成果物生成）** | `logi_clo_benchmark_position`, `logi_clo_driver_gap`, `logi_clo_target_proposal`, `logi_clo_plan_draft`, `logi_clo_periodic_report_draft` |

---

## ツール定義のルール

1. **docstring は日本語で詳細に書く** — Claude がツール選択する根拠になるため
2. **引数は Pydantic モデルで定義する**
3. **戻り値は構造化レスポンス（後述）に統一する** — 文字列だけ返してはいけない
4. **エラー時は構造化したエラー情報を返す**
5. **ロジックは core に書く** — ツール層は core の呼び出しのみ
6. **CLO 関連ツールは必ず `core/export/` を経由してファイル成果物を返す** — 「Claude の会話画面で完結」させない

---

## 戻り値構造（フェーズ2.5 で統一）

すべての MCP ツールは以下の構造化レスポンスを返す。

```python
{
    "summary": str,                            # Claude/人間に読ませる要約テキスト
    "files": dict[str, str] | None,            # 成果物ファイルのパス（必要時のみ）
    "citations": list[dict],                   # 出典情報のリスト（必須）
    "freshness_warnings": list[str] | None,    # 古いデータの警告（鮮度管理）
}
```

### `citations` の構造

```python
{
    "label": "経済センサス‐活動調査 2021",   # 人間が読む名称
    "stats_data_id": "0004005642",          # e-Stat の場合
    "notice_number": "...",                 # 告示番号（該当時のみ）
    "ordinance_number": "...",              # 省令番号（該当時のみ）
    "fetched_at": "2026-05-02T10:00:00+09:00",
    "url": "https://www.e-stat.go.jp/...",
}
```

### `files` の例（CLO 計画書ドラフト）

```python
{
    "ppt": "outputs/ppt/clo_plan_acme_1714628400_a1b2.pptx",
    "pdf": "outputs/pdf/clo_plan_acme_1714628400_a1b2.pdf",
    "excel": "outputs/excel/clo_plan_acme_1714628400_a1b2.xlsx",
    "docx_form3": "outputs/docx/form3_acme_1714628400_a1b2.docx",
    "markdown": "outputs/markdown/clo_plan_acme_1714628400_a1b2.md",
}
```

### ファイル名衝突回避命名

`outputs/{type}/{purpose}_{company_id}_{unix_ts}_{rand4}.{ext}` で命名する（同時実行時の衝突回避）。

---

## フェーズ別 実装対象ツール

### フェーズ 1（完了）

| ツール名 | 機能 |
|---------|------|
| `logi_estat_search` | 統計表をキーワードで検索 |
| `logi_estat_get_data` | 統計表 ID を指定してデータを取得 |
| `logi_estat_resolve_code` | 地域コード・分類コードを名称に変換 |

### フェーズ 2（完了）

| ツール名 | 機能 |
|---------|------|
| `logi_corp_*` | 国税庁法人番号 |
| `logi_traffic_*` | xROAD 交通量 |
| `logi_weather_*` | 気象庁 警報・予報 |
| `logi_fuel_price` | 燃料価格（gogo.gs） |
| `logi_macro_overview` | 都道府県マクロ概況 統合 |

### フェーズ 2.5（着手中）

| ツール名 | 機能 |
|---------|------|
| 既存全ツール | 戻り値を `{summary, files, citations}` 構造に統一 |
| `logi_fuel_history` | 燃料価格の蓄積履歴を返す（新規） |

### フェーズ 3

| ツール名 | 機能 |
|---------|------|
| `logi_clo_benchmark_position` | 業界ベンチマーク（業種別・地域別） |
| `logi_clo_driver_gap` | ドライバー需給ギャップ |
| `logi_clo_eligibility` | 特定荷主3区分の判定 |
| `logi_clo_target_proposal` | 数値目標の提案 |
| `logi_clo_simulate_*` | 施策効果シミュレータ |
| `logi_clo_certified_match` | 物流効率化法 認定事業マッチング |
| `logi_clo_plan_draft` | **中長期計画書ドラフト統合生成** |

### フェーズ 3.5

| ツール名 | 機能 |
|---------|------|
| `logi_clo_measure_eval` | 施策評価エンジン |
| `logi_clo_scenario_sim` | シナリオシミュレータ |
| `logi_clo_financial_translate` | 物流KPI → 経営指標翻訳 |
| `logi_clo_feasibility_check` | 実現可能性チェッカー |
| `logi_clo_submission_validate` | 提出前バリデータ |
| `logi_clo_periodic_report_draft` | **定期報告書（様式第5）ドラフト** |

### フェーズ 4.0 / 4.5

| ツール名 | 機能 |
|---------|------|
| `logi_clo_load_company` | 自社プロフィール Excel/CSV テンプレ取込 |
| `logi_clo_generate_template` | 用途別（daily / monthly / annual）入力テンプレ生成 |
| `logi_clo_today_decisions` | J3 デイリーコックピット（今日の 3 判断 + 想定反論） |

### フェーズ 5.0

| ツール名 | 機能 |
|---------|------|
| `logi_clo_industry_package` | 業種別 CLO 標準パッケージ（4 業種 × 5 要素マトリクス） |
| `logi_clo_standardization_score` | F2 標準化スコア（業種標準への準拠度 0-100） |
| `logi_clo_waste_traps` | J2 罠スコア（6 軸セーフガード付きの誤検知抑止検出） |

### フェーズ 5.5（Tier S）

| ツール名 | 機能 | 関連 Tier |
|---------|------|---|
| `logi_clo_decision_log_record` | 経営判断スナップショットを jsonl 永続化（様式第 5 証跡引用可） | S1 |
| `logi_clo_decision_log_query` | 新旧 jsonl 統合読み出し（フィルタ + 日付範囲 + limit） | S1 |
| `logi_clo_kpi_timeseries` | 月次 KPI 推移 + 業界平均 + 悪化アラート（最大 24 ヶ月）| S2 |
| `logi_clo_record_monthly_snapshot` | 月次スナップショット記録（cockpit_snapshots 月平均化 + F2/J2 + 物流コスト比率） | S2 |
| `logi_clo_facility_register` | 報告単位 1 施設の登録 / 更新（upsert） | S3 |
| `logi_clo_facility_list` | 自社の登録 Facility 一覧 | S3 |
