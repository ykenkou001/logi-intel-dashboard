# フェーズ 5.5 α アップグレード計画

**ブランチ**: `feature/phase-5.5-alpha-upgrade`
**確定日**: 2026-05-09
**確定方法**: Claude / Codex 二者議論（CLAUDE.md §9）

---

## 確定スコープ（α 案）

「2〜3 機能に絞ってブラッシュアップ・効果大／負荷小から着手」という方針のもと、Codex 修正反映済の α 案で確定。

| # | タスク | 規模 | 7本柱への効果 |
|---|---|---|---|
| α-1 | J2 罠スコア Web画面新設 (`/dashboard/waste-traps`) | 約 400 行 | Continuous Operation + Defensibility |
| α-2 | judgment trail Web化 (`measure-eval` に Bottom 3 比較セクション追加) | +150 行 | Decision Support + Defensibility |
| α-3 | 4業種切替ナビ + グローバルナビ修正 | +120 行 | Executive Communication |

**合計 約 670 行・1.5〜2 日 / バックエンド変更ゼロ。**

---

## 二者議論サマリ

### Claude の初期推奨: A-1 + C-3

- A-1 J2 罠スコア Web画面（standardization 画面が雛形）
- C-3 4業種デモ動線ウィザード（既存 12 画面流用）
- 理由: バックエンド変更ゼロ、社内デモ準備直結

### Codex の評価（採用 / 修正のうえ採用 / 却下）

- **修正のうえ採用**
- A-1 採用。C-3 単独は弱い（印象だけで提出・継続運用への寄与が薄い）
- 最大効果は計画案 C（Executive Communication + Defensibility）
- B-1 (kpi_history 自動逆算) は **Phase 6 defer 妥当** — 計算根拠の意味づけ・出典・監査可能性を詰めずに「もっともらしい金額」を出すと defensibility を損なう

### Codex 対案: α 案

- A-1 + C-2 + C-3 縮小版
- 「罠を見せる → なぜ判断したかを示す → 4業種切替ナビに留める」

### Codex の盲点指摘（採用）

> 現行グローバルナビには industry-package / standardization / waste-trap が出ておらず、画面を増やしても **導線設計を直さないとデモで発見されない**。

→ 検証済（[web/app/layout.tsx:25-31](../web/app/layout.tsx#L25-L31)）。グローバルナビは 5 項目のみで cockpit / industry-package / standardization が掲載されていない。α-3 にナビ修正を追加。

---

## 着手しない / 後回しにするもの

| 項目 | 扱い | 理由 |
|---|---|---|
| B-1 `actual_effect_jpy` 自動逆算 | Phase 6 defer | kpi_history のセマンティクス未確定。対象 KPI 限定+計算根拠+出典+欠損時挙動+テストをセットで入れる必要がある |
| B-2 罠検出履歴の時系列保存 | Phase 6 で B-1 と一緒 | B-1 が前提 |
| B-3 outputs ファイル一覧 Web | 別 PR で検討 | 単独で価値はあるが今回のテーマからは外れる |
| C-1 F2 × J2 統合 1枚 PPT | 別 PR で検討 | デザイン整合性確認が必要（[docs/ppt_design.md](../docs/ppt_design.md)） |

---

## 実装方針

### α-1: J2 罠スコア Web画面

- ファイル: `web/app/dashboard/waste-traps/page.tsx` 新規
- 雛形: [web/app/dashboard/standardization/page.tsx](../web/app/dashboard/standardization/page.tsx)（442 行）
- API 流用: 既存 `/api/v1/clo/waste-traps/{id}` エンドポイント + `web/lib/api.ts` の `fetchWasteTraps()` 想定
- 表示要素:
  - severity 別件数（high / medium / low / freeze）の上部サマリ
  - 1 件ずつのカード: measure_name / invested_jpy / expected / actual / months_since_start / safeguard_triggered / suggested_remediation / investment_freeze_recommended
  - severity による色分け（high=赤 / medium=黄 / low=緑）
  - safeguard_triggered の日本語表示（ramp_up_period → 「立ち上げ期間中」等）
- 入力: 業種パッケージ画面と同じく `company_id` クエリ + サンプル 4 業種ボタン

### α-2: judgment trail Web化

- ファイル: [web/app/dashboard/measure-eval/page.tsx](../web/app/dashboard/measure-eval/page.tsx) 拡張（95 → 約 245 行）
- 既存 `MeasureEvalResult` には Bottom 3 が出力済（[core/analytics/measure_eval.py](../core/analytics/measure_eval.py) 短期 3 で実装）
- 追加表示:
  - Top 3 / Bottom 3 の対比表（横に並べる）
  - 各 Bottom 3 に「不採用理由」「Top と比べての劣位ポイント」
  - 各 Top 3 に short fields（responsible_dept / monthly_kpi / dependencies）が既にあれば表示
- API 変更不要（既存レスポンスの未表示フィールドを引き出すだけ）

### α-3: グローバルナビ修正 + 4業種切替ナビ

- グローバルナビ修正: [web/app/layout.tsx:25-31](../web/app/layout.tsx#L25-L31)
  - 追加: `cockpit` / `industry-package` / `standardization` / `waste-traps`
  - 5 項目 → 8〜9 項目（モバイルでもスクロールで見える形で）
- 4業種切替ナビ:
  - 各分析画面の上部に共通の「4 業種サンプル切替」コンポーネント
  - `web/components/CompanySwitcher.tsx` を新規作成し、industry-package / standardization / waste-traps / cockpit / measure-eval / scenario-sim / plan-draft で使い回す
  - クエリパラメータ `?company_id=sample_mfg_01` で永続化、ボタンクリックで navigate

---

## 検証手順

1. `uv run ruff check core/ api/ mcp_server/` （Python は今回触らない想定だが念のため）
2. `cd web && npm run lint` / `npm run build`（Next.js build pass を確認）
3. `pwsh scripts/dev_api.ps1` + `pwsh scripts/dev_web.ps1` でローカル起動
4. 4 業種サンプル全部で α-1 / α-2 / α-3 を手動確認
5. グローバルナビから 8 画面以上にアクセスできるか確認

---

## CLAUDE.md §1.5 整合性チェック

- ✅ Decision Support: α-2 で「なぜそれを選んだか」即答可能に
- ✅ Compliance Assurance: 既存ロジック温存（フェーズ5.0 数値を変更しない）
- ✅ Continuous Operation: α-1 で罠を画面化し継続監視可能に
- ✅ Executive Communication: α-3 ナビ修正で経営層が直接アクセス可能に
- ✅ Defensibility: α-1 + α-2 で「数字の根拠」と「判断の根拠」を可視化
- ✅ 「やらないこと」リスト遵守: PPT/Word/Excel ファイル出力には触らず、core 数値も変更しない

---

## ロールバック計画

各 α-N を独立コミットで積む。問題発覚時は対応コミットだけ revert すれば残りは活きる。
最悪ブランチごと破棄しても main に影響なし（feature ブランチ + PR 経由のため）。
