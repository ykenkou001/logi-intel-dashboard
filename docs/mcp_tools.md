# MCP ツール命名規則・設計指針

**責任範囲**: `mcp_server/tools/` 配下のツール定義の命名・実装方針。新しいツールを追加する前の必読ドキュメント。

---

## プレフィックス規則

全ツール名は `logi_` で始める。

命名パターン: `logi_{datasource}_{action}`

---

## データソース別プレフィックス

| データソース | プレフィックス | ツール例 |
|------------|--------------|----|
| e-Stat | `logi_estat_*` | `logi_estat_search`, `logi_estat_get_data` |
| RESAS | `logi_resas_*` | `logi_resas_industry`, `logi_resas_population` |
| 国税庁法人番号 | `logi_corp_*` | `logi_corp_search`, `logi_corp_by_pref` |
| xROAD | `logi_traffic_*` | `logi_traffic_realtime`, `logi_traffic_by_route` |
| 気象庁 | `logi_weather_*` | `logi_weather_forecast`, `logi_weather_warning` |
| エネ庁 | `logi_fuel_*` | `logi_fuel_price`, `logi_fuel_subsidy` |
| 複合分析 | `logi_analyze_*` | `logi_analyze_benchmark`, `logi_analyze_driver_gap` |
| CLO 支援 | `logi_clo_*` | `logi_clo_plan_draft`, `logi_clo_kpi_compare` |

---

## ツール定義のルール

1. **docstring は日本語で詳細に書く** — Claude がツール選択する根拠になるため
2. **引数は Pydantic モデルで定義する**
3. **戻り値は Claude が読みやすい形式に整形する** — コード → 名称変換済みで返す
4. **エラー時は構造化したエラー情報を返す**
5. **ロジックは core に書く** — ツール層は core の呼び出しのみ

---

## フェーズ 1 実装対象ツール（e-Stat）

| ツール名 | 機能 |
|---------|------|
| `logi_estat_search` | 統計表をキーワードで検索 |
| `logi_estat_get_data` | 統計表 ID を指定してデータを取得 |
| `logi_estat_resolve_code` | 地域コード・分類コードを名称に変換 |
