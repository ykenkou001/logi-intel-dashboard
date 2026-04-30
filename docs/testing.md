# テスト方針

**責任範囲**: テストレベルの定義・モック方針・カバレッジ目標。テストを書く前の必読ドキュメント。

---

## テストレベル

| レベル | 対象 | 方法 |
|--------|------|------|
| 単体テスト | `core/` モジュールの全関数 | API 呼び出しは mock |
| 結合テスト | MCP サーバー経由でツールを呼ぶ E2E | VCR で録画 |
| 手動テスト | Claude Desktop での実動作確認 | 目視確認 |

---

## モック方針

- `tests/fixtures/` に各 API のサンプルレスポンスを保存する
- `pytest` の `monkeypatch` で httpx クライアントを差し替える
- VCR.py 検討（API 呼び出しを録画・再生）

---

## カバレッジ目標

| 対象 | 目標 |
|------|------|
| `core/` モジュール | 80% 以上 |
| MCP ツール層 | 60% 以上（ロジック薄いため） |

---

## テスト実行

```bash
uv run pytest tests/
uv run pytest tests/core/ -v        # core のみ
uv run pytest --cov=core tests/     # カバレッジレポート付き
```
