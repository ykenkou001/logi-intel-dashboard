# 営業戦略キックオフインデックス

**作成日**: 2026-05-16
**作成元**: Claude Opus 4.7 セッション（Codex × Web 調査の 3 ラウンド統合結果）
**目的**: 営業戦略の実行タスクを別セッションで継続できる形に分割し、コンテキスト節約と Codex 並行活用を両立する

---

## 戦略の核（3 行サマリ）

1. **コンサル向け OEM が直販より先**（信頼ギャップ・利益相反・意思決定スピードで有利）
2. **第一弾標的**: ロジ・ソリューション + 辻総合会計（外部発信に開かれた中堅）
3. **個人で 1 社 PoC → 既成事実化して micware に持ち込み → 認定アドバイザー型展開**（Codex 推奨ルート）

---

## なぜこの順序か（Codex × Web 調査の合意）

| 論点 | 結論 | 根拠 |
|---|---|---|
| 優先順位 | コンサル向け 70% / 社内提案 20% / 直販対応 10% | Codex 第 3 セッション結論 |
| 利益相反 | コンサル向けは荷主と直接競合せず micware と分離可 | Codex 評価 |
| 競合 | CLO 専業ベンダーは既参入だが、**CLO 計画策定 Decision Support は手薄** | Web 調査（ウイングアーク/Hacobu/ロジスティードは別ポジション） |
| 市場規模 | 3,200 社 × 平均 500 万円 = **約 160 億円/初回サイクル** | 国交省 + 物流コンサル単価相場の試算 |
| 期限 | **2026/10/31 中長期計画 初回提出期限** | 国交省ポータル |
| ベスト形態 | 完全ホワイトラベルではなく「認定アドバイザー型」（Powered by 表記残し） | freee / 弥生 PAP / SmartHR for Adviser の業界慣行 |

---

## 5 つのキックオフドキュメント

| # | ファイル | 主担当 | Codex 役割 | 想定工数 | 優先度 |
|---|---|---|---|---|---|
| 01 | `kickoff_01_check_page.md` | Claude (実装) | Tailwind/UI 補助 | 半日〜1 日 | 🔴 高 |
| 02 | `kickoff_02_zenn_article_01.md` | Claude (執筆) | 業界読者視点レビュー | 半日 | 🔴 高 |
| 03 | `kickoff_03_sales_outreach.md` | Claude (文面 + 提案書) | 文面レビュー + 業界相場 verify | 半日 | 🟠 中 |
| 04 | `kickoff_04_advisor_pricing.md` | **Codex** (リサーチ + 試算) | 主担当 | 1 日 | 🟡 中 |
| 05 | `kickoff_05_jils_route.md` | **Codex** (Web リサーチ) | 主担当 | 半日 | 🟡 低-中 |

**起動順の推奨**: 01 → 02 → 03 → 04 → 05（外部反応の入口を先に作り、営業材料を整え、ビジネスモデルを後追いで設計）

ただし 04 / 05 は Codex リサーチ主体のため、01-03 と**並行起動可能**。

---

## 別セッション起動の標準プロンプト

```
tasks/SALES_STRATEGY_KICKOFF_INDEX.md と tasks/kickoff_NN_xxx.md を読んで、当該タスクを実行してください。
Codex 委譲タイミングを判断し、必要に応じて codex:codex-rescue agent を起動してください。
```

NN を 01-05 に置き換えるだけで、別セッションが独立して走れます。

---

## 共通前提（全キックオフで参照）

### プロダクト概要
- CLO 中長期計画策定支援ダッシュボード（Python + FastAPI + MCP + Next.js + AWS）
- 業種別パッケージ（食品・化学・小売・連鎖化）+ F2 標準化スコア + J2 罠スコア
- PPT/Word/Excel 出力可、全数値に出典追跡性
- 社内レビュー URL: https://d1zei8qivkf3cr.cloudfront.net/

### CLO 義務化の重要数値（経営会議で即答用）
- 施行: **2026/4/1**
- 初年度提出期限: **2026/10/31**（次年度以降は 7 月末）
- 対象企業: 特定荷主 **約 3,200 社**（年間貨物 9 万トン以上）+ 特定倉庫 70 社 + 特定運送 790 社
- 罰則: CLO 未選任 **100 万円以下の罰金** / 届出懈怠 20 万円以下の過料
- 認知乖離: 船井総研 SC 調査では特定荷主の **42% が CLO 選任意識なし** / Hacobu 調査では 76.2% 選任済/予定

### 開発者・micware の関係（最重要制約）
- 開発者: micware 社（物流システム開発企業）の現役エンジニア、CLO アプリは**完全プライベートな個人開発**
- micware の既存顧客: CLO 対象外規模の中小荷主・物流事業者中心
- 副業申請: 未済（着手前に必須）
- 利益相反: コンサル向け OEM は荷主直販より低リスク

### 攻め先優先順位（コンサル）
- 🥇 **ロジ・ソリューション** (logi-solu.co.jp / note 発信あり)
- 🥈 **辻総合会計** (m-assets.com / CLO × 財務翻訳)
- 🥉 **船井総研サプライチェーンコンサル** (CLO 機能 MAP 保有)
- 4. ロジスティードソリューションズ（旧日立物流・大手稟議重い）
- 5. プロレド・パートナーズ（成果報酬型）
- ❌ NRI / PwC / デロイト / アクセンチュア（個人不可）

### 価格レンジ（Codex 推定）
- 初期導入費: 10-30 万円
- 月額利用料: 3-10 万円（小規模）〜 30-50 万円（中規模）
- レベニューシェア: 案件売上の 10-30%
- 認定アドバイザー加入費: 49,800 円/月〜（freee 並み）

---

## 戦略議論の流れ（背景文脈）

### セッション 1（直販向け）
- 個人開発者として直接荷主に売る案 → 与信・信頼ギャップ・利益相反で苦戦予想
- 必須準備: 副業申請・合同会社・賠償責任保険・契約書・対象判定ツール
- アプローチ序列: 紹介 > パートナーシップ > 業界団体 > インバウンド > 実証 > アウトバウンド (却下)

### セッション 2（micware 巻き込み）
- リフレーミング: 「個人プロダクト承認」ではなく「**外部規制で発生した期限付き需要を micware が取り逃がさない提案**」
- 「Zenn/note 経由問い合わせ」は直接受注ではなく**社内提案の既成事実**として価値
- 「来やすい記事」は技術型ではなく「自社は対象か」「経営会議で説明する 5 枚」型
- LinkedIn は「決裁者接触」より「外部反応ログ作り」

### セッション 3（コンサル向け OEM）← 現在の主軸
- **直販より先にコンサル向け** が Codex / Web 調査ともに合意
- ロジ・ソリューション + 辻総合会計が第一弾
- 「コンサル名差し込み + 認定アドバイザー型」が業界慣行に沿う
- 「工数 80% 削減」は実測前 NG → 「初回診断たたき台 1 日で作成」から

---

## 全タスク共通の重要な警告

1. ⚠️ **副業申請は着手前に完了**（無申告で営業しない・本業リスク + 信用失墜の二重損失）
2. ⚠️ **大手コンサル（NRI / PwC / デロイト / アクセンチュア）に最初に当たらない**
3. ⚠️ **完全ホワイトラベルにしない**（Powered by 表記必須）
4. ⚠️ **「工数 80% 削減」を実測前に言わない**（1 社 PoC で実測してから）
5. ⚠️ **初期に独占条項を結ばない**（他コンサルに売れなくなる）
6. ⚠️ **micware 巻き込み前に Hacobu 等への JV 打診はしない**（社内不信を招く）
7. ⚠️ **9-10 月の新規追加禁止**（既存 PoC の品質事故防止）
8. ⚠️ **個人開発の開示は最後**（先にデモ・実績を示してから）

---

## 各キックオフの完了後にやること

1. 各タスク完了後、本インデックスの該当行に `✅` を追記
2. 学びは `tasks/lessons.md` に `[YYYY-MM-DD] [営業戦略]` 形式で記録
3. 重要決定は `memory/` の feedback/project 系メモリに保存
4. PR ベース運用（main 直 push 禁止）。ブランチ命名は `feature/check-page` / `docs/zenn-article-01` / `docs/sales-outreach-N` 等

---

## 参考リンク

### 政府・公式
- 国交省 物流効率化法ポータル: https://www.revised-logistics-act-portal.mlit.go.jp/
- 特定事業者の指定: https://www.revised-logistics-act-portal.mlit.go.jp/designation/
- 国交省 CLO ページ: https://www.revised-logistics-act-portal.mlit.go.jp/clo/
- 中長期計画作成: https://www.revised-logistics-act-portal.mlit.go.jp/planning/
- 厚労省 副業ガイドライン: https://www.mhlw.go.jp/content/11200000/000962665.pdf
- 国税庁 インボイス制度: https://www.nta.go.jp/taxes/shiraberu/zeimokubetsu/shohi/keigenzeiritsu/invoice_about.htm

### コンサル先行 3 社（CLO 専用サービス）
- ロジスティードソリューションズ: https://www.logisteed.com/jp/news/news-release/202503272578/
- 船井総研サプライチェーンコンサル: https://prtimes.jp/main/html/rd/p/000001153.000059144.html
- ロジ・ソリューション: https://note.com/logi_solution/n/n3026f6ffae35
- 辻総合会計（会計系参入）: https://m-assets.com/lp/online/blog/shippper-logistics-cost-clo-2026

### 業界団体
- JILS ロジスティクス研究会 2026: https://www1.logistics.or.jp/newest/logiken/
- JILS 物流技術管理士: https://www1.logistics.or.jp/education/clm/
- JILS CLO 法制化対策セミナー: https://www1.logistics.or.jp/network/da02/
- 日本物流団体連合会: https://www.butsuryu.or.jp/

### 業界誌（寄稿ハードル低い順）
- 月刊マテリアルフロー: `info@mf-p.jp`（メール直送可）
- LNEWS: https://www.lnews.jp/contents/what_lnews.html （投稿メニュー）
- LOGISTICS TODAY: https://www.logi-today.com/advertising
- カーゴニュース: TEL 03-5771-2101 / https://cargo-news.co.jp/contact

### 認定アドバイザー先行モデル
- freee 認定アドバイザー（49,800 円/月〜・5,000 社超）: https://adv.freee.co.jp/advisor
- 弥生 PAP（14,000 会員）: https://www.yayoi-kk.co.jp/pap/
- マネーフォワード パートナー: https://biz.moneyforward.com/partner/
- SmartHR for Adviser: https://smarthr.jp/sr/
