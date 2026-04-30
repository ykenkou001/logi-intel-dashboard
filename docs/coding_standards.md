# コーディング規約

**責任範囲**: コードを書く際の言語・命名・設計・エラーハンドリング・Lint 設定の全規約。「どう書くか」の唯一の参照先。

---

## 言語使い分け

| 対象 | 言語 |
|------|------|
| コード内コメント・docstring・ログ・エラーメッセージ | 日本語 |
| 関数名・変数名・クラス名 | 英語、snake_case / PascalCase |
| ドキュメント（README、docs/） | 日本語 |
| コミットメッセージ | 日本語 |

---

## 命名規則

| 種別 | 形式 | 例 |
|------|------|----|
| 関数・変数 | `snake_case` | `fetch_data`, `area_code` |
| クラス | `PascalCase` | `EStatClient`, `ApiCache` |
| 定数 | `UPPER_SNAKE_CASE` | `DEFAULT_TTL`, `MAX_RETRY` |
| プライベート | 先頭 `_` | `_internal_helper` |

---

## 関数設計

- 1 関数 1 責務
- 副作用のある関数と純粋関数を分離
- 引数は Pydantic モデルか基本型のみ
- async 関数には型ヒントを必ずつける

---

## エラーハンドリング

- カスタム例外を `core/exceptions.py` に定義する
- API エラーは個別のカスタム例外でラップする（例: `EStatApiError`）
- ユーザー（Claude）向けのエラーメッセージは日本語で具体的に記述する

---

## Lint / Format 設定

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "C4", "SIM", "RUF"]

[tool.mypy]
strict = true
python_version = "3.12"
```

---

## アンチパターン（禁止事項）

- 状態を持たない不要なクラス化
- 継承の実装予定がない段階での抽象基底クラス（ABC）の導入
- デッドコードや未使用引数の放置
- ロジックを MCP / REST 層に書く（必ず core に置く）
