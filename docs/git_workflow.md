# Git 運用・ブランチ戦略

**責任範囲**: ブランチ命名・コミットメッセージ・PR 運用のルール。コミットや PR を作成する際の参照先。

---

## ⚠️ main ブランチ運用ルール（必読・全エージェント共通）

`main` への**直接コミット・直接 push は禁止**。GitHub の branch protection（Ruleset）で
ブロックされている。Claude / Codex / 健一を含めた全担当者が以下を守ること。

### ルール

1. **必ず feature ブランチを切ってから作業する** — `feature/...` `fix/...` `docs/...` `ci/...`
2. **commit と push は feature ブランチに対してのみ行う** — `git push origin main` は失敗する
3. **main への取り込みは Pull Request 経由のみ** — `gh pr create` で PR を作成し、GitHub UI でマージする
4. **PR マージ時は merge commit / squash どちらでも可**（健一判断）
5. **CI（`CI / Python` `CI / Web`）が Green になるまでマージしない** — Status checks 必須化済

### 違反時に起きる症状

- `git push origin main` → `! [remote rejected] main -> main (protected branch hook declined)`
- main を直接 checkout してコミットしてしまった場合 → feature ブランチを切り直して `git reset` で main を巻き戻し → 同名で push し直す

### feature ブランチからのフロー（標準）

```powershell
# 1. main を最新化
git checkout main
git pull

# 2. feature ブランチを切る（命名規則は下表）
git checkout -b fix/lambda-deploy-zip

# 3. 変更 → コミット → push
git add ...
git commit -m "fix(ci): ..."
git push -u origin fix/lambda-deploy-zip

# 4. PR 作成
gh pr create --title "..." --body "..."

# 5. CI Green を確認 → GitHub UI でマージ
# 6. ローカルで main に戻して pull、不要 feature ブランチを削除
git checkout main && git pull
git branch -d fix/lambda-deploy-zip
```

### Codex / Claude が並行作業する場合

- 担当領域を分けて feature ブランチも分ける（同じファイルを同時に触らない）
- 互いの作業境界は `HANDOFF_NEXT_SESSION.md` の冒頭表を参照
- main マージ後は他方のセッションで `git pull` してから作業を続ける

---

## ブランチ戦略

| ブランチ | 用途 | 例 |
|---------|------|-----|
| `main` | 常にデプロイ可能な状態。**直接 push 禁止・PR 経由のみ** | — |
| `feature/{機能名}` | 機能開発 | `feature/estat-client` |
| `fix/{修正内容}` | バグ修正 | `fix/lambda-deploy-zip` |
| `docs/{ドキュメント名}` | ドキュメント追加・更新 | `docs/handoff-cicd-zip-fix` |
| `ci/{内容}` | CI/CD・インフラ周り | `ci/deploy-via-s3` |
| `refactor/{内容}` | 振る舞いを変えないリファクタ | `refactor/clients-base` |

---

## コミットメッセージ

日本語、Conventional Commits 風:

```
feat: e-Stat 統計表検索ツールを実装
fix: キャッシュキー生成のハッシュ衝突を修正
docs: CLO ドメイン知識ドキュメントを追加
refactor: HTTP クライアント基底クラスを抽出
test: e-Stat クライアントの単体テストを追加
chore: 依存関係を更新
ci: GitHub Actions ワークフローを修正
```

スコープ付き（推奨）:

```
fix(ci): Lambda デプロイを S3 経由に切替
feat(clo): 施策別 P&L 翻訳ツールを追加
```

---

## Pull Request

- 自分一人の開発でも、フェーズ単位 / 修正単位で PR を切る（振り返り・Zenn 記事ネタになる）
- PR 説明には「何を」「なぜ」を日本語で書く
- Test plan セクションを書く（マージ後に動作確認すべき項目）
- Codex / Claude が作成する PR は本文末尾に Co-Authored-By / Generated 表記を残す（既存運用通り）
