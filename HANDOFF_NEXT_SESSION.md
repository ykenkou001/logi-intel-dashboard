# 次セッションへの引継ぎ（2026-05-06 時点）

> このファイルを最初に読み、`uv sync` 実行後にフェーズ5.5（公開・記事化）に着手する。

---

## 🎯 次セッションのタスク: フェーズ5.5 — 公開・記事化

### 全体像

**フェーズ5.0（段階 c 業種別 CLO 標準パッケージ + F2/J2 スコア）は完了**（c.1-c.9 全達成）。
次は最終フェーズ **5.5 公開・記事化** で、本プロダクトを社内・社外に届ける段階。

`docs/roadmap.md` §フェーズ5.5 の TODO は以下:

- [ ] **README 整備** — 現行 README の更新 + 主要機能の Quick Start 化
- [ ] **Zenn 記事執筆** — 開発過程・設計判断・Codex 協業実績を技術記事化
- [ ] **社内デモ** — 営業・企画・経営層向けに動作デモを実施
- [ ] **（任意）Public 化、PyPI 公開**

### フェーズ5.0 完了の確認

| PR | 内容 | テスト |
|---|---|---|
| #11 | c.1-c.3 IndustryPackage 基盤 | +88 件 |
| #13 | c.4 既存資産接続検証 + c.5/c.6 F2 / J2 スコア | +73 件 |
| #15 | c.7 業種別パッケージ + F2/J2 を MCP/REST 公開 | +21 件 |
| #16 (本セッションでマージ予定) | c.8 連鎖化強制ガード + c.9 Web 2 画面 + 統合テスト | +22 件 |

**最終 pytest 結果**: 826 件全 pass / ruff クリーン / Next.js build 全 16 ページ pass

---

## 📋 必読ドキュメント（着手前）

1. **CLAUDE.md** — プロジェクト全体方針。特に §1.5 ミッション宣言 / §6.5 dev サーバ起動ルール / §7 検証ルール / §9 Codex 協業方針
2. **docs/roadmap.md §フェーズ5.5** — 公開・記事化の TODO リスト
3. **README.md**（リポジトリ ルート）— 現状の説明範囲を確認し、フェーズ5.0 で追加された機能を反映する
4. **docs/zenn_drafts/**（健一の WIP）— 既存ドラフトがあるか確認してから着手する。健一の方針に合わせて執筆する

---

## ⚠️ 並行作業の注意

- 健一は **Claude / Codex を別セッションで並行起動** することがある。本セッション開始前に「Codex 並行作業はあるか？」を確認する
- 公開・記事化フェーズでは衝突可能性は低いが、`docs/zenn_drafts/` / `README.md` は両者が触りうるため、着手前に方針を確認する
- **`main` への直接 push は禁止**。必ず feature ブランチ（`feature/phase-5.5-...` / `docs/...`）+ PR 経由

---

## 🛠 推奨アクション

### 1. README 整備

現状の README は フェーズ4.0 までの内容に止まっている可能性が高い。以下を反映:

- **フェーズ4.5 J3 デイリーコックピット** — `/dashboard/cockpit` Web / `logi_clo_today_decisions` MCP
- **フェーズ5.0 業種別 CLO 標準パッケージ** — 4 業種マトリクス + F2/J2 スコア + Web 2 画面
- **MCP ツール一覧** — 現状提供している全ツール（c.7 で 3 件追加済）
- **REST エンドポイント一覧** — 同上
- **Web ダッシュボード機能** — トップ画面の FEATURES と整合させる
- Quick Start: `git clone` → `uv sync` → `pwsh scripts/dev_api.ps1` + `pwsh scripts/dev_web.ps1`

### 2. Zenn 記事執筆

健一の WIP（`docs/zenn_drafts/`）を確認してから書く。書きたい候補:

- **「Claude Code で CLO 計画策定支援アプリを作る — 設計・Codex 協業の記録」**
- **「物流効率化法 第46条/第65条 をコードで遵守する — 業種別 CLO 標準パッケージの実装」**
- **「F2 標準化スコア × J2 罠スコア — Codex 勧告で誤検知を抑える」**
- 各記事に出典 URL（e-Stat / 物流効率化法ポータル / JILS）を必ず付ける

### 3. 社内デモ準備

- AWS PoC 環境（https://d1zei8qivkf3cr.cloudfront.net/）が稼働中なので、デモ可能
- 4 業種サンプル profile（sample_mfg_01 / sample_wholesale_01 / sample_retail_01 / sample_chain_01）でストーリー組立
- デモ動線案:
  1. ホーム画面 → 業種別 CLO 標準パッケージ → F2 標準化スコア → コックピット → 計画書ドラフト生成
  2. 「経営会議で説明できる数字」が出ること、出典 URL が踏めることを必ず見せる

---

## 🚫 触らないこと

- フェーズ5.0 で確定した core ロジックの数値・閾値（積載率 44% / F2 -5pt / J2 6 軸セーフガード等）
- 4 業種パッケージの KPI target_value（Codex レビュー反映済の値は変更しない）
- `core/playbook/industry_packages.py` の `_CHAIN_FRANCHISE_PACKAGE`（c.8 強制ガードで保護されているが、KPI / measure 追加時は必ず `validate_chain_franchise_constraints()` で確認）

---

## 🗒 c.5/c.6 + c.7 + c.8 の持ち越し課題（フェーズ5.5 以降の改善 PR で対応予定）

1. **F2 施策実装ステータスの拡張** — `decision_log` 連動（DecisionRecord に measure_id フィールド追加が必要）
2. **J2 actual_effect_jpy の自動逆算** — kpi_history から「コスト削減施策なら物流コスト/売上比率の改善 × 売上」で逆算する補助関数
3. **F2 bonus 拡張** — 「全必須 KPI 実装 + 月次会議定着 → +10pt」は会議出席率データが乗らないため未実装
4. **MeasureExecutionRecord の永続化** — `outputs/measure_runs/<company_id>.json` で永続化する `measure_run_store.py`

これらはフェーズ5.5 中に「リアルな運用データが乗ってきたタイミング」で再着手する候補。

---

## 完了の定義（フェーズ5.5）

- README が現状機能を網羅し、新規来訪者が 10 分以内に Quick Start できる
- Zenn 記事 1 本以上が公開されている（または社内 Confluence 等に掲載）
- 社内デモを実施し、営業・企画・経営層からのフィードバックが集まっている
- HANDOFF_NEXT_SESSION.md がフェーズ6 以降（あれば）に更新されている

---

## 📦 リポジトリ整理（2026-05-06）

- untracked: `docs/notebooklm/`, `docs/overview_for_review.md`, `docs/zenn_drafts/` は健一の WIP。フェーズ5.5 で活用する候補。
