# フェーズ 5.5 β: 既知 3 課題の修正計画

**ブランチ（推奨）**: `feature/phase-5.5-beta-fixes`
**確定日**: 2026-05-10
**前提**: PR #33 (α 案) マージ済 / 健一が AWS PoC で実機確認 → 既知問題 3 件を発見

---

## 着手前チェック（必須）

1. 別セッション（Claude / Codex）が並行作業しているか健一に確認
2. `git checkout main && git pull origin main` で最新化
3. `git checkout -b feature/phase-5.5-beta-fixes` でブランチを切る
4. memory `feedback_parallel_session_branching.md` のルールに従う

---

## 課題一覧（優先度順・効果大／負荷小から）

| # | 課題 | 規模 | 推定工数 |
|---|---|---|---|
| β-1 | J2 罠スコア画面のセレクタに sample_retail_01 が抜けている | XS | 15 分 |
| β-2 | 計画書 DL が即 DL にならず Edge プレビューで開く（特に MD は DL 不可） | S | 1〜2 時間 |
| β-3 | Markdown 出力を HTML に置換／併用するかの設計判断 + 実装 | M | 半日〜1 日 |

---

## β-1: list_samples が 4 業種を返さない

### 症状
J2 罠スコア画面 (`/dashboard/waste-traps`) の会社 ID セレクタに `sample_retail_01` が出ていない（製造 / 卸売 / 連鎖化のみ表示）。実装上は同画面以外でも `fetchSamples()` を使う全画面で共通の不具合。

### 原因（特定済）
[api/routers/company.py:157-183](../api/routers/company.py#L157-L183) の `list_samples()` がハードコードで 3 件しか返していない。実体の [core/static/sample_company.py:606](../core/static/sample_company.py#L606) `ALL_SAMPLES` には 4 件全部登録済 (`sample_mfg_01` / `sample_wholesale_01` / `sample_retail_01` / `sample_chain_01`)。

```python
# 現状（抜粋）
@router.get("/samples", response_model=list[dict[str, str]])
async def list_samples() -> list[dict[str, str]]:
    return [
        {"company_id": "sample_mfg_01", ...},
        {"company_id": "sample_wholesale_01", ...},
        {"company_id": "sample_chain_01", ...},
        # ← sample_retail_01 が欠落
    ]
```

### 修正方針

**2 案の比較**

#### 案 A: ハードコード追加（最小修正）
sample_retail_01 を 1 件追加するだけ。15 行未満。

#### 案 B: ALL_SAMPLES から動的生成（推奨）
将来サンプル追加時の抜け漏れを構造的に防止。`core/static/sample_company.py` に `data_source` / `name` / `industry` のメタを足し、`list_samples()` は `ALL_SAMPLES.values()` をそのまま返す。

```python
# 案 B 実装イメージ
from core.static.sample_company import ALL_SAMPLES
from core.static.jsic import category_of

@router.get("/samples", response_model=list[dict[str, str]])
async def list_samples() -> list[dict[str, str]]:
    return [
        {
            "company_id": p.company_id,
            "name": p.name,
            "industry": category_of(p.jsic_code) or "other",
            "data_source": p.data_source,
        }
        for p in ALL_SAMPLES.values()
    ]
```

**推奨**: 案 B（β-2/β-3 でサンプル追加の余地もあり、根治しておく）

### 影響範囲
- `tests/api/test_company_router.py` の samples 件数アサーション（3 → 4 への更新が必要）
- pytest 該当テストのみで確認可能

### 検証
1. `uv run pytest tests/api/test_company_router.py -q`
2. ローカル dev でセレクタに 4 件出ることを Playwright で確認

---

## β-2: 計画書 DL が即 DL にならない

### 症状
- `/dashboard/plan-draft` で生成した PPT/Word/Excel をクリックすると Edge が新規タブでプレビュー表示してしまう（即 DL にならない）
- **Markdown は DL 自体できない**（ブラウザが直接表示する）

### 原因（推定）

#### 原因 1: フロント側の `<a>` タグに `download` 属性なし
全 3 箇所で `<a target="_blank">` のみ使用、`download` 属性なし:
- [web/components/ToolResponseDisplay.tsx:92,160](../web/components/ToolResponseDisplay.tsx#L92)
- [web/app/dashboard/plan-draft/page.tsx:184,276](../web/app/dashboard/plan-draft/page.tsx#L184)
- [web/app/dashboard/industry-package/page.tsx:113](../web/app/dashboard/industry-package/page.tsx#L113)

#### 原因 2: MD の MIME type が text 系
[api/routers/files.py:29](../api/routers/files.py#L29) で `.md → text/markdown; charset=utf-8` を返している。ブラウザは text/* を「閲覧可能」と判断し、`Content-Disposition: attachment` を無視して直接表示することが多い（特に Edge / Chrome）。

#### 原因 3: S3 backend のプレサインド URL に Content-Disposition 未指定
[api/routers/files.py:50-53](../api/routers/files.py#L50-L53) は単純に `storage.download_url(file_path)` で 302 リダイレクト。AWS PoC は S3 backend なので、プレサインド URL に `ResponseContentDisposition=attachment;filename=...` を付けないと Office ファイルもブラウザで開いてしまう。

### 修正方針

#### Fix 1（フロント）: `download` 属性を全 a タグに付与
```tsx
<a
  href={fileDownloadUrl(path)}
  download
  rel="noreferrer"
>
```
- `target="_blank"` を **削除**（`download` と併用すると挙動が不安定）
- 同一 origin / プレサインド URL（クロスオリジン）双方で効く保証はないので、以下の Fix 2/3 と組合せて多重化する

#### Fix 2（API）: MD の media_type を `text/plain` または `application/octet-stream` に
```python
_MEDIA_TYPES = {
    ...
    ".md": "text/plain; charset=utf-8",  # ブラウザ直接表示を抑制
    # または完全強制で "application/octet-stream"
}
```
- text/markdown はブラウザ表示を促すので、汎用テキストにダウングレードする

#### Fix 3（S3 backend）: プレサインド URL に Content-Disposition を載せる
[core/storage.py](../core/storage.py) の S3Storage クラスで `download_url` を拡張:
```python
def download_url(self, key: str) -> str:
    return self.s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": self.bucket,
            "Key": key,
            "ResponseContentDisposition": f'attachment; filename="{Path(key).name}"',
        },
        ExpiresIn=3600,
    )
```

#### Fix 4（API）: ローカル backend でも明示的に attachment 指定
FastAPI FileResponse はデフォルトで `content_disposition_type="attachment"` だが、念のため明示:
```python
return FileResponse(
    path=candidate,
    media_type=media_type,
    filename=candidate.name,
    content_disposition_type="attachment",  # 明示
)
```

### 推奨実施順
1. **Fix 1 + Fix 2** を最低限実施（フロント + MD media_type ダウングレード） → ローカル dev で 4 ファイル DL 確認
2. **Fix 3** を S3 backend に追加 → AWS PoC で確認
3. Fix 4 は念のため

### 影響範囲
- `tests/core/test_storage.py` で S3 download_url のテスト追加
- `tests/api/test_files_router.py` の MD 配信テスト確認
- フロントのスナップショット系テスト（あれば）

### 検証
1. ローカル dev で 4 ファイルすべて DL されること（ブラウザのダウンロード履歴で確認）
2. AWS PoC で同じく 4 ファイル DL されること
3. β-3 で MD を廃止する場合は本 Fix 2 / 3 の MD 部分は不要

---

## β-3: Markdown を HTML に置換／併用するか

### 健一の問題提起
> MD は HTML に変更しようと思うが、Claude どう思う。Anthropic では MD では使わず、HTML を使っているようだ。

### 調査結果（2026-05-10 時点）

**Anthropic 公式の方針**:
- Claude Artifacts は markdown・HTML・SVG・React など複数フォーマットをサポート（[公式 help](https://support.claude.com/en/articles/9487310)）
- 公式に「Markdown より HTML を推奨」と明文化はされていない
- ただし「self-contained で見栄えのよい成果物」用途では HTML が選ばれる傾向（[html-artifacts skill](https://github.com/dogum/html-artifacts) は「produce self-contained HTML artifacts instead of markdown when the task warrants it」と明示）

**Claude.ai の実装**:
- Markdown artifacts は live preview でレンダリング表示される
- HTML artifacts は CSS/JS 含めて自己完結
- 経営層・対外資料の用途では HTML が一般的

### Claude の意見（推奨判断）

**HTML を主軸にして、MD は残す（併用）** を推奨。

#### HTML 採用のメリット（CLO 業務に効く点）
1. **ブラウザでそのまま開ける** — MD は閲覧アプリが必要、HTML はダブルクリックで誰でも見える（経営会議の現場で強い）
2. **印刷で PDF 化が容易** — Ctrl+P → PDF 保存で配布物が即作れる
3. **インライン CSS でブランド統一** — `docs/ppt_design.md` のデザイントークンを CSS 変数として埋め込める
4. **チャート / 表埋め込み** — Mermaid・SVG・テーブルが MD より柔軟
5. **出典 URL が clickable** — MD は閲覧環境でリンクが効くか不安定、HTML は確実

#### HTML 単独切替のリスク（MD を完全廃止する場合）
1. 既存テストの outputs/ パス全件書換が必要（影響大）
2. CLI で grep したい場面（plain text として）には MD のほうが扱いやすい
3. NotebookLM への取込は MD のほうが互換性が高い場合あり

#### 推奨実装プラン
**段階 1（β-3a）**: HTML writer を追加（MD は残す）
- `core/export/html_writer.py` を新規作成（雛形は `core/export/markdown_writer.py`）
- self-contained: `<style>` インラインで [docs/ppt_design.md](../docs/ppt_design.md) のトークン適用
- `result.files["html"] = path` を追加、ToolResponse 経由で DL ボタンが自動追加
- [web/components/ToolResponseDisplay.tsx:11-46](../web/components/ToolResponseDisplay.tsx#L11) `FILE_CONFIG` に `html` エントリ追加

**段階 2（β-3b）**: 様子見後、MD を deprecation
- HTML が定着したら MD を削除（影響最小化のため別 PR）
- もしくは「MD は内部用」「HTML は配布用」と運用上分離

### CLAUDE.md §1.5 整合性
- ✅ Executive Communication: HTML は経営層への配布物として MD より優れる
- ✅ Defensibility: 出典 URL の clickable 維持
- ⚠️ 「成果物ファイル」原則は変更なし（PPT/Word/Excel/HTML/(MD)）

### 影響範囲
- `core/export/__init__.py` / `core/analytics/plan_draft.py` / `core/analytics/periodic_report.py` 等の生成側
- `tests/core/test_export_writers.py` に HTML writer テスト追加
- フロント `FILE_CONFIG` 拡張
- README / docs/architecture.md の出力一覧更新

### 検証
1. 4 業種サンプルで HTML 生成 → ブラウザで開いて経営会議に耐えるレイアウトか
2. Ctrl+P で PDF 化したときも体裁崩れないか
3. β-2 完了後の DL 即実行を HTML でも確認

---

## まとめ：着手順序

| 順 | タスク | 工数 | 依存 |
|---|---|---|---|
| 1 | β-1（samples 4 件返す） | 15 分 | なし |
| 2 | β-2（DL 即実行） | 1〜2 時間 | β-3 と相互影響あり |
| 3 | β-3（HTML writer 追加） | 半日〜1 日 | β-2 と相互影響あり |

β-1 は単独 PR（即マージ）でよい。β-2 と β-3 は MD の扱いで設計が連動するので 1 PR にまとめてもよい（または β-3 を先行 → β-2 で HTML だけ DL 強化、MD は将来削除）。

---

## 補足: 関連ファイル一覧

### β-1
- 修正: [api/routers/company.py:157-183](../api/routers/company.py#L157-L183)
- 参照: [core/static/sample_company.py:606](../core/static/sample_company.py#L606) `ALL_SAMPLES`
- テスト: [tests/api/test_company_router.py](../tests/api/test_company_router.py)

### β-2
- フロント修正: [web/components/ToolResponseDisplay.tsx](../web/components/ToolResponseDisplay.tsx) / [web/app/dashboard/plan-draft/page.tsx](../web/app/dashboard/plan-draft/page.tsx) / [web/app/dashboard/industry-package/page.tsx](../web/app/dashboard/industry-package/page.tsx)
- API 修正: [api/routers/files.py](../api/routers/files.py) / [core/storage.py](../core/storage.py)（S3Storage）
- テスト: [tests/api/test_files_router.py](../tests/api/test_files_router.py) / `tests/core/test_storage.py`

### β-3
- 新規: `core/export/html_writer.py`
- 修正: [core/export/__init__.py](../core/export/__init__.py) / [core/analytics/plan_draft.py](../core/analytics/plan_draft.py) / [core/analytics/periodic_report.py](../core/analytics/periodic_report.py) / [web/components/ToolResponseDisplay.tsx:11](../web/components/ToolResponseDisplay.tsx#L11)
- 削除候補: [core/export/markdown_writer.py](../core/export/markdown_writer.py)（β-3b）
- テスト: [tests/core/test_export_writers.py](../tests/core/test_export_writers.py)
