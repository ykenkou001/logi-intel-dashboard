# 次セッションへの引継ぎ（2026-05-05 時点）

## ⚠️ 並行作業の注意（最初に必ず確認）

健一は **Claude / Codex を別セッションで並行起動** して別領域を担当させる運用。

| 領域 | 担当 | 触ってよいファイル |
|------|------|-------------------|
| **Word / Excel 生成物の品質改善** | **Codex（並行作業中・触るな）** | `core/export/docx_form3_writer.py`, `core/export/excel_writer.py`, `tests/core/test_export_writers.py` |
| **CI/CD パイプライン修正（Lambda zip 問題）** | **Claude（このセッションの主目的）** | `infra/main.tf`, `.github/workflows/*.yml`, `pyproject.toml` の依存棚卸し |

**衝突注意の共有領域**: `pyproject.toml` の `[project.dependencies]` は Codex が docx/excel ライブラリ追加で触る可能性あり。変更時は健一に確認する。

詳細 → メモリ `feedback_codex_parallel_collaboration.md`

---

## 🎯 次セッションの主目的（最優先）

**CI/CD パイプラインを Green にする — Lambda zip サイズ問題を C 案で解決する。**

### 経緯

- フェーズ4.0 集大成 PR #1 を 2026-05-05 に main へマージ済（merge commit `5fda8b2`）
- マージで起動した GitHub Actions `Deploy API to Lambda` が「Lambda 関数を更新」ステップで失敗:

```
RequestEntityTooLargeException:
  Request must be smaller than 70167211 bytes (≈ 66.9 MB)
  for the UpdateFunctionCode operation
```

- 原因: `aws lambda update-function-code --zip-file` の API 直接アップロードは ~70MB 上限。CI の Linux 環境で生成された wheel（numpy / pandas / lxml の manylinux 版）が、ローカル Windows ビルド（44MB）より大きく 70MB を超えた
- **デプロイは現状失敗中。Lambda 上のコードは PR #1 マージ前のまま停滞している**（健一によるレイアウト修正・KPI カード修正等は本番反映していない）

### 採用方針: C 案（健一指示）

**A: S3 経由デプロイ + B: zip サイズ削減 を両方入れる**

- A: S3 経由で 70MB → 250MB の上限へ拡張（安全マージン）
- B: zip 自体を削減（デプロイ速度向上 + S3 容量削減）

### やる作業（順番）

#### 1. infra/main.tf の IAM 権限拡張

`data "aws_iam_policy_document" "github_actions_deploy"` 内に追加:

```hcl
statement {
  actions   = ["s3:PutObject"]
  resources = ["${aws_s3_bucket.main.arn}/lambda-deploy/*"]
}
```

`aws_s3_bucket_lifecycle_configuration.main` に rule 追加（古い zip 自動削除）:

```hcl
rule {
  id     = "expire-lambda-deploy-zips"
  status = "Enabled"
  filter { prefix = "lambda-deploy/" }
  expiration { days = 7 }
}
```

#### 2. terraform apply（健一実行）

```powershell
cd c:\Users\ykenk\repos\logi-intel-dashboard\infra
terraform plan -var "env=dev" -out plan.tfplan
terraform apply plan.tfplan
```

#### 3. .github/workflows/deploy-api.yml を S3 経由に変更

現在の `--zip-file fileb://...` を 2 段階に:

```yaml
- name: Lambda zip を S3 にアップロード
  run: |
    aws s3 cp lambda/function.zip \
      "s3://logi-intel-dev-7m2lqc/lambda-deploy/function-${{ github.sha }}.zip" \
      --region "$AWS_REGION"

- name: Lambda 関数を更新（S3 経由）
  run: |
    aws lambda update-function-code \
      --function-name "$LAMBDA_FUNCTION_NAME" \
      --s3-bucket logi-intel-dev-7m2lqc \
      --s3-key "lambda-deploy/function-${{ github.sha }}.zip" \
      --region "$AWS_REGION"
```

#### 4. zip サイズ削減（B）

`.github/workflows/deploy-api.yml` の Lambda zip ビルドステップで:

- `mcp_server/` を Lambda zip から **除外**（API ハンドラから参照されない・Lambda では使わない）
- `pip install --no-compile` でバイトコード生成抑制
- インストール後に不要ファイルを削除（例: `find lambda/build -name "*.pyc" -delete`, `__pycache__` 削除, `*.dist-info/RECORD` 等）
- numpy / pandas が本当に Lambda で必要か棚卸し
  - 不要なら `pyproject.toml` の dependencies から外す（**Codex の Word/Excel 改善と衝突注意**）
  - 必要なら諦めて B より A 中心で

zip 内訳の確認方法（CI runner で）:

```bash
du -sh lambda/build/*/ | sort -h | tail -20
```

目標: 50MB 以下。S3 経由なら 250MB まで OK だが、デプロイ速度にも効く。

#### 5. CI 動作確認

修正したワークフローを feature ブランチで PR → マージ後に Actions タブで Green 確認:

- https://github.com/ykenkou001/logi-intel-dashboard/actions
- `Deploy API to Lambda` workflow が Green
- ヘルスチェック (`curl https://d1zei8qivkf3cr.cloudfront.net/health`) が 200
- `aws lambda get-function --function-name logi-intel-dev-api --query "Configuration.LastModified"` で更新時刻確認

### 健一さん側の残タスク

| タスク | 状況 |
|---|---|
| GitHub Secrets `AWS_GITHUB_ACTIONS_ROLE_ARN` 登録 | **登録済**（CI が動いてエラー出ているので OIDC 自体は通っている） |
| Branch protection の Status checks 必須化 | main 上で CI が初回 green になり次第、Settings → Branches → main rule → Status checks に `CI / Python` `CI / Web` を追加 |

### やらないこと（このセッション）

- **`core/export/docx_form3_writer.py` `core/export/excel_writer.py` `tests/core/test_export_writers.py` を編集しない**（Codex が並行作業中）
- ローカル dev の API_BASE 問題は前セッションで対応済 → 触らない
- AWS インフラの構成変更は CI/CD 用 IAM ポリシー追加・S3 lifecycle rule 追加に限定（CloudFront / API Gateway / Lambda 関数本体は触らない）
- PPT は触らない（前セッションで完了）

---

## 後続タスク（CI/CD 完了 + Codex 作業完了の後）

### Word / Excel 生成物の品質改善（Codex 担当）

健一からの方針:

- **このセクションは Codex が並行作業中。Claude は触らない**
- 本番は AWS で構築済みなので、**ローカル開発 API_BASE まわりの修正は今回やらなくてよい**
- 前回レビューで見つかった改善点のうち、**生成物の Word / Excel を優先して改善する**
- セッションを変えて作業するため、この引継ぎを読んでから着手する

### 前回レビューで確認した生成物の状態

2026-05-05 のレビュー時点で、`logi_clo_plan_draft` / Web の計画書生成から出る最新成果物を構造検査した。

#### PPT

最新生成 PPT は **13 slides / native charts 3 / tables 0 / pictures 0**。

- `core/export/ppt_writer.py` に `ChartSpec` が入り、施策ポートフォリオ / コスト削減ウォーターフォール / KPI 5 ヶ年ロードマップの 3 チャートが生成される状態
- PPT は今回の主対象ではない。大きな破綻がなければ触らない

関連ファイル:

- `core/export/ppt_writer.py`
- `core/analytics/plan_draft.py`

#### Word（要改善）

最新生成 DOCX は **paragraphs 9 / tables 4**。構造は出るが、提出物としてはまだ薄い。

現状:

- `core/export/docx_form3_writer.py`
- 公式テンプレート `core/templates/clo_plan_form3.docx` が存在すれば流し込み、なければ python-docx で簡易構造を生成
- 公式テンプレ未取得時は先頭にドラフト注意書きを出す
- ただし Web 側では Word カードに「様式第3別紙・e-Gov 提出用」と表示しており、実態（公式テンプレ未取得時は参考ドラフト）より強い

優先改善:

1. **DOCX の見た目を提出前レビュー用として整える**
   - タイトル、注意書き、事業者情報、各セクション表のスタイルを改善
   - 表のヘッダ塗り、列幅、余白、フォントサイズ、段落間隔を調整
   - 「PoC 用ドラフト」「公式テンプレ未取得」注意が目立つようにする

2. **提出用と誤認させない表現に揃える**
   - 公式テンプレ未取得時は Web のダウンロードカード文言を「様式第3別紙ドラフト」などに弱める
   - ただしユーザーは「ローカル開発修正は不要」と言っているだけで、生成物を正しく表す UI 文言の小修正は Word 改善に付随するなら可

3. **DOCX レンダリング QA**
   - `documents` skill を使う
   - `render_docx.py --renderer artifact-tool` でページ PNG を出して目視確認
   - 生成物を ship する前に、表の文字切れ・重なり・余白不足を確認する

#### Excel（要改善）

最新生成 XLSX は **sheets `Data`, `出典` / Excel tables 0 / charts 0 / freeze pane None**。

現状:

- `core/export/excel_writer.py`
- openpyxl で単純に表と出典シートを書いている
- 経営会議の付録や社内レビュー用ブックとしては、まだ「整形済み CSV」に近い

優先改善:

1. **Excel を分析ブックらしくする**
   - `Data` シートに freeze pane、auto filter、Excel Table を追加
   - 数値列に適切な表示形式、折り返し、列幅、行高を設定
   - 主要KPIサマリーを上部または別 `Summary` シートに作る

2. **チャートを最低1つ追加**
   - 施策別コスト削減、CO2削減、投資額のいずれかを棒グラフ化
   - できれば `Summary` シートに KPI ブロック + 施策別チャート
   - 出典シートは監査用として残す

3. **出典シートの可読性改善**
   - freeze pane、filter、URL列折り返し、列幅調整
   - `statsDataId/告示番号` が空でも見やすいようにする

4. **XLSX QA**
   - `spreadsheets` skill を使う
   - 生成後に workbook 構造を検査し、少なくとも tables/charts/freeze panes が入ったことを確認
   - 可能ならレンダーして視覚確認

### 想定する実装ファイル

主対象:

- `core/export/docx_form3_writer.py`
- `core/export/excel_writer.py`
- `tests/core/test_export_writers.py`

必要なら付随:

- `web/app/dashboard/plan-draft/page.tsx`（Word カード文言のみ）
- `web/components/ToolResponseDisplay.tsx`（汎用ファイル文言のみ）
- `docs/roadmap.md` / `HANDOFF_NEXT_SESSION.md`（作業後の記録）

### 次セッションの推奨開始手順

```powershell
cd c:\Users\ykenk\repos\logi-intel-dashboard
git status
git log --oneline -8
uv sync
uv run pytest tests\core\test_export_writers.py -q
```

その後、現在の生成物を再生成してベースラインを取る:

```powershell
uv run python scripts\generate_sample_ppt_design.py
```

または API / analytics 経由で `sample_mfg_01` の plan draft を生成し、最新の `outputs/docx` / `outputs/excel` を確認する。

### 完了条件

- Word:
  - DOCX のページレンダーで、注意書き・事業者情報・各セクション表が読みやすい
  - 公式テンプレ未取得時に「提出用完成版」と誤認しない
  - 既存テストが通る

- Excel:
  - `Data` または `Summary` に Excel Table / freeze pane / chart が入る
  - `出典` シートが監査用に読みやすい
  - 生成された workbook を構造検査して tables/charts/freeze panes を確認
  - 既存テストが通る

- 検証:
  - `uv run pytest tests\core\test_export_writers.py -q`
  - 可能なら関連する export/plan draft テストも追加実行
  - Word は render PNG で目視確認
  - Excel は workbook inspect/render で確認

### やらないこと

- 今回はローカル dev の API_BASE 問題を修正しない
- AWS インフラや CloudFront 設定は触らない
- PPT は明確な破綻がなければ触らない

---

## ⚠️ 0. 最初に確認 — apply 待ちの差分があるか

直前セッション末で **CloudFront Function（directory URL → index.html 書換）** を追加したが、
健一の側で `terraform apply` が実行されたかどうか確認すること。

```powershell
cd c:\Users\ykenk\repos\logi-intel-dashboard\infra
terraform plan -var="env=dev"
# "No changes" ならapply済。差分が出たら未apply。
```

未 apply の場合は次を実行：
```powershell
terraform apply plan.tfplan
# 5〜10 分（CloudFront 配信反映）
```

apply 後の動作確認:
```powershell
curl -s -o NUL -w "HTTP=%%{http_code}`n" "https://d1zei8qivkf3cr.cloudfront.net/dashboard/macro/"
# HTTP=200 が期待値（apply 前は AccessDenied XML が返る）
```

### 直前セッションで発見・対応した 2 件のバグ（記録）

1. **`Failed to construct 'URL': Invalid URL`** （フロントエンド）
   - 原因: `new URL("/api/v1/...")` は base なし相対パスを受け付けない。`NEXT_PUBLIC_API_BASE_URL=""` の本番ビルドで全 fetch 失敗
   - 対応: `web/lib/api.ts` の `request()` を文字列結合 + URLSearchParams に変更（コミット `854efdf`）。デプロイ済（S3 同期 + CloudFront 無効化済）

2. **`/dashboard/<page>/` で AccessDenied XML**（インフラ）
   - 原因: S3 はディレクトリ概念がないため `web/dashboard/macro/` の GetObject が失敗。実体は `web/dashboard/macro/index.html`
   - 対応: CloudFront Function `rewrite-index` を追加（コミット `e6d3574`）。**未 apply の可能性あり** — 上記手順で確認

---

## ⚠️ 0.5 ローカル開発時の必須手順（必読）

**`uvicorn` / `npm run dev` を直接叩かない。** 必ずヘルパースクリプト経由で起動すること。

```powershell
pwsh scripts/dev_api.ps1            # FastAPI :8000（既存 uvicorn を kill + --reload）
pwsh scripts/dev_web.ps1            # Next.js :3000（既存 next dev を kill + API_BASE 固定）
```

### 経緯（2026-05-05 の事故・コミット `685bd77`）

PPT レイアウト修正を Lambda にデプロイしたあと、ブラウザで再生成したのに修正前の
PPT が DL される現象が発生。原因調査の結果:

- ローカルに古い `uvicorn`（5/4 16:03 起動分など）が `--reload` なしで複数残存し、
  古い `core/` をメモリに保持したまま port 8000/8765 を同時 listen
- `web/lib/api.ts` のデフォルト API_BASE が `http://localhost:8000` だったため、
  ブラウザのフロントが本番ではなくローカル uvicorn を叩いていた
- ダウンロードした PPT のタイムスタンプ・サイズが Lambda 経由（13 枚 / 77 KB）と
  ローカル経由（10 枚 / 51 KB）で食い違うことで判明

### 恒久対策（実施済）

| 対策 | 場所 |
|------|------|
| `api.ts` デフォルト API_BASE を `""`（同一 origin）に変更 | [web/lib/api.ts](web/lib/api.ts) |
| 既存 uvicorn を pre-kill して `--reload` で起動 | [scripts/dev_api.ps1](scripts/dev_api.ps1) |
| 既存 next dev を pre-kill して API_BASE を環境変数固定 | [scripts/dev_web.ps1](scripts/dev_web.ps1) |
| 経緯と起動ルール記載 | [CLAUDE.md §6.5](CLAUDE.md) |

### 自己診断手順（同種事故の再発時）

「コード直したのに本番のフロントから動作が変わらない」と感じたら:

1. ブラウザ DevTools の Network タブで API 先が `localhost` か CloudFront か確認
2. `Get-Process uvicorn,node` で残存プロセスを点検
3. 古いプロセスを Stop → `dev_api.ps1` / `dev_web.ps1` で再起動

---

## 1. 現在地

**フェーズ 4.0 完了** — AWS PoC デプロイ稼働中。社内レビューに使える状態。

| 項目 | 値 |
|------|----|
| 社内レビュー URL | https://d1zei8qivkf3cr.cloudfront.net/ |
| API Gateway 直叩き | https://fgwicoog66.execute-api.ap-northeast-1.amazonaws.com |
| AWS アカウント | 538099532416（健一個人・AdministratorAccess） |
| Region | ap-northeast-1 |
| Lambda 関数名 | `logi-intel-dev-api` |
| CloudFront ID | `E3F7LKFZVFU04Q` |
| API Gateway ID | `fgwicoog66` |
| S3 バケット | `logi-intel-dev-7m2lqc` |
| Terraform state | `infra/terraform.tfstate`（ローカル・gitignored） |

## 2. 動作確認済み

| 経路 | 結果 |
|------|------|
| `GET /` （Web トップ） | 200 / 全 8 画面リンク表示 |
| `GET /health` | 200 `{"status":"ok"}` |
| `GET /api/v1/company/samples` | 200 / サンプル3社 JSON |
| `GET /api/v1/clo/playbook` | 200 / 標準10施策 |
| `POST /api/v1/clo/plan-draft/sample_mfg_01` | 200 / PPT/Word/Excel/Markdown 生成（30〜60秒）|
| `GET /api/v1/files/markdown/...` | 302 → S3 プレサインド URL → 19KB DL OK |

## 3. 残課題（優先度順）

### 🔴 必須（次セッション最優先）

#### 3.1 e-Stat API キーが Lambda 上で読めるか確認
- SSM Parameter Store: `/logi-intel/dev/ESTAT_APP_ID` に投入済
- Lambda 環境変数: `LOGI_SECRETS_BACKEND=ssm` + `LOGI_SSM_PREFIX=/logi-intel/dev`
- `core/secrets.py` の `get_secret("ESTAT_APP_ID")` が SSM から取得して `os.environ` に反映する仕組み
- **未検証**: macro / benchmark / driver-gap のいずれも e-Stat 呼出が動作するか

検証手順：
```powershell
curl -s "https://d1zei8qivkf3cr.cloudfront.net/api/v1/macro/overview?prefecture=東京都"
curl -s "https://d1zei8qivkf3cr.cloudfront.net/api/v1/clo/benchmark?jsic_code=5411&prefecture=東京都&revenue_jpy=5000000000"
curl -s "https://d1zei8qivkf3cr.cloudfront.net/api/v1/clo/driver-gap?prefecture=東京都"
```

`{"detail":"e-Stat API error..."}` が返れば **`core/clients/estat.py` のクライアント初期化が `os.environ.get("ESTAT_APP_ID")` を直接読んでいる**箇所が原因。`core.secrets.get_secret()` 経由に書き換える必要あり。

CloudWatch Logs 確認：
```powershell
aws logs tail /aws/lambda/logi-intel-dev-api --follow --region ap-northeast-1
```

#### 3.2 sample_chain_01 / sample_wholesale_01 の plan-draft 動作確認

```powershell
curl.exe -X POST "https://d1zei8qivkf3cr.cloudfront.net/api/v1/clo/plan-draft/sample_chain_01"
curl.exe -X POST "https://d1zei8qivkf3cr.cloudfront.net/api/v1/clo/plan-draft/sample_wholesale_01"
```

連鎖化事業者（chain_01）は荷役等項目が省略されるなど挙動が異なるため、念のため動作確認。

### 🟡 高優先（社内デモ前）

#### 3.3 Codex 指摘の PPT 視覚化強化
PoC は数字が出るが PPT は **charts/tables/pictures = 0** で「文章を整えたスライド」状態。社内デモで「資料っぽさ」を出すには：

優先 3 枚（推定 1〜2 日）：
1. **施策ポートフォリオ図**（横軸 営業利益インパクト × 縦軸 CO2 削減 × バブル投資額・色 難易度）
2. **重複控除後ウォーターフォール**（合算最大 → 重複控除 → 標準シナリオ → 保守シナリオ）
3. **2030 年 KPI ロードマップ**（積載率 38→50% / CO2 ▲23.4% の四半期マイルストーン）

実装ファイル：`core/export/ppt_writer.py` に追加（python-pptx で matplotlib 画像を埋込）

### 🟢 中優先

#### 3.4 ホーム画面のローカル開発手順を AWS 経路にも対応
[web/app/page.tsx](web/app/page.tsx) のフッター部分が「`uv run uvicorn ... --port 8000`」のままなので、本番デプロイ表示と整合性取る（簡易タスク）。

#### 3.5 認証導入（PoC 卒業後）
- 現状: 認証なし（CloudFront URL を知ってる人なら誰でもアクセス可）
- 案: CloudFront Functions で Basic 認証 / Cognito User Pool / IP allowlist
- PoC 段階では不要だが社内全展開前に必要

### ⚪ 低優先（フェーズ 4.5）

- 計画書ドラフト docx の文章テンプレート化（公式記載見本集 MD 10 ファイル取込）
- 実 KPI 計測フレーム（計画策定時の測定方法・頻度・閾値埋込）
- CLO スタイル別重み付け（攻め / 守り / 環境重視 / 効率重視）

## 4. アーキテクチャ概要（記事化用素材）

```
[ブラウザ] ─HTTPS─→ [CloudFront]
                       │
                       ├─ /            ──→ [S3: web/ プレフィックス] (Next.js 静的)
                       │                       OAC で署名
                       │
                       └─ /api/* /health /docs /openapi.json
                                          ──→ [API Gateway HTTP API]
                                                 │ AWS_PROXY 統合
                                                 ↓
                                           [Lambda: Python 3.12 + Mangum + FastAPI]
                                                 │
                                                 ├─ /tmp/outputs ──→ [S3: outputs/ プレフィックス] (PPT/Word/Excel/Markdown)
                                                 ├─ /tmp/profiles → [S3: profiles/ プレフィックス] (CompanyProfile JSON)
                                                 └─ secrets        ──→ [SSM Parameter Store SecureString]
                                                                          /logi-intel/dev/ESTAT_APP_ID
```

### Zenn 記事ネタ
1. **「FastAPI を Mangum で Lambda に載せて API Gateway HTTP API でフロント、月 $3 で社内 PoC」**（実話そのまま）
2. **「Lambda OAC 採用を試みて 403 沼にハマった話」**（途中の試行錯誤・最終的に API Gateway HTTP API に逃げた経緯）
3. **「MCP × REST 同じビジネスロジックで 2 経路 — `core/` を Claude Desktop と Web ダッシュボードで共有」**（差別化ポイント）
4. **「物流効率化法 CLO 業務 × LLM ツール — 法令準拠ドラフト生成のドメイン設計」**（業界向け）

## 5. 次セッション開始時の手順

```powershell
# 1. プロジェクト確認
cd c:\Users\ykenk\repos\logi-intel-dashboard
git log --oneline -5
git status

# 2. ローカル環境確認
uv run pytest --tb=short -q       # 422 件 pass を確認
cd web && npm run type-check      # type-check pass を確認

# 3. 残課題 3.1 から着手
curl -s "https://d1zei8qivkf3cr.cloudfront.net/api/v1/macro/overview?prefecture=東京都"
# 失敗するなら CloudWatch Logs を見る
aws logs tail /aws/lambda/logi-intel-dev-api --since 5m --region ap-northeast-1
```

## 6. AWS リソース管理

### Lambda zip 再ビルド & 再デプロイ
```powershell
cd c:\Users\ykenk\repos\logi-intel-dashboard

# 1. lambda/build/ にコード再配置
Remove-Item -Recurse -Force lambda\build\api, lambda\build\core -ErrorAction SilentlyContinue
Copy-Item -Recurse -Force core lambda\build\
Copy-Item -Recurse -Force api lambda\build\
Get-ChildItem lambda\build -Recurse -Directory -Force | Where-Object { $_.Name -eq "__pycache__" -or $_.Name -like "*.dist-info" } | Remove-Item -Recurse -Force

# 2. zip 圧縮
Remove-Item lambda\function.zip -ErrorAction SilentlyContinue
Compress-Archive -Path lambda\build\* -DestinationPath lambda\function.zip -CompressionLevel Optimal

# 3. アップロード
aws lambda update-function-code --function-name logi-intel-dev-api --zip-file fileb://lambda/function.zip --region ap-northeast-1
```

### Next.js 再ビルド & S3 再同期
```powershell
cd web
$env:NEXT_PUBLIC_API_BASE_URL = ""
npm run build
aws s3 sync out/ s3://logi-intel-dev-7m2lqc/web/ --delete --region ap-northeast-1
aws cloudfront create-invalidation --distribution-id E3F7LKFZVFU04Q --paths "/*" --region ap-northeast-1
```

### AWS リソース全削除（PoC 終了時）
```powershell
cd c:\Users\ykenk\repos\logi-intel-dashboard\infra
terraform destroy -var="env=dev"

# SSM パラメータも個別に削除（terraform 管理外のため）
aws ssm delete-parameter --name /logi-intel/dev/ESTAT_APP_ID --region ap-northeast-1
```

## 7. 設計上の決定（記録）

### Lambda Function URL → API Gateway HTTP API へ転換
PoC で次の 2 つを試したが両方 403：
1. Function URL（NONE auth）+ public resource policy
2. Function URL（AWS_IAM auth）+ CloudFront OAC + sigv4 署名

**結論**: API Gateway HTTP API + Lambda Proxy 統合に切替。コスト差 <$0.01/月で許容。
原因は AWS の Block Public Access 系か OAC の sigv4 経路の問題と推測されるが、PoC 期限優先で深追いせず。

### Docker は不要と判断
- 当初 ECS Fargate 想定で Dockerfile を準備したが、Lambda zip で十分（45MB）。
- Dockerfile / docker-compose.yml / .dockerignore は撤去済（コミット 9d52337）。

### `core/storage.py` + `core/secrets.py` の抽象化
- ローカル開発（既存挙動）を完全互換のまま AWS 切替対応
- 環境変数 `LOGI_STORAGE_BACKEND={local|s3}` / `LOGI_SECRETS_BACKEND={env|ssm}` で切替
- Lambda は両方 S3/SSM、ローカルは local/env のまま

## 8. 主要ファイルマップ

```
infra/
├── main.tf                       # Terraform IaC（S3+Lambda+API GW+CloudFront+IAM）
├── README.md                     # デプロイ手順
└── terraform.tfstate             # ローカル state（gitignored）

lambda/
├── README.md                     # zip ビルド手順
├── requirements-lambda.txt       # Lambda 専用最小依存リスト
└── function.zip                  # ビルド成果物（gitignored・43MB）

scripts/
└── put-ssm-secrets.ps1           # .env から SSM Parameter Store へ投入

core/
├── storage.py                    # LocalStorage / S3Storage 抽象（新規）
├── secrets.py                    # env / SSM 抽象（新規）
└── macro/
    └── sources.py                # macro fetch ヘルパー切り出し（fastmcp 非依存）

api/
└── lambda_handler.py             # Mangum で FastAPI を Lambda 化

docs/
├── aws_migration_plan.md         # AWS 移行計画書（PoC 最安構成）
└── roadmap.md                    # フェーズ全体（フェーズ4.0 完了マーク済）
```

---

最終更新: 2026-05-05（PoC デプロイ完了直後）
