# Logi-Intel Dashboard REST API

FastAPI ベースの REST API 層。`core/` のビジネスロジックを HTTP エンドポイントとして公開する。

## 起動方法

```bash
uv run uvicorn api.main:app --reload --port 8000
```

- Swagger UI: http://localhost:8000/docs
- ReDoc:      http://localhost:8000/redoc
- OpenAPI:    http://localhost:8000/openapi.json
- Health:     http://localhost:8000/health

## エンドポイント一覧

### Meta
| Method | Path | 用途 |
|--------|------|------|
| GET | `/` | ドキュメント URL の案内 |
| GET | `/health` | ヘルスチェック（AWS ALB 用） |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc |

### CLO 支援（`/api/v1/clo/*`）
| Method | Path | 対応 MCP ツール |
|--------|------|------------------|
| GET  | `/benchmark` | logi_clo_benchmark_position |
| GET  | `/driver-gap` | logi_clo_driver_gap |
| GET  | `/eligibility` | logi_clo_eligibility |
| GET  | `/target-proposal` | logi_clo_target_proposal |
| GET  | `/simulate-measures` | logi_clo_simulate_measures |
| GET  | `/certified-match` | logi_clo_certified_match |
| GET  | `/playbook` | logi_clo_playbook_search |
| GET  | `/measure-eval/{company_id}` | logi_clo_measure_eval |
| GET  | `/feasibility/{company_id}` | logi_clo_feasibility_check |
| POST | `/plan-draft/{company_id}` | logi_clo_plan_draft |
| POST | `/scenario-sim/{company_id}` | logi_clo_scenario_sim |
| POST | `/financial-translate/{company_id}` | logi_clo_financial_translate |
| POST | `/submission-validate/{company_id}` | logi_clo_submission_validate |
| POST | `/periodic-report/{company_id}` | logi_clo_periodic_report_draft |

### マクロ概況（`/api/v1/macro/*`）
| Method | Path | 対応 MCP ツール |
|--------|------|------------------|
| GET | `/overview` | logi_macro_overview |

### 自社プロフィール（`/api/v1/company/*`）
| Method | Path | 対応 MCP ツール |
|--------|------|------------------|
| POST | `/template` | logi_clo_generate_template |
| POST | `/load`（multipart） | logi_clo_load_company |
| GET | `/samples` | （新規・サンプル3社の列挙） |

### 成果物ダウンロード（`/api/v1/files/*`）
| Method | Path | 用途 |
|--------|------|------|
| GET | `/{file_path}` | `outputs/` 配下の成果物（PPT/Word/Excel/Markdown/PDF/JSON）配信 |

## レスポンス構造

全 CLO/macro/company エンドポイントは MCP ツールと同じ `ToolResponse` を JSON で返す。

```json
{
  "summary": "人間が読む要約テキスト",
  "files": {
    "ppt": "outputs/ppt/clo_plan_xxx_xxx.pptx",
    "docx": "outputs/docx/form3_xxx_xxx.docx",
    "excel": "outputs/excel/clo_plan_xxx_xxx.xlsx",
    "markdown": "outputs/markdown/clo_plan_xxx_xxx.md"
  },
  "citations": [
    {
      "label": "...",
      "url": "https://...",
      "stats_data_id": null,
      "notice_number": null,
      "ordinance_number": null,
      "fetched_at": "2026-05-03T12:34:56+00:00",
      "accessed_via": "..."
    }
  ],
  "freshness_warnings": ["..."],
  "data_source": "estimated"
}
```

`files.*` の値は `/api/v1/files/{path}` でダウンロードできる相対パス（`outputs/` から見た相対）。

## CORS

開発時はワイルドカード許可（`*`）。AWS 移行時に `LOGI_API_CORS_ORIGINS` 環境変数で社内ドメインに絞る。

```bash
LOGI_API_CORS_ORIGINS=https://logi-intel.micware.internal,https://staging.logi-intel.micware.internal
```

## テスト

```bash
uv run pytest tests/api -v
```

27 件の TestClient ベースのスモークテスト + 統合テスト。外部 API（e-Stat 等）を叩く benchmark / driver-gap / macro-overview は core 側で既にカバー済みのため REST 経路では省略。
