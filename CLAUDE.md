# Logi-Intel Dashboard — Claude Code 指示書

このファイルは Claude Code がこのプロジェクトで作業する際の指示書。
作業前に必ず最初に読み込むこと。

---

## 1. プロジェクト概要

日本のオープンデータ（e-Stat, 国税庁法人番号, xROAD, 気象庁等）を統合し、物流業界の分析データを提供する基盤。
※ RESAS API は 2025-03-24 に提供終了。e-Stat（経済センサス・国勢調査等）で代替する。

**主用途**:
- 営業・提案資料の根拠データ提供
- 2026年4月義務化の CLO（物流統括管理者）の中長期計画策定支援
- Claude Desktop/Code から自然言語でデータ問い合わせ

**ターゲットユーザー**: micware 社内の営業・企画・経営層、CLO 候補者

詳細 → [docs/architecture.md](docs/architecture.md) | [docs/clo_domain.md](docs/clo_domain.md)

---

## 2. ドキュメント索引

| ドキュメント | 内容 |
|-------------|------|
| [docs/architecture.md](docs/architecture.md) | 3 層アーキテクチャ・技術スタック・ディレクトリ構造・キャッシュ設計 |
| [docs/roadmap.md](docs/roadmap.md) | 開発フェーズ・進捗状況（今どこにいるか） |
| [docs/coding_standards.md](docs/coding_standards.md) | 言語・命名・設計・Lint 規約 |
| [docs/api_endpoints.md](docs/api_endpoints.md) | 利用 API 一覧・認証・TTL・制約 |
| [docs/mcp_tools.md](docs/mcp_tools.md) | MCP ツール命名規則・実装方針 |
| [docs/clo_domain.md](docs/clo_domain.md) | CLO 業務ドメイン知識・法的定義 |
| [docs/oss_reference.md](docs/oss_reference.md) | 参考 OSS の方針・Attribution |
| [docs/testing.md](docs/testing.md) | テストレベル・モック方針・カバレッジ目標 |
| [docs/git_workflow.md](docs/git_workflow.md) | ブランチ戦略・コミットメッセージ規則 |
| [docs/notes.md](docs/notes.md) | API 利用規約・シークレット管理・パフォーマンス制約 |
| [docs/licenses.md](docs/licenses.md) | 各 API の利用規約と商用利用可否（要作成） |

---

## 3. 現在のフェーズ

**フェーズ 2: データソース拡張** ← 今ここ

詳細は [docs/roadmap.md](docs/roadmap.md) 参照

詳細 → [docs/roadmap.md](docs/roadmap.md)

---

## 4. 重要原則（必ず守ること）

- **ビジネスロジックは必ず `core/` に置く** — MCP・REST 層には書かない
- **過剰アクセス禁止** — キャッシュ必須、リトライにバックオフ必須
- **API キーをログに出力しない** — `core/clients/base.py` でマスク処理
- **ロジックを先に読む** — 推測で実装しない

---

## 5. 作業開始時のチェックリスト

1. このファイル（CLAUDE.md）を読み込んだか
2. 現在のフェーズを [docs/roadmap.md](docs/roadmap.md) で確認したか
3. 直近の git log を見て、どこまで進んでいるか確認したか（`git log --oneline -20`）
4. 作業前に `uv sync` で依存関係を最新化したか

---

## 6. 判断に迷ったら

優先順位:
1. このファイルの記載内容を最優先
2. `docs/` 配下の該当ドキュメント
3. 既存実装のパターンに合わせる
4. 健一（開発者）に確認

判断に迷う実装は、まず簡単な版で動かしてから、健一に確認する。**完璧主義より MVP 思考**。

---

## 7. Subagent 活用方針

複雑なタスクは subagent に分割して委譲する。

| 役割 | 担当タスク |
|------|-----------|
| `estat-explorer` | e-Stat の統計表 ID・コード体系の探索 |
| `api-spec-reader` | API 仕様書を読んでクライアント実装を提案 |
| `test-writer` | 既存実装に対するテストを書く |
| `doc-writer` | docstring・README を整備する |

**起動の判断基準**: 単一ファイル修正 → 直接編集 / 複数ファイル横断調査 → subagent

---

最終更新: 2026-05-01（RESAS 終了反映・AWS 移行計画追加）
