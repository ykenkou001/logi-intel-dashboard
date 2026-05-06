# 次セッションへの引継ぎ（2026-05-06 時点）

> このファイルを最初に読み、`uv sync` 実行後に c.8 から着手する。

---

## 🎯 次セッションのタスク: フェーズ5.0 段階 c — c.8 連鎖化特有処理 + c.9 統合テスト + Web 2 画面

### 全体像

`plans/b-c-flickering-pixel.md`（健一の `~/.claude/plans/` 配下）の **段階 c** のうち、c.1〜c.7 は完了済（PR #11 / #13 / #15(c.7)）。次は **c.8 連鎖化事業者特有処理** と **c.9 統合テスト + Web 画面 2 件** で、フェーズ5.0 を完了させる。

### 完了済の前提資産（直前 PR）

| PR | 内容 |
|---|---|
| #15 (本セッションでマージ予定) | c.7 業種別パッケージ + F2 / J2 を MCP / REST で公開 — `logi_clo_industry_package` / `logi_clo_standardization_score` / `logi_clo_waste_traps` の MCP 3 件 + 対応 REST 3 件 + テスト 21 件追加（pytest 804 件全 pass） |
| #13 (merged) | c.4 既存接続検証 + c.5/c.6 F2 標準化スコア + J2 罠スコア — `core/analytics/standardization_score.py` / `core/analytics/waste_trap.py` + テスト 73 件 |
| #11 (merged) | c.1 マトリクス + c.2 データモデル + c.3 resolve / Override 永続化 — `core/playbook/industry_packages.py` + `core/io/override_store.py` + テスト 88 件 |

---

## ⚠️ 並行作業の注意（最初に必ず確認）

健一は **Claude / Codex を別セッションで並行起動** して別領域を担当させる運用。

- 現時点で他領域に並行作業の予定はないが、本セッション開始前に健一に「Codex 並行作業はあるか？」を確認する
- 衝突可能性が高い共有領域:
  - `core/playbook/industry_packages.py` — c.8 で chain_franchise の強制ロジック追加
  - `core/analytics/standardization_score.py` / `waste_trap.py` — c.8 で連鎖化向けの調整
  - `web/app/dashboard/industry-package/` / `web/app/dashboard/standardization/` — c.9 の新規 2 画面（**Codex 優先領域**。CLAUDE.md §9.2）
  - `tests/api/test_clo_router.py` — c.9 で Web 用シナリオテスト追加

詳細 → メモリ `feedback_codex_parallel_collaboration.md` / CLAUDE.md §9

**`main` への直接 push は禁止**。必ず feature ブランチ + PR 経由。

---

## 📋 必読ドキュメント（着手前）

1. **CLAUDE.md** — プロジェクト全体方針。特に §1.5 ミッション宣言 / §6.5 dev サーバ起動ルール / §7 検証ルール / §9 Codex 協業方針
2. **plans/b-c-flickering-pixel.md** §段階 c.8 / c.9 — 連鎖化処理 + Web 2 画面の仕様（健一の `~/.claude/plans/b-c-flickering-pixel.md`）
3. **api/routers/clo.py** §c.7（`industry_package` / `standardization_score` / `waste_traps`）— Web 側で叩く REST のスキーマ
4. **mcp_server/tools/clo_tools.py** §c.7 — MCP ツール命名規則と body 形状
5. **core/playbook/industry_packages.py**（`_CHAIN_FRANCHISE_PACKAGE`）— 連鎖化向け仕様の現在地。c.8 で強制ガードを足す対象

---

## 🛠 実装スコープ

### c.8: 連鎖化事業者特有処理

実装ファイル: `core/playbook/industry_packages.py`（`_CHAIN_FRANCHISE_PACKAGE` の補強）+ `core/analytics/standardization_score.py`（必要なら）+ `core/legal/eligibility.py`（連鎖化判定の徹底）

仕様:

- `chain_franchise` パッケージで以下を強制:
  - `metric_id` に `handling_*` プレフィックスを持つ KPI を含めない
  - `form3_section == "loading"` の施策が `measure_ids` に紛れない（c.4 の整合性検証で検出済だが、ガード追加）
  - 様式第5 の `legal_basis` を `第65条`（旧 `第46条` ではない）に揃える
- 連鎖化 profile の F2 スコアで「実装すべきでない loading 系施策」を unmanaged_deviation として警告（必要なら）
- pytest で連鎖化サンプルが製造業向け施策を Override しても unmanaged で減点される挙動を保証

### c.9: 統合テスト + Web 画面 2 件

実装ファイル:

| 画面 | パス | 表示内容 |
|---|---|---|
| 業種別パッケージ閲覧 | `web/app/dashboard/industry-package/page.tsx` | 4 業種タブ × 5 要素（KPI / 施策 / 会議 / レポート / データ項目）の表 + Override 4 分類別件数 |
| 標準化スコア | `web/app/dashboard/standardization/page.tsx` | 自社 F2 スコア + 不足 KPI 一覧 + 未採用 施策一覧 + 差分テーブル |

接続:

- `web/lib/api.ts` に `getIndustryPackage(companyId)` / `getStandardizationScore(companyId)` を追加
- TypeScript 型は REST の `metadata` を反映（`IndustryPackage` / `StandardizationScoreResult` の Pydantic スキーマと完全一致）
- 既存 `cockpit/page.tsx` の Tailwind 配色を踏襲

統合テスト:

- `tests/api/test_clo_router.py` に「Web シナリオ：4 業種で `industry-package` → `standardization-score` 連動」の E2E
- pytest 825+ 件全 pass を目指す

---

## 🔧 ブランチ・コミット戦略

- ブランチ名: `feature/phase-5.0-chain-franchise-and-web`（c.8 と c.9 を 1 PR にまとめる場合）
  - 大きくなりすぎる場合は `feature/phase-5.0-c8-chain` と `feature/phase-5.0-c9-web` に分割可
- コミット粒度推奨:
  - commit 1: c.8 連鎖化強制ガード + テスト
  - commit 2: c.9 Web 2 画面（API クライアント拡張 + page.tsx 2 つ）
  - commit 3: c.9 統合テスト + ドキュメント更新
- 1 PR にまとめる場合 PR タイトル: `feat(playbook,web): c.8-c.9 連鎖化特有処理 + 業種別パッケージ Web 2 画面`

---

## ✅ 検証チェックリスト

- [ ] `git pull origin main` で最新化
- [ ] `uv sync` で依存最新化
- [ ] `uv run pytest --tb=short -q` がベースライン pass（直近 main で 804+ 件全 pass）
- [ ] `uv run ruff check` クリーン
- [ ] **Claude Desktop 実機確認**（CLAUDE.md §7 の Step 検証ルール）:
  - サンプル 4 社（mfg/wholesale/retail/chain）で c.7 の 3 ツールを呼び出し、c.8 の連鎖化強制ガードが効いているか
  - 特に sample_chain_01 で「製造業向け施策を Override で追加」しても F2 が減点される挙動
- [ ] FastAPI + Next.js 両方の実機確認:
  - `pwsh scripts/dev_api.ps1` 起動 (CLAUDE.md §6.5 必須)
  - `pwsh scripts/dev_web.ps1` 起動
  - http://localhost:3000/dashboard/industry-package で 4 業種タブが描画されるか
  - http://localhost:3000/dashboard/standardization で自社 F2 スコア + 差分テーブルが描画されるか
- [ ] PR 説明に「Codex 議論で確定した修正点」と「Claude 単独判断」を区別

---

## 🧠 Codex 協業の活用ポイント

CLAUDE.md §9.1 に従って、以下のタイミングで Codex に相談を **積極的に** する:

1. **Web 2 画面の Tailwind 設計** — Codex 優先領域（CLAUDE.md §9.2）。Claude は API スキーマ確定後に委譲する想定
2. **連鎖化向け F2 スコアの追加減点ロジック** — 「製造業施策を流用 → unmanaged 減点」の妥当性を Codex に独立評価依頼
3. **`metric_id` プレフィックスガード** — `handling_*` の正規表現か明示禁止リストかの選択

呼出: `/codex setup` で疎通確認 → `/codex rescue` または `codex:codex-rescue` agent

---

## 📝 既存コードからの参考パターン

- **業種別 KPI / 施策の整合性検証**: `tests/core/test_playbook_industry_packages.py`（c.4 の整合性テスト）
- **Web 画面 + REST 接続**: `web/app/dashboard/cockpit/page.tsx` + `web/lib/api.ts`（J3 デイリーコックピット）
- **REST → metadata → Web の型安全な伝播**: `api/routers/clo.py` の `today_decisions` / `industry_package` / `standardization_score`
- **Pydantic v2 の frozen ConfigDict + model_dump(mode="json")**: `IndustryPackage` / `StandardizationScoreResult` / `WasteTrapResult`

---

## 🚫 触らないこと

- `core/playbook/measures.py` の ALL_MEASURES 構造（フィールド追加・削除等）
- `core/io/template_writer.py` — 触る場合は健一確認
- 本セッションで追加した `core/analytics/standardization_score.py` / `core/analytics/waste_trap.py` の中核ロジック（連鎖化向けの追加判定で拡張は OK だが、既存閾値は変更しない）
- `core/playbook/industry_packages.py` の 4 業種パッケージの数値（KPI target_value 等）— Codex レビュー反映済の値は変更しない

---

## 🗒 c.4-c.7 で持ち越した課題（c.8 以降で対応）

1. **F2 施策実装ステータスの拡張**: 現状は Override の `target_kind="measure"` + approved/required_localization のみ。`decision_log`（DecisionRecord）と連動させるには DecisionRecord に measure_id フィールド追加が必要
2. **J2 actual_effect_jpy の自動逆算**: 現状は `actual_effect_jpy=None` で判定保留。kpi_history から「コスト削減施策なら物流コスト/売上比率の改善 × 売上」で逆算する補助関数を追加
3. **F2 bonus 拡張**: 「全必須 KPI 実装 + 月次会議定着 → +10pt」は会議出席率データが乗らないため未実装。継続運用データが揃った段階で再導入
4. **MeasureExecutionRecord の永続化**: c.7 では POST body / MCP 引数で都度受け取る形のみ。`outputs/measure_runs/<company_id>.json` で永続化する `measure_run_store.py` を c.8 と同時に整備するのが妥当

---

## 完了の定義

- 連鎖化事業者で `handling_*` KPI / `form3_section=loading` 施策が混入したら CI で fail
- Web 画面 2 件が `npm run build` 成功・実機動作確認済
- pytest 825+ 全 pass + 新規 20+ 件全 pass
- ruff check クリア
- Claude Desktop 実機 + FastAPI + Next.js の三方すべてで動作確認済
- PR を `feature/phase-5.0-chain-franchise-and-web`（または分割）で作成し、Codex の助言反映点を PR 説明に明記
- HANDOFF_NEXT_SESSION.md をフェーズ5.5（公開・記事化）向けに更新

---

## 📦 リポジトリ整理（2026-05-06）

- untracked: `docs/notebooklm/`, `docs/overview_for_review.md`, `docs/zenn_drafts/` は健一の WIP（触らない）。
