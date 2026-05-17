# Tier S4 詳細実装計画 — 罰則・社名公表リスクの経営層視覚化

**作成日**: 2026-05-17
**担当**: Claude（セッション A — Tier S4 専属）
**並列セッション**: A=Tier S1 (DecisionLog) / B=Tier S3 (Facility)
**ベース**: `plans/phase55_update_proposal.md` Tier S4
**ブランチ**: `docs/compliance-risk-ppt` (worktree `../logi-intel-dashboard.compliance-risk`)

---

## 1. 目的

`submission_validator` の準拠率を、経営会議で即答できる
**「行政指導 → 勧告 → 公表 → 100 万円罰金」のステップフロー**として PPT に焼き付ける。
現在地と該当する追加対応の箇条書きを 1 枚で示し、CLO 担当者が経営層に説明責任を果たせる成果物を保証する。

非目標:
- ❌ 「準拠率 X% のとき行政指導の確率は Y%」のような **数値推定値の付与はしない**（公表根拠なし）
- ❌ 既存 `submission_validator` のロジックは触らない（読み込みのみ）
- ❌ Web 画面・REST 拡張はしない（PPT 拡張のみ）

## 2. 既存資産の前提（読み込みのみ・改変禁止）

| ファイル | 役割 | 本計画での扱い |
|---|---|---|
| `core/validators/submission_validator.py` | `ValidationReport` / `compliance_score_pct` | **読み込みのみ** |
| `core/export/citation.py` | 法令根拠 citation | 読み込みのみ |
| `core/legal/article_resolver.py` | 第46/65/66条の区分判定 | 読み込みのみ |

`compliance_score_pct` の算出ロジック:
- 100pt 起点・error ▲10pt・warning ▲3pt・下限 0 / 上限 100
- `total_checks = 20` は現状未使用パラメタ（参考値）

## 3. 4 ステップフロー定義（法的根拠ベース）

物流効率化法における CLO / 特定荷主 / 連鎖化事業者への段階的措置を **法文で確認できる範囲だけ**ステップ化する。

| # | ステップ | 法的根拠（区分別） | 実害 | スライドでの位置づけ |
|---|---|---|---|---|
| 1 | **行政指導** | 法令上の明文規定なし（実務運用） | 改善要請・追加報告依頼 | 軽度警告 |
| 2 | **勧告** | 特定荷主: 法第48条 / 連鎖化: 法第67条 | 計画修正の正式要求 | 中度警告 |
| 3 | **命令 + 社名公表** | 特定荷主: 法第49条 / 連鎖化: 法第68条 | 社名公表（取引先・取引銀行に波及） | 重度警告 |
| 4 | **罰則（100 万円以下の罰金）** | 特定荷主: 法第50条 / 連鎖化: 法第69条 | 100 万円以下の罰金・刑事処分扱い | 致命警告 |

**判断**: 「行政指導」は法文に明文なしのため、本計画では **「制度運用上のステップ」** と明示し、勧告以降を主軸の法的根拠とする。CLO 制度施行（2026-04）後の公表予告事例は未蓄積のため、確率推定値は出さない（推測禁止）。

## 4. 現在地マーカーの判定ロジック（準拠率からの段階的マッピング）

`compliance_score_pct` と `error_count` の組み合わせで段階決定する。

| 状態キー | 条件 | 表示 |
|---|---|---|
| `ok` | score ≥ 90 かつ error 0 件 | 「指導前」緑バナー |
| `guidance` | score 70-89 または warning ≥ 3 件 | 行政指導マーカー（黄） |
| `recommendation` | score 40-69 または error 1-2 件 | 勧告マーカー（オレンジ） |
| `publication` | score 1-39 または error 3-5 件 | 公表マーカー（赤） |
| `fine` | score = 0 または error ≥ 6 件 | 罰金マーカー（暗赤） |

**根拠の限界**:
- これは「内部運用上の段階分け」であり、行政の実運用とは別である
- スライドには **「※本判定は当社の準拠率しきい値による内部評価」** と注記する
- score 100% でもエラー検査が当たっていないだけの可能性があるため、ok 表示時も「現在判定基準で問題なし」と限定文言

## 5. データ受け渡し設計

`ChartSpec` の `kind` を増設して `_add_content_slide` を介さず `_add_chart_body` 経由で描画する。既存パターン（portfolio/waterfall/roadmap）に沿う。

```python
ChartSpec(
    kind="compliance_risk_step",
    data={
        "compliance_score_pct": 78.5,
        "error_count": 1,
        "warning_count": 2,
        "current_step": "recommendation",  # ok / guidance / recommendation / publication / fine
        "missing_actions": [
            "様式第3 の「実施措置」欄を埋める",
            "CO2 削減目標を国家目標 ▲23.4% まで引き上げ",
            "改善基準告示 拘束時間 13h/日 の引用追加",
        ],  # 最大 5 件 — validator の error suggestion + warning suggestion から
        "is_chain_franchise": False,  # 第46条 vs 第65条 系列の文言切替
    },
)
```

## 6. 実装ファイル一覧

| ファイル | 種別 | 内容 |
|---|---|---|
| `core/export/ppt_writer.py` | 追記 | (a) `_COMPLIANCE_STEP_DEFS` 定数 (b) `_compliance_step_color(step)` (c) `_add_compliance_risk_step_body(slide, spec)` (d) `_add_chart_body` の dispatch (e) `_english_label` に "COMPLIANCE RISK" 追加 |
| `core/analytics/plan_draft.py` | 拡張 | (a) `generate_plan_draft(company_id, include_compliance_risk_slide: bool = True)` (b) docx 生成順序を ppt より前に移動（validator 実行用） (c) `_build_compliance_risk_slide(plan_result)` 関数追加 (d) `_build_ppt_slides` に slide を差し込み |
| `mcp_server/tools/clo_tools.py` | 拡張 | `logi_clo_plan_draft` に `include_compliance_risk_slide: bool = True` 引数追加（既存関数の挙動はデフォルトで Tier S4 ON） |
| `tests/core/test_export_writers.py` | 追記 | PPT スライド生成テスト 3 件 |
| `tests/core/test_validators_submission.py` | 追記 | 不要（validator 自体は触らない） |
| `tests/core/test_plan_draft_compliance_slide.py` | 新規 | plan_draft 統合テスト 5 件以上 |

合計目安: 新規テスト **8 件以上**（要件遵守）

## 7. 実装順序

1. `plans/compliance_risk_ppt.md`（本ファイル）作成
2. `core/export/ppt_writer.py` への新スライド追加（純粋関数・テストしやすい単位から）
3. `tests/core/test_export_writers.py` に PPT 単体テスト追加（赤→緑）
4. `core/analytics/plan_draft.py` の generate_plan_draft 拡張
5. `tests/core/test_plan_draft_compliance_slide.py` 新規（赤→緑）
6. `mcp_server/tools/clo_tools.py` の logi_clo_plan_draft 引数追加
7. `pytest -q` 全 pass
8. `ruff check` + `mypy` パス
9. Claude Desktop 実機確認（sample_manufacturing_01 で生成 → 該当スライド存在）
10. PR 作成

## 8. 衝突回避（並列セッション領域確認）

| 領域 | セッション | 触る/触らない |
|---|---|---|
| `core/io/decision_log_store.py`（新規） | A=Tier S1 | **触らない** |
| `core/analytics/operation_cockpit.py` | A=Tier S1 読み込み | **触らない** |
| `core/io/facility_store.py`（新規） | B=Tier S3 | **触らない** |
| `core/analytics/wait_time_heatmap.py` | B=Tier S3 | **触らない** |
| `core/export/ppt_writer.py` | **C=Tier S4（本セッション）専属** | 追記のみ・既存関数の引数シグネチャは変更しない |
| `core/analytics/plan_draft.py` | C=Tier S4（本セッション）専属 | 既存関数は **新引数のデフォルト値を従来挙動と同じにする** ことで後方互換確保 |
| `mcp_server/tools/clo_tools.py` | C=Tier S4（本セッション）専属 | `logi_clo_plan_draft` のみ拡張・他ツールは触らない |

並列セッションが `plan_draft.py` に手を入れる可能性は低いが、もし手を入れていればマージ時に競合する。**rebase 前に `git fetch origin && git log origin/main --oneline -10` で確認**。

## 9. Codex への確認事項（着手前確認方針）

タスク指示「ステップ確率の数値根拠については推測で埋めず None / 警告マーク扱いにする方針で Codex 確認」に従う。

確認事項:
1. ステップフロー 4 段（行政指導 → 勧告 → 公表 → 罰金）の **法文準拠表現**
   - 「公表」を独立ステップとするか、勧告/命令の中に内包するか
   - 100 万円罰金が「特定荷主 第50条 / 連鎖化 第69条」で正しいか
2. score → step マッピングの **閾値根拠の不在を注記すべきか**
   - 現案: 「内部評価」と明示注記
   - 代替案: 段階表示を完全に外し「現状の準拠率」のみ表示

→ Codex の検証は **本計画書作成後にユーザー判断で起動**（CLAUDE.md §9.2 の役割分担に従い、Tier S4 は本セッション専属。Codex を呼ぶ場合は健一に確認）。

**判断**: 着手前の Codex 起動は **しない**。理由:
- 法文ベースの 4 段は plans/phase55_update_proposal.md S4 で確定済（「行政指導→勧告→公表→100 万円罰金」）
- 数値推測の禁止は実装で `current_step` を限定列挙とし、確率値を一切付与しないことで担保済
- スライド注記で「本判定は当社の準拠率しきい値による内部評価」と明示すれば説明責任は確保

スコープ拡大時（例: 業種別の罰則実例追加）は Codex 並行確認を検討。

## 10. 完了基準（タスク指示準拠）

- [x] `plans/compliance_risk_ppt.md` 作成
- [ ] pytest 全 pass（新規 8 件以上）
- [ ] `logi_clo_plan_draft` で生成された PPT に compliance_risk_step スライドが含まれる（実機確認）
- [ ] Claude Desktop で `sample_manufacturing_01` の中長期計画生成 → 準拠率に応じた色で該当スライド出力確認
- [ ] PR 作成（タイトル: `feat(ppt): Tier S4 罰則リスクステップフロースライド追加`）
- [ ] マージ後 worktree 片付け

## 11. ロールバック判断基準

- 既存 PPT 生成テスト（test_write_clo_plan_ppt_creates_pptx 等）が壊れたら即ロールバック
- スライド数が想定外に増減して既存テストの `len(prs.slides) == N` 系を壊したら、新引数を従来挙動と同じデフォルトで切り戻し可能にする（`include_compliance_risk_slide=False` → 従来通り）

---

**最終決定者**: 健一
**最終更新**: 2026-05-17
