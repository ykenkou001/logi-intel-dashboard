# 成果物フォーマット 棲み分けガイド

CLO 中長期計画書ドラフト等の成果物は、**1 回の生成で 5 種類のファイル**を同時出力する（フェーズ 5.5 β-3a 以降）。
本ドキュメントは「どの場面でどのファイルを使うか」を CLO 業務観点で明文化する。

## CLAUDE.md §1.5 ミッション宣言との対応

> 経営会議で使える成果物を出すこと — 会話画面で完結させない。**PPT（最優先）/ PDF / Excel / Markdown** をファイルとして出力できること

β-3a で **HTML を併設** することにより、`PPT / Word / Excel / HTML / MD` の 5 形態に拡張した。MD は廃止せず、再編集と差分確認の中継フォーマットとして残す。

## 5 つの役割分担

| # | フォーマット | 主な利用シーン | 強み | writer |
|---|---|---|---|---|
| 1 | **PPT (.pptx)** | 経営会議の投影・口頭説明 | 大型 KPI / 視覚インパクト / 会議の進行制御 | `core/export/ppt_writer.py` |
| 2 | **Word (.docx)** | 国交省提出（様式第3別紙） | 法定様式準拠 / 印鑑欄 / e-Gov 対応 | `core/export/docx_form3_writer.py` |
| 3 | **Excel (.xlsx)** | 数値検証・出典確認・KPI 推移 | セル単位の計算検証 / 出典シート | `core/export/excel_writer.py` |
| 4 | **HTML (.html)** | 詳細閲覧・印刷・社内共有 | ダブルクリックで開ける / Ctrl+P で PDF 化 / リンク clickable | `core/export/html_writer.py` |
| 5 | **Markdown (.md)** | 人間レビュー・再編集・AI 反復 | 差分確認 / NotebookLM 取込 / Claude との再編集 | `core/export/markdown_writer.py` |

## 利用シーン別の意思決定マトリクス

| 場面 | 第一選択 | 第二選択 |
|---|---|---|
| 経営会議で投影しながら説明する | **PPT** | — |
| 国交省 e-Gov へ提出する | **Word** | — |
| 数値の妥当性を 1 セルずつ確認する | **Excel** | — |
| 役員に事前メールで送る（添付して読んでおいてもらう） | **HTML** | PPT |
| 印刷して紙の資料として配布する | **HTML**（Ctrl+P → PDF） | Word |
| Claude に「ここをこう修正して」と依頼する | **Markdown** | — |
| NotebookLM に取り込んで Q&A させる | **Markdown** | — |
| 社内 Slack / Teams に貼り付けて議論する | **Markdown** | HTML |
| 法令更新時に変更履歴を git diff で見る | **Markdown** | — |

## 設計原則（β-3a 確定事項）

1. **MD と HTML は同じ素材から生成する** — `_build_markdown_sections()` の `(見出し, 本文)` リストを両 writer が共有
2. **HTML は self-contained** — 外部 CSS / JS への参照なし。社内メール添付で誰でも開ける
3. **HTML は print-friendly** — `@media print` で Ctrl+P → PDF 化したときも体裁が崩れない
4. **HTML のデザイントークンは [DESIGN.md](../DESIGN.md) と同期** — ネイビー (#1E2761) + アンバー (#F5B82E) のブランド統一
5. **出典 URL は HTML で必ず clickable** — `<a target="_blank">` / Defensibility（CLAUDE.md §1.5 必達 7 本柱 #7）担保
6. **MD は廃止しない** — 再編集・差分確認・AI 反復のフォーマットとして役割が明確

## β-3a 適用範囲（フェーズ 5.5）

| ツール | HTML 同梱 | 備考 |
|---|---|---|
| `logi_clo_plan_draft` | ✅ | β-3a で実装（中長期計画書ドラフト） |
| `logi_clo_periodic_report_draft` | 未対応 | β-3b 以降で検討（Word が法定様式なので優先度低） |
| `logi_clo_industry_package` 等 | 未対応 | Web 画面で十分。HTML 同梱は CLO 業務価値次第で判断 |

> **β-3b 以降の判断基準**: その成果物を「経営層が机に持ち帰って読み込む」用途があるかどうか。会議内で完結する診断系（waste-traps, today-decisions 等）は HTML 化の必要性が低い。

## 将来拡張（β-3b 以降）

- HTML 利用ログを取って「実際にダウンロードされている割合」を計測 → MD deprecation の判断材料に
- `logi_clo_periodic_report_draft` への HTML 同梱（様式第5 の社内レビュー版）
- HTML から PDF への自動変換（`weasyprint` / `playwright` 等）— 現状は Ctrl+P で代替

## 参考

- [DESIGN.md](../DESIGN.md): デザイントークン定義
- [docs/ppt_design.md](ppt_design.md): PPT 専用のレイアウト方針
- [plans/phase-5.5-beta-fixes.md](../plans/phase-5.5-beta-fixes.md): β-3 の意思決定経緯（Codex 独立評価込み）
