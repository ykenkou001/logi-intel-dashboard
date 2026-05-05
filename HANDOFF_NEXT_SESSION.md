# 次セッションへの引継ぎ（2026-05-06 時点）

> このファイルを最初に読み、`uv sync` 実行後に c.7 から着手する。

---

## 🎯 次セッションのタスク: フェーズ5.0 段階 c — c.7 MCP/REST 公開

### 全体像

`plans/b-c-flickering-pixel.md`（健一の `~/.claude/plans/` 配下）の **段階 c** のうち、c.1〜c.6 は完了済（PR #11 マージ済 + 本セッション PR）。次は **c.7 MCP/REST 公開** で、F2 標準化スコア + J2 罠スコアを Claude Desktop と Web ダッシュボードから呼べるようにする。

### 完了済の前提資産（直前 PR）

| PR | 内容 |
|---|---|
| 本セッション PR (TBD) | c.4 既存接続検証 + c.6 F2 標準化スコア + J2 罠スコア — `core/analytics/standardization_score.py` / `core/analytics/waste_trap.py` + テスト 56 件 |
| #11 (merged) | c.1 マトリクス + c.2 データモデル + c.3 resolve / Override 永続化 — `core/playbook/industry_packages.py` + `core/io/override_store.py` + テスト 88 件 |
| #10 (merged) | フェーズ4.5 B 用途別テンプレ生成（daily/monthly/annual） |
| #9 #8 #7 (merged) | b 段階：J3 デイリーコックピット中核 / Web 画面 / シナリオテスト |

---

## ⚠️ 並行作業の注意（最初に必ず確認）

健一は **Claude / Codex を別セッションで並行起動** して別領域を担当させる運用。

- 現時点で他領域に並行作業の予定はないが、本セッション開始前に健一に「Codex 並行作業はあるか？」を確認する
- 衝突可能性が高い共有領域:
  - `mcp_server/tools/clo_tools.py` — c.7 で 3 ツール追加
  - `api/routers/clo.py` — c.7 で 3 エンドポイント追加
  - `pyproject.toml` の dependencies — どちらも触る可能性

詳細 → メモリ `feedback_codex_parallel_collaboration.md` / CLAUDE.md §9

**`main` への直接 push は禁止**。必ず feature ブランチ + PR 経由。

---

## 📋 必読ドキュメント（着手前）

1. **CLAUDE.md** — プロジェクト全体方針。特に §1.5 ミッション宣言 / §6.5 dev サーバ起動ルール / §7 検証ルール / §9 Codex 協業方針
2. **plans/b-c-flickering-pixel.md** §段階 c.7 — MCP/REST 公開仕様（健一の `~/.claude/plans/b-c-flickering-pixel.md`）
3. **core/analytics/standardization_score.py** — F2 戻り値 `StandardizationScoreResult` 構造
4. **core/analytics/waste_trap.py** — J2 戻り値 `WasteTrapResult` + 入力モデル `MeasureExecutionRecord`
5. **mcp_server/tools/clo_tools.py** — 既存 MCP ツール命名規則・実装パターン
6. **api/routers/clo.py** — 既存 REST エンドポイント命名規則・ToolResponse 構造

---

## 🛠 実装スコープ

### c.7-1: MCP ツール 3 件追加

実装ファイル: `mcp_server/tools/clo_tools.py`（既存パターンに合わせる）

| MCP ツール名 | 内部呼出 | 入力 | 用途 |
|---|---|---|---|
| `logi_clo_industry_package` | `core.playbook.industry_packages.resolve_company_package` | `company_id`（任意で override JSON）| 業種別 標準パッケージを返す |
| `logi_clo_standardization_score` | `core.analytics.standardization_score.compute_standardization_score` | `company_id` | F2 標準化スコア |
| `logi_clo_waste_traps` | `core.analytics.waste_trap.detect_waste_traps` | `company_id` + `measure_runs` リスト | J2 罠検出（measure_runs は当面 fixtures 経由） |

戻り値構造（既存 ToolResponse ライク）:
```python
{
    "summary": "標準化スコア: 78/100 (coverage 80% / unmanaged 1 件)",
    "data": <Pydantic.model_dump()>,
    "citations": [c.to_dict() for c in result.citations],
    "freshness_warnings": result.freshness_warnings,
}
```

### c.7-2: REST エンドポイント 3 件追加

実装ファイル: `api/routers/clo.py`

| エンドポイント | response_model | 注記 |
|---|---|---|
| `GET /clo/industry-package/{company_id}` | `IndustryPackage` | Override は load_override で自動取得 |
| `GET /clo/standardization-score/{company_id}` | `StandardizationScoreResult` | 同上 |
| `POST /clo/waste-traps/{company_id}` | `WasteTrapResult` | body は `list[MeasureExecutionRecord]` |

### c.7-3: テスト追加

- `tests/api/test_clo_routes.py` に 3 エンドポイント分のスモークテスト追加
- `tests/mcp/` 配下に MCP ツール 3 件のスモークテスト追加
- 推定テスト件数 15-20 件

---

## 🔧 ブランチ・コミット戦略

- ブランチ名: `feature/phase-5.0-scoring-mcp-rest`
- コミット粒度推奨:
  - commit 1: MCP ツール 3 件追加
  - commit 2: REST エンドポイント 3 件追加
  - commit 3: 統合テスト + Web 接続用クライアント関数追加（必要なら）
- 1 PR にまとめる想定
- PR タイトル: `feat(api,mcp): c.7 業種別パッケージ + F2/J2 を MCP/REST で公開`

---

## ✅ 検証チェックリスト

- [ ] `git pull origin main` で最新化
- [ ] `uv sync` で依存最新化
- [ ] `uv run pytest --tb=short -q` がベースライン pass（直近 main で 783+ 件全 pass のはず）
- [ ] `uv run ruff check` クリーン
- [ ] **Claude Desktop 実機確認**（CLAUDE.md §7 の Step 検証ルール）:
  - サンプル 4 社（mfg/wholesale/retail/chain）で 3 ツールを呼び出し、出力値の妥当性確認
  - F2: 各社の score / coverage_pct / missing_kpi_ids / missing_measure_ids が現実的か
  - J2: actual_effect_jpy=None のサンプル run で trap_severity=low が固定されるか
- [ ] FastAPI 実機確認:
  - `pwsh scripts/dev_api.ps1` 起動 (CLAUDE.md §6.5 必須)
  - `curl localhost:8000/clo/standardization-score/sample_mfg_01` で動作確認
- [ ] PR 説明に「Codex 議論で確定した修正点」と「Claude 単独判断」を区別

---

## 🧠 Codex 協業の活用ポイント

CLAUDE.md §9.1 に従って、以下のタイミングで Codex に相談を **積極的に** する:

1. **MCP ツールの命名・パラメータ仕様** — 既存 `logi_clo_*` 命名規則との整合性レビュー依頼
2. **POST /waste-traps の body 設計** — `MeasureExecutionRecord` を 1 件ずつ受けるか list 受けるか、認証なしで OK か等
3. **Web 接続前のスキーマ確認** — c.9 で Next.js 側に F2/J2 ダッシュボードを足すときに使う TypeScript 型生成（`web/lib/api.ts`）の方針

呼出: `/codex setup` で疎通確認 → `/codex rescue` または `codex:codex-rescue` agent

---

## 📝 既存コードからの参考パターン

- **MCP ツール定義**: `mcp_server/tools/clo_tools.py` の `logi_clo_feasibility_check`（dataclass を ToolResponse に変換するパターン）
- **REST エンドポイント**: `api/routers/clo.py` の既存 `/clo/feasibility-check/{company_id}`
- **Pydantic v2 モデルの API レスポンス**: `core.analytics.standardization_score.StandardizationScoreResult` は frozen ConfigDict のため `model_dump(mode="json")` で serialize する

---

## 🚫 触らないこと

- `core/playbook/measures.py` の ALL_MEASURES 構造（フィールド追加・削除等）
- `core/io/template_writer.py` — 触る場合は健一確認
- `web/` 配下 — c.9 のスコープ
- 本 PR で実装した `core/analytics/standardization_score.py` / `core/analytics/waste_trap.py` の中核ロジック（API 公開での型変換のみ許容）
- `core/playbook/industry_packages.py` の `applicable_industries` 値（c.4 で既存不整合を修正済）

---

## 🗒 c.4-c.6 で持ち越した課題（c.7 とは別 PR）

1. **F2 施策実装ステータスの拡張**: 現状は Override の `target_kind="measure"` + approved/required_localization のみ。`decision_log`（DecisionRecord）と連動させるには DecisionRecord に measure_id フィールド追加が必要。c.7 後の改善 PR で対応。
2. **J2 actual_effect_jpy の自動逆算**: 現状は `actual_effect_jpy=None` で判定保留。kpi_history から「コスト削減施策なら物流コスト/売上比率の改善 × 売上」で逆算する補助関数を追加する。c.7 後の改善 PR で対応。
3. **F2 bonus 拡張**: 「全必須 KPI 実装 + 月次会議定着 → +10pt」は会議出席率データが乗らないため未実装。継続運用データが揃った段階で再導入。

---

## 完了の定義

- F2 / J2 / IndustryPackage が MCP 3 ツール + REST 3 エンドポイントで公開される
- pytest 783+ 全 pass + 新規 15+ 件全 pass
- ruff check クリア
- Claude Desktop 実機 + FastAPI 実機の両方で動作確認済
- PR を `feature/phase-5.0-scoring-mcp-rest` で作成し、Codex の助言反映点を PR 説明に明記
- HANDOFF_NEXT_SESSION.md を c.8/c.9（連鎖化特有処理 + Web 2 画面）向けに更新

---

## 📦 リポジトリ整理（2026-05-06）

- 本 PR の作業前に `git stash` で待避した CLAUDE.md / docs/roadmap.md / README.md の進捗反映 WIP は別途確認・統合する想定（`git stash list` で確認可能）。
- untracked: `docs/notebooklm/`, `docs/overview_for_review.md`, `docs/zenn_drafts/` は健一の WIP（触らない）。
