# 参考 OSS の方針

**責任範囲**: 既存 OSS の参照方針・ライセンス上の取り扱い・attribution ルール。コードを書く前に「車輪の再発明か参考にすべきか」を判断するためのドキュメント。

---

## japan-data-mcp

| 項目 | 内容 |
|------|------|
| リポジトリ | https://github.com/Izyuusya/japan-data-mcp |
| ライセンス | Apache-2.0 |
| 方針 | **フォークではなく参考にする**（コード引用は OK だが attribution 必須） |

### 参考にする部分

- e-Stat のコード → 名称解決ロジック
- メタ情報取得の流れ

### 独自に書く部分

- 物流特化の複合分析
- CLO 支援機能
- リアルタイムデータ統合
- ドメインモデル

---

## estat-mcp

| 項目 | 内容 |
|------|------|
| リポジトリ | https://github.com/ajtgjmdjp/estat-mcp |
| ライセンス | Apache-2.0 |
| 方針 | **参考実装として読む** |

---

## Attribution（README 記載内容）

```
本プロジェクトは以下の OSS を参考にしています:
- japan-data-mcp (Apache-2.0): e-Stat クライアント実装の参考
- estat-mcp (Apache-2.0): MCP ツール設計の参考
```
