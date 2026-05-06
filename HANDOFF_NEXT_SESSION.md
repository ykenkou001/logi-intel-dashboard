# 次セッションへの引継ぎ（2026-05-06 時点）

> このファイルを最初に読み、`uv sync` 実行後にフェーズ5.5（公開・記事化）に着手する。

---

## 🎯 次セッションのタスク: フェーズ5.5 — 公開・記事化

### 全体像

**フェーズ5.0（段階 c 業種別 CLO 標準パッケージ + F2/J2 スコア）は完了**（c.1-c.9 全達成 / Codex 独立評価で「条件付き完了 → docs 整備で完了確定」）。
次は最終フェーズ **5.5 公開・記事化** + **運用ハーデニング**。

### フェーズ5.0 完了の粒度（Codex 評価 2026-05-06 反映）

完了したのは **「業種別 CLO 標準パッケージ + F2/J2 スコアの機能基盤」** であり、**「法令提出を完全保証」ではない**。フェーズ5.5 で公開・社外発信する際は以下の表現に留める:

✅ OK: 「産業別パッケージ・F2 標準化スコア・J2 罠スコアの基盤公開」「中長期計画策定の支援ツール」
❌ NG: 「法令提出を完全保証」「全ての CLO 業務を自動化」「コンサル代行」

詳細 → [docs/roadmap.md](docs/roadmap.md) §フェーズ5.0 完了の粒度

---

## 🚦 フェーズ5.5 タスク優先順位（Codex 勧告反映）

### #0 [最優先] MeasureExecutionRecord 永続化（昇格課題）

Codex 勧告:「**継続運用と監査証跡に直結。2026年10月31日の中長期計画提出支援では『誰が、いつ、どの施策を実行・見直したか』が弱いと実務導入で詰まる**」

実装内容:
- `core/io/measure_run_store.py` 新規 — `outputs/measure_runs/<company_id>.json` で施策実行記録を永続化（save / load / append）
- `MeasureExecutionRecord` を `core/analytics/waste_trap.py` から共通モデル層に昇格させるか、`core/io/` 配下に移動して循環 import を回避
- POST body / MCP 引数で受け取った run を保存し、`logi_clo_waste_traps` を呼ぶ際に永続化済みデータと merge できるようにする
- 永続化テスト 5-10 件追加（save/load round-trip / append / 同 measure_id 複数回 / company_id 分離）

**フェーズ5.5 着手の最初の PR としてこれをやる**。記事化・README 整備より先。

### #1 [高] AWS 運用ハーデニング（Codex 指摘 ③）

公開前に最低限揃える:

- [ ] CloudWatch Logs の保管期間（現状デフォルト = 永久。30 日 or 90 日に短縮してコスト圧迫回避）
- [ ] Lambda のエラー率アラート（5% 超で SNS → 健一のメール）
- [ ] Lambda のレイテンシアラート（p95 > 5s 等）
- [ ] CloudFront / Lambda のコスト急増アラート（Cost Anomaly Detection or Budget アラート $50/月で通知）
- [ ] 公開範囲確認（CloudFront ディストリビューション / API Gateway / S3 バケットすべて意図した公開範囲か）
- [ ] APIキー秘匿（e-Stat appId 等が Lambda 環境変数に直接書かれていないか、SSM Parameter Store 経由か再確認）
- [ ] 障害時ロールバック手順を `docs/aws_migration_plan.md` に追記（`aws lambda update-function-code --revision-id` で前リビジョンに戻す等）

### #2 README 整備

- フェーズ4.5 J3 デイリーコックピット
- フェーズ5.0 業種別 CLO 標準パッケージ + F2/J2 スコア
- MCP / REST / Web の 3 経路一覧
- Quick Start: `git clone` → `uv sync` → `pwsh scripts/dev_api.ps1` + `pwsh scripts/dev_web.ps1`

### #3 Zenn 記事執筆

健一の WIP（`docs/zenn_drafts/`）を確認してから書く。**過大なコンプライアンス保証表現を避ける**（Codex ④ ⑤）。候補:
- 「Claude Code で CLO 計画策定支援アプリを作る — 設計・Codex 協業の記録」
- 「物流効率化法 第46条/第65条 をコードで遵守する — 業種別 CLO 標準パッケージの実装」
- 「F2 標準化スコア × J2 罠スコア — Codex 勧告で誤検知を抑える」

### #4 社内デモ準備

- AWS PoC（https://d1zei8qivkf3cr.cloudfront.net/）でデモ可能
- 4 業種サンプル profile（sample_mfg_01 / sample_wholesale_01 / sample_retail_01 / sample_chain_01）でストーリー組立
- デモ動線案: ホーム → 業種別 CLO 標準パッケージ → F2 標準化スコア → コックピット → 計画書ドラフト生成
- 「経営会議で説明できる数字」が出ること、出典 URL が踏めることを必ず見せる

### #5 [任意] Public 化、PyPI 公開

---

## 📋 必読ドキュメント（着手前）

1. **CLAUDE.md** — プロジェクト全体方針。特に §1.5 ミッション宣言 / §6.5 dev サーバ起動ルール / §7 検証ルール / §9 Codex 協業方針
2. **docs/roadmap.md §フェーズ5.0 完了の粒度** — 公開時に避けるべき表現と完成範囲の明文化
3. **docs/roadmap.md §フェーズ5.5** — 公開・記事化の TODO リスト
4. **docs/aws_migration_plan.md** — AWS 構成と運用ハーデニング着手時の参照
5. **README.md**（リポジトリ ルート）— 現状の説明範囲を確認し、フェーズ4.5 + 5.0 で追加された機能を反映する
6. **docs/zenn_drafts/**（健一の WIP）— 既存ドラフトがあるか確認してから着手する

---

## ⚠️ 並行作業の注意

- 健一は **Claude / Codex を別セッションで並行起動** することがある。本セッション開始前に「Codex 並行作業はあるか？」を確認する
- 公開・記事化フェーズでは衝突可能性は低いが、`docs/zenn_drafts/` / `README.md` は両者が触りうるため、着手前に方針を確認する
- **`main` への直接 push は禁止**。必ず feature ブランチ + PR 経由

---

## 🚫 触らないこと

- フェーズ5.0 で確定した core ロジックの数値・閾値（積載率 44% / F2 -5pt / J2 6 軸セーフガード等）
- 4 業種パッケージの KPI target_value（Codex レビュー反映済の値は変更しない）
- `core/playbook/industry_packages.py` の `_CHAIN_FRANCHISE_PACKAGE`（c.8 強制ガードで保護されているが、KPI / measure 追加時は必ず `validate_chain_franchise_constraints()` で確認）

---

## 🗒 c.5/c.6 + c.7 + c.8 の持ち越し課題

| # | 課題 | フェーズ5.5 での扱い |
|---|---|---|
| 0 | **MeasureExecutionRecord の永続化** | **#0 最優先（Codex 勧告で昇格）** |
| 1 | F2 施策実装ステータスの拡張（`decision_log` 連動） | リアルな運用データが揃った段階で再着手 |
| 2 | J2 `actual_effect_jpy` の自動逆算 | kpi_history と紐付ける形で Phase 5.5 後半 |
| 3 | F2 bonus 拡張（必須 KPI 全実装 + 月次会議定着） | 会議出席率データが乗った段階で再導入 |

---

## 完了の定義（フェーズ5.5）

- README が現状機能を網羅し、新規来訪者が 10 分以内に Quick Start できる
- Zenn 記事 1 本以上が公開されている（または社内 Confluence 等に掲載）
- 社内デモを実施し、営業・企画・経営層からのフィードバックが集まっている
- **MeasureExecutionRecord 永続化が完成し、施策実行履歴が monitor できる**
- **AWS 監視・コストアラート・ロールバック手順が整備されている**
- HANDOFF_NEXT_SESSION.md がフェーズ6 以降（あれば）に更新されている

---

## 📦 リポジトリ整理（2026-05-06）

- untracked: `docs/notebooklm/`, `docs/overview_for_review.md`, `docs/zenn_drafts/` は健一の WIP。フェーズ5.5 で活用する候補。
- `.gitignore` の `.mcp.json` 追加分は別途 PR で対応 or 健一が個別コミット予定。
