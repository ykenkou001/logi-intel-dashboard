# キックオフ 01: 対象企業判定チェックリスト `/check` Web 画面実装

**親ドキュメント**: `tasks/SALES_STRATEGY_KICKOFF_INDEX.md`（共通前提を含む）
**主担当**: Claude (実装)
**Codex 役割**: Tailwind/UI 補助（必要時）
**想定工数**: 半日〜1 日
**優先度**: 🔴 高

---

## ゴール

既存ダッシュボード `web/` 配下に **`/check` 画面**を追加し、ブラウザで「CLO 義務対象判定」が **30 秒で完了**する入口を作る。

## 戦略上の役割

- **外部反応の入口**: Zenn 記事 → `/check` → サンプル PDF DL → コンタクト
- **SEO 流入受け皿**: 「CLO 義務 対象」「特定荷主 判定」等のキーワード狙い
- **社内提案の既成事実**: 「外部からアクセスがある」既成事実化（PV/DL/メアド収集）
- **コンサル向け営業の補助**: 「貴社の顧客にもこのページを送れます」と提案

---

## 機能要件

### MUST（必須）
1. **判定質問 6-8 項目**
   - 業種（食品・化学・小売・連鎖化フランチャイズ・運送・倉庫・その他）
   - 年間取扱貨物トン数（< 1 万 / 1-5 万 / 5-9 万 / 9 万以上 / 不明）
   - 保有車両台数（< 50 / 50-150 / 150 以上 / 該当なし）
   - 営業倉庫の年間入庫貨物トン数（< 10 万 / 10-70 万 / 70 万以上 / 該当なし）
   - 売上高（参考表示用・必須ではない）
   - 物流統括責任者の選任状況（既選任 / 選任予定 / 未検討）

2. **判定ロジック**（3 区分）
   - **特定荷主・特定連鎖化事業者**: 年間貨物 9 万トン以上 → 約 3,200 社該当
   - **特定倉庫業者**: 年間保管 70 万トン以上 → 約 70 社該当
   - **特定貨物自動車運送事業者等**: 保有車両 150 台以上 → 約 790 社該当
   - 複数該当の場合は全て表示

3. **判定結果の表示**
   - 「対象」「対象外」「グレーゾーン（要詳細確認）」の 3 段階
   - 該当した法令条文の引用 + 国交省出典 URL
   - 罰則情報（100 万円以下の罰金 / 届出懈怠 20 万円以下）
   - 残り日数カウントダウン（2026/10/31 までの日数）

4. **次のアクション動線**
   - 業種別パッケージサンプル PDF DL（食品・化学・小売・連鎖化）
   - メアド任意入力 + 「個別相談」コンタクトフォーム
   - 結果シェア用 URL 生成（クエリパラメータ encode 方式・SNS シェアボタン）

### SHOULD（推奨）
- アクセス解析（GA4 or Plausible）
- 「あなたと同じ業種で対象になった企業の数」表示（業種別 KPI 接続）
- スマホレスポンシブ
- LP 風の OG image（SNS シェア時用）

### NICE TO HAVE
- PDF 形式での判定結果保存
- LINE で結果送信
- メアド入力者への定期メルマガ送付（無料 CLO ニュース）

---

## 非機能要件

- ログイン不要（最大限フリクション削減）
- 個人情報取扱規程準拠（メアド任意・SSL・削除リクエスト可）
- レート制限（1 IP あたり 100 req/h）

---

## 既存実装の参照ポイント

実装開始時に最初に確認すべきファイル:

- `web/app/` 配下の既存画面（dashboard/, industry-package/, standardization/ 等のパターンを踏襲）
- `web/lib/api.ts` の型定義（Pydantic スキーマと完全一致する 18 型）
- `web/components/` の共通コンポーネント
- `core/playbook/industry_packages.py`（4 業種の定義）
- `core/clo/eligibility.py`（既存の `logi_clo_eligibility` ツールの判定ロジックが流用可能か確認）
- `app/routers/clo.py`（REST エンドポイントの追加方針）
- `docs/dashboard_feature_guide.md`（既存画面のドキュメント規約）

---

## 判定ロジックの根拠（コード内コメントに必須）

```
特定荷主・特定連鎖化事業者: 年間貨物 9 万トン以上（上位約 3,200 社）
特定倉庫業者: 年間保管 70 万トン以上（上位約 70 社）
特定貨物自動車運送事業者等: 保有車両 150 台以上（上位約 790 社）
罰則: CLO 未選任 100 万円以下の罰金 / 届出懈怠 20 万円以下の過料
出典: 国交省ポータル https://www.revised-logistics-act-portal.mlit.go.jp/designation/
施行日: 2026-04-01 / 初回計画提出期限: 2026-10-31
```

---

## 実装ステップ案

1. **ブランチ作成**: `feature/check-page`
2. **既存 eligibility ツール調査**: `core/clo/eligibility.py` 等が既にあれば流用、なければ新規
3. **判定ロジック実装**: `core/eligibility/check.py`（純粋関数 + 型定義）
4. **REST エンドポイント**: `app/routers/eligibility.py` に `POST /api/v1/check` を追加
5. **Next.js 画面**: `web/app/check/page.tsx` 作成（質問フォーム → 結果表示の 2 ステップ）
6. **判定結果コンポーネント**: `web/components/check/Result.tsx`（業種別 PDF DL リンク + シェア URL）
7. **メアド入力フォーム**: 既存のコンタクト API があれば流用、なければ簡易版作成
8. **OG image 生成**: 静的画像 or Vercel OG
9. **テスト**: `tests/api/test_check.py` で 4 業種 × 3 区分 = 12 シナリオの判定確認
10. **Lint + Type check**: `uv run ruff check` + `uv run mypy` + Next.js build
11. **ローカル確認**: `pwsh scripts/dev_api.ps1` + `pwsh scripts/dev_web.ps1` で `/check` 表示
12. **PR 作成**: タイトル `feat(check): 対象企業判定チェックリスト /check 画面を追加`

---

## 成功基準

- ✅ `/check` がローカル + AWS デプロイ後の社内レビュー URL で表示
- ✅ 4 業種 × 3 区分の判定が法律閾値通り
- ✅ メアド入力でコンタクト DB に保存される（任意入力）
- ✅ サンプル PDF DL リンクが動く
- ✅ シェア URL 生成 + SNS で正しく OG image 表示
- ✅ pytest 全件 pass（既存テスト含む）
- ✅ Next.js build 全ページ pass
- ✅ スマホでレイアウト崩れなし

---

## Codex 委譲タイミング

- **Tailwind CSS のレイアウト調整**: Codex が早い（CLAUDE.md §9.2 領域分担）
- **OG image デザイン**: Codex
- **判定ロジック・API・テスト**: Claude（core/ 中核は Claude 担当）
- **コピーライティング**（質問文・結果文・CTA）: Codex で叩き台 → Claude が法令用語の正確性 verify

委譲する場合は `Agent(subagent_type=codex:codex-rescue)` で実装依頼。プロンプトテンプレは `using-codex` スキル参照。

---

## 完了後にやること

- `tasks/SALES_STRATEGY_KICKOFF_INDEX.md` の該当行に ✅ 追記
- `tasks/lessons.md` に学びを追記（とくに既存 eligibility ツールとの統合・差分）
- 次セッション向けに `/check` の URL を記録（営業資料化のため）
- Zenn 記事第 1 回（kickoff 02）から `/check` へのリンクを差し込み

---

## 別セッション起動プロンプト例

```
tasks/SALES_STRATEGY_KICKOFF_INDEX.md と tasks/kickoff_01_check_page.md を読んで、
対象企業判定チェックリスト /check 画面を実装してください。
ブランチを切り、PR まで作成してください。Tailwind/UI は必要に応じて Codex に委譲してください。
```

---

## 想定リスク・落とし穴

- ❌ 既存の `logi_clo_eligibility` ツールと判定基準が乖離 → **必ず先に既存実装を読む**
- ❌ メアド収集で個人情報保護方針の明示を忘れる → 個人情報取扱規程を `web/app/privacy/page.tsx` で公開
- ❌ AWS デプロイ後に CloudFront キャッシュで判定 API が古い結果を返す → `Cache-Control: no-store` 明示
- ❌ クエリパラメータでメアドを encode してしまう → セキュリティ事故。シェア URL はメアドを含めない
