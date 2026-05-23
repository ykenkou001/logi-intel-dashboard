# 次セッションへの引継ぎ（2026-05-23 時点）

> このファイルを最初に読み、`uv sync` 実行後にフェーズ5.5 残タスク（公開・記事化）に着手する。

---

## フェーズ5.5 Tier S 進捗（2026-05-23）

| Tier | タスク | PR | 状態 |
|---|---|---|---|
| S1 | DecisionLog 永続化 | #53 | ✅ マージ済 |
| **S2** | **KPI 時系列トラッキング** | **本ブランチ feat/tier-s2-kpi-timeseries** | **✅ 実装完了・PR 化予定** |
| S3 | 報告単位 Facility 管理 | #50 / #51 / #52 | ✅ マージ済 |
| S4 | 罰則・社名公表リスク PPT | #49 | ✅ マージ済 |
| S5 | README Decision Support 軸再編集 | #48 | ✅ マージ済 |

**Tier S 5 件すべて達成**。残るは記事化（Zenn）/ 社内デモ / Codex 二次調査（寄託先関連の条文出典）/ AWS terraform apply。

---

## Tier S2 で追加したファイル（フェーズ5.5 / 本セッション）

- `core/io/kpi_timeseries_store.py` — 月次スナップショット永続化（jsonl + S3 backend）
- `core/analytics/kpi_timeseries.py` — 日次→月次ロールアップ + 悪化検出
- `api/routers/clo.py` — GET/POST `/kpi-timeseries/{company_id}`
- `mcp_server/tools/clo_tools.py` — `logi_clo_kpi_timeseries` / `logi_clo_record_monthly_snapshot`
- `web/app/dashboard/kpi-timeseries/page.tsx` — 月次推移 LineChart + 悪化アラート + 一覧表
- `web/components/KpiTimeseriesChart.tsx` — Recharts ベースの 5 系列折れ線
- `web/lib/api.ts` / `web/lib/labels.ts` — 型 + severity ラベル追加
- `web/app/layout.tsx` — ナビに「月次推移」追加
- `tests/io/test_kpi_timeseries_store.py`（11 件）
- `tests/core/test_kpi_timeseries_analytics.py`（13 件）
- `tests/api/test_clo_router.py` に E2E 4 件追加
- `plans/tier_s2_kpi_timeseries.md` 起案

pytest 1022 件全 pass / ruff pass / Next.js build 全 20 ページ pass。

---

## 並列セッション運用記録（2026-05-17〜・全完了）

| セッション | タスク | worktree | ブランチ | 主担当ファイル | PR / 状態 |
|---|---|---|---|---|---|
| A | Tier S1 DecisionLog | ../logi-intel-dashboard.decision-log | docs/decision-log-store | core/io/decision_log_store.py | ✅ #53 マージ済 |
| B | Tier S3 Facility | ../logi-intel-dashboard.facility-store | docs/facility-store | core/io/facility_store.py | ✅ #50, #51, #52 マージ済 |
| C | Tier S4 罰則 PPT | ../logi-intel-dashboard.compliance-risk | docs/compliance-risk-ppt | core/export/ppt_writer.py | ✅ #49 マージ済 |

共通の追記領域（mcp_server/tools/clo_tools.py / api/routers/clo.py / web/lib/api.ts）
は PR マージ順に rebase で吸収済み。Tier S2 もこのファイル群を拡張している。

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

### #0 [✅ 完了] MeasureExecutionRecord 永続化（2026-05-06）

- `core/io/measure_run_store.py` 新規作成（save / load / append / merge_with_stored）
- `MeasureExecutionRecord` / `RootCause` / `TrapSeverity` を `core/io/` に昇格（`waste_trap.py` で re-export し後方互換維持）
- REST `POST /waste-traps/{id}` + MCP `logi_clo_waste_traps` で incoming を永続化 & stored と merge
- `tests/io/test_measure_run_store.py` 10 件新規 / `tests/conftest.py` cleanup fixture 追加
- pytest 845 件全 pass（+11 件）

### #1 [✅ 完了] AWS 運用ハーデニング（2026-05-06）

`infra/main.tf` に以下を追加（**要 `terraform apply`**）:
- CloudWatch Logs 保管期間: 7 日 → 30 日
- Lambda エラー率アラーム（5 分で 5 件超 → SNS → `ykenkou001@gmail.com`）
- Lambda p95 レイテンシアラーム（p95 > 20s）
- Budget アラート（月 $50 の 80%/100% 超でメール通知）
- 公開範囲確認済み（S3/CloudFront/API GW すべて OK）、SSM 経由のシークレット管理確認済み
- `docs/aws_migration_plan.md` §9 にロールバック手順 + セキュリティチェック結果を追記

**次セッション開始時に `cd infra && terraform apply -var="env=dev"` を実行してアラートを有効化する。**
SNS サブスクリプション確認メールが届いたら "Confirm subscription" をクリックすること。

### #1.5 [✅ 完了] Tier S2 KPI 時系列トラッキング v1.0（2026-05-23 / PR #55）

`core/io/kpi_timeseries_store.py` + `core/analytics/kpi_timeseries.py` を新設し、
月次粒度の KPI 推移と悪化アラートを Web / REST / MCP 経由で取得可能に。
詳細は [plans/tier_s2_kpi_timeseries.md](plans/tier_s2_kpi_timeseries.md) を参照。

### #1.6 [✅ 完了] Tier S2 v1.1 物流コスト比率 + 業界平均（2026-05-23）

Codex 独立評価（plans/tier_s2_kpi_timeseries_codex_review.md）の観点 ③ / ⑤ / ⑥ を反映:
- `logistics_cost_ratio` フィールド追加（JILS 2021 業種別平均と比較）
- baseline 由来（3 ヶ月前比 / 最古比）を UI バッジ表示
- 業種別水準差を吸収する**相対率閾値**採用
- `profile.kpi_history` の `logistics_cost_revenue_ratio_pct` を fallback ソースとして取込

v1.2 候補（別 PR）: 計画値線（target_proposal / plan_draft_freeze 由来の線形補間 vs 月次入力）。
Phase 6 候補: Excel `kpi_history_monthly` シート追加（後方互換テスト大のため別 PR）。

### #1.7 [✅ 完了] Tier S3 寄託先 citation 登録（2026-05-23）

Codex 二次調査（docs/facility_citation_research.md）の確定値を反映:
- `form5_iv4_iv5_consigned_citation()`（経産省 PDF / 様式第5 IV-4/IV-5）新規追加
- `mlit_shipper_handbook_consigned_citation()`（国交省 特定荷主手引書 第1.1版）新規追加
- `logistics_efficiency_law_article57_citation()`（e-Gov / 特定倉庫業者の定期報告）新規追加
- `improvement_standards_notice_pdf_citation()`（厚労省 PDF 一次資料）新規追加
- `wait_time_heatmap.py` で寄託先 facility 集計時に上記 IV-4/IV-5 + 手引書 citation を自動付与
- 既存 `article46/65/66` / `improvement_standards` の URL は破壊しない（テスト・フィクスチャ依存のため）
- **登録しなかったもの**（推測値）: 「3-5-3」「測定実施者」「責任主体」「自社直接計測外」を公式定型語として扱う citation

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
