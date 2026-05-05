# 次セッションへの引継ぎ（2026-05-06 時点）

> このファイルを最初に読み、`uv sync` 実行後に c.4 から着手する。

---

## 🎯 次セッションのタスク: フェーズ5.0 段階 c — c.4 既存接続検証 + c.6 F2/J2 スコアリング

### 全体像

`plans/b-c-flickering-pixel.md`（健一の `~/.claude/plans/` 配下にある計画書）の **段階 c** のうち、c.1-c.3 は完了済（PR #11 マージ済）。次は **c.4 既存接続検証** と **c.6 F2 標準化スコア + J2 罠スコア** を実装する。c.5 個社差分永続化は c.3 で実装済（`core/io/override_store.py`）。c.7 MCP/REST と c.8/c.9 は本セッションのスコープ外。

### 完了済の前提資産（直前 PR）

| PR | 内容 |
|---|---|
| #11 (merged) | c.1 マトリクス + c.2 データモデル + c.3 resolve / Override 永続化 — `core/playbook/industry_packages.py` + `core/io/override_store.py` + テスト 55 件 |
| #10 (merged) | フェーズ4.5 B 用途別テンプレ生成（daily/monthly/annual） |
| #9 #8 #7 (merged) | b 段階：J3 デイリーコックピット中核 / Web 画面 / シナリオテスト |

---

## ⚠️ 並行作業の注意（最初に必ず確認）

健一は **Claude / Codex を別セッションで並行起動** して別領域を担当させる運用。

- 現時点で他領域に並行作業の予定はないが、本セッション開始前に健一に「Codex 並行作業はあるか？」を確認する
- 衝突可能性が高い共有領域:
  - `pyproject.toml` の dependencies — どちらも触る可能性。先に触る側が他方に通知する想定で、健一に都度確認する
  - 統合テスト（`tests/api/`, `tests/core/test_plan_draft*.py`）

詳細 → メモリ `feedback_codex_parallel_collaboration.md` / CLAUDE.md §9

**`main` への直接 push は禁止**。必ず feature ブランチ + PR 経由。

---

## 📋 必読ドキュメント（着手前）

1. **CLAUDE.md** — プロジェクト全体方針。特に §1.5 ミッション宣言 / §6.5 dev サーバ起動ルール / §7 検証ルール / §9 Codex 協業方針
2. **plans/b-c-flickering-pixel.md** §段階 c.6 — F2/J2 ロジック仕様（健一の `~/.claude/plans/b-c-flickering-pixel.md`）
3. **core/playbook/industry_packages.py** — c.1-c.3 で構築した IndustryPackage / Override 4 分類 / resolve_company_package
4. **core/io/override_store.py** — Override JSON 永続化（save_override / load_override）
5. **core/playbook/measures.py** ALL_MEASURES — 全 10 施策の applicable_industries フィールド構造
6. **core/static/industry_benchmarks.py** — baseline 数値の出典
7. **memory `reference_industry_sense_ranges.md`** — 業界感覚レンジ表（妥当性判定用）

---

## 🛠 実装スコープ

### c.4: 既存資産との接続検証（軽量・最初に着手）

**目的**: `core/playbook/industry_packages.py` で参照する既存資産との整合性を CI で守る。

実装ファイル候補:
- `tests/core/test_playbook_industry_packages.py` を拡張（新規ファイルは作らない）
- 必要なら `core/playbook/industry_packages.py` に検証ヘルパを追加

検証項目:
1. **measure_ids ↔ ALL_MEASURES.applicable_industries 整合性**
   - 各業種の `IndustryPackage.measure_ids` が `measures.ALL_MEASURES` の `applicable_industries` に当該業種を含む施策と矛盾なく対応していることをテストで確認
   - 例: chain_franchise パッケージに `warehouse_dx_wms` が混入していないか（既存テストで確認済だが、ALL_MEASURES 側からの逆検証も追加）
2. **plan_template_paths が実在するか**
   - 現在 manufacturing のみパス指定済、他 3 業種は空。`core/templates/clo_plan_examples/` 配下の既存テンプレファイル名で埋められる範囲を埋める
   - 該当ファイルが無い場合は空のままで OK（推測でファイル名を作らない）
3. **industry_benchmarks.py との接続**
   - `LOGISTICS_COST_RATIO[industry]` が IndustryPackage.kpis の `logistics_cost_revenue_ratio_pct.baseline_value` と整合（c.1 で _common_kpis 経由で実装済 → テストで確認）

c.4 は実装が小さい想定（テスト 5-10 件追加程度）。コミットは「test(playbook): c.4 既存資産接続の整合性検証」。

### c.6: F2 標準化スコア + J2 罠スコア（中核）

**新規ファイル 2 件**:
- `core/analytics/standardization_score.py` — F2
- `core/analytics/waste_trap.py` — J2

**新規テスト 2 件**:
- `tests/core/analytics/test_standardization_score.py`（または既存 tests/core/ 直下）
- `tests/core/analytics/test_waste_trap.py`

#### F2 標準化スコア（plans/b-c-flickering-pixel.md §c.6 F2 完全反映）

```python
class StandardizationScoreResult(BaseModel):
    company_id: str
    base_package_category: JsicCategory
    coverage_pct: float
    deviation_count_unmanaged: int       # NEW: 減点対象のみ
    deviation_count_total: int           # NEW: 全 override
    missing_kpi_ids: list[str]
    missing_measure_ids: list[str]
    score: float
    rationale: list[str]
    citations: list[Citation]

def compute_standardization_score(profile, override) -> StandardizationScoreResult: ...
```

**ロジック（unmanaged のみ減点）**:
```python
coverage_pct = (
    (実装済 KPI 数 + 実装済 施策数)
    / (標準 KPI 総数 + 標準 施策総数)
) * 100

deviation_penalty = (
    sum(5 for entry in override.entries if entry.category == "unmanaged_deviation")
    + sum(3 for entry in override.entries
          if entry.category == "temporary_exception" and entry.expires_at < today)
)
# approved_better_practice / required_localization は減点なし

bonus = (
    +10 if all(必須 KPI 実装) and 月次会議定着
    +5 if approved_better_practice 件数 >= 2
)

score = max(0, min(100, coverage_pct - deviation_penalty + bonus))
```

**「実装済」の判定**:
- KPI 実装済 = `profile.kpi_history` に該当 metric_id を含む `KpiHistoryEntry` が 1 件以上存在
- 施策実装済 = ?（次の課題：施策の実装ステータスを保持する仕組みがまだ無い）
  - 暫定: Override の `target_kind="measure"` × `category="approved_better_practice"` を採用済とみなす
  - 別案: `decision_log` から `decision="adopt"` の measure_id を引く（`outputs/decisions/<id>.jsonl` 参照）

着手前に健一に「施策実装ステータスをどう判定するか」を確認すること。

#### J2 罠スコア（plans/b-c-flickering-pixel.md §c.6 J2 完全反映）

```python
class WasteTrapItem(BaseModel):
    measure_id: str
    invested_jpy: int | None
    expected_effect_jpy: int | None
    actual_effect_jpy: int | None
    months_since_start: int | None
    trap_severity: Literal["low", "medium", "high"]
    suspected_root_cause: Literal[
        "scale_misfit", "resource_missing", "governance_gap", "wrong_kpi",
        "external_factor",
        "data_quality",            # NEW (Codex 勧告⑤)
        "adoption_resistance",     # NEW
        "implementation_quality",  # NEW
        "unknown",
    ]
    suggested_remediation: str
    investment_freeze_recommended: bool

def detect_waste_traps(profile, plan, decision_log) -> WasteTrapResult: ...
```

**6 軸セーフガード（Codex 勧告④・誤検知抑止）**:
```python
def _trap_severity(invested, expected, actual, months_since_start, ...):
    # ① 立ち上げ期間が短い
    if months_since_start is None or months_since_start < 6: return "low"
    # ② データ欠損
    if data_completeness < 0.5: return "low"
    # ③ サンプル数不足
    if measured_count < min_sample_size: return "low"
    # ④ 季節性影響中
    if seasonal_factor_active: return "low"
    # ⑤ 外部要因（燃料急騰等）
    if external_event_active: return "low"
    # ⑥ 投資回収前
    if months_since_start < payback_months_estimated: return "low"

    ratio = (actual or 0) / (invested or 1)
    if ratio <= 0.3 and (expected / invested) >= 2.0: return "high"
    if 0.3 < ratio < 0.7: return "medium"
    return "low"

investment_freeze_recommended = (
    trap_severity == "high"
    and suspected_root_cause in ("scale_misfit", "wrong_kpi", "implementation_quality")
)
```

**入力**:
- `profile`: CompanyProfile
- `plan`: PlanDraftResult（`core/analytics/plan_draft.py` の戻り値）— 施策の expected_effect_jpy / typical_investment_jpy 等
- `decision_log`: `outputs/decisions/<id>.jsonl` の DecisionRecord 一覧（`core/analytics/operation_cockpit._load_pending_decisions` を参考に拡張）

actual_effect_jpy は `kpi_history` の改善幅から逆算する想定（コスト削減施策なら物流コスト/売上比率の改善 × 売上）。複雑になるなら **当初は actual=None 許容で初版を出す** のもアリ。健一に方針確認。

---

## 🔧 ブランチ・コミット戦略

- ブランチ名: `feature/phase-5.0-scoring-engines`
- コミット粒度推奨:
  - commit 1: c.4 既存接続検証（テスト追加 + 必要なら industry_packages.py に検証ヘルパ）
  - commit 2: F2 標準化スコア（standardization_score.py + テスト）
  - commit 3: J2 罠スコア（waste_trap.py + テスト）
- 1 PR にまとめる想定（推定行数 1500〜2000）
- PR タイトル: `feat(analytics): c.4-c.6 標準化スコア (F2) + 罠スコア (J2)`

---

## ✅ 検証チェックリスト

着手前 → 着手後の順:

- [ ] `git pull origin main` で最新化
- [ ] `uv sync` で依存最新化
- [ ] `uv run pytest --tb=short -q` がベースライン pass（直近 main で 700+ 件全 pass のはず）
- [ ] `uv run ruff check` クリーン
- [ ] 新規テスト: F2 / J2 各 10 件以上
- [ ] **境界条件テスト**: F2 完全一致 ≥ 90 / Override 5 件で 50 / 未実装 3 件以上で 30 以下
- [ ] **J2 セーフガード**: months_since_start=0 の擬似データで trap_severity="low" 固定
- [ ] **F2 単調性**: override 件数を 0,1,2,5,10 で減点対象（unmanaged）のみ単調減少、approved_better_practice は減点なし
- [ ] PR 説明に「Codex 議論で確定した修正点」と「Claude 単独判断」を区別して書く（CLAUDE.md §9.4）

---

## 🧠 Codex 協業の活用ポイント

CLAUDE.md §9.1 に従って、以下のタイミングで Codex に相談を **積極的に** する:

1. **F2 のスコア重み（5pt / 3pt / 10pt / 5pt）の妥当性** — 業界実績ベースで Codex に評価依頼。ALl 0/100 に偏らないか単調性検証の助言を求める
2. **J2 のセーフガード閾値** — `months_since_start < 6`、`data_completeness < 0.5` 等の値が業界実態と整合するか
3. **施策実装ステータスの判定方法** — 上記「着手前確認事項」で健一に確認 → 案が固まったら Codex にレビュー依頼

呼出: `/codex setup` で疎通確認 → `/codex rescue` または `codex:codex-rescue` agent

---

## 📝 既存コードからの参考パターン

- **Pydantic v2 モデル + frozen ConfigDict**: `core/playbook/industry_packages.py` のパターン
- **citations 構築**: `core/analytics/feasibility_check.py` の `citations=[logistics_efficiency_law_citation(), ...]`
- **freshness_warnings**: `core/static/_freshness.all_warnings()`
- **build_*_summary 関数**: feasibility_check.build_feasibility_summary が良いお手本

---

## 🚫 触らないこと

- `core/playbook/measures.py` の ALL_MEASURES 編集（ALL_MEASURES の構造変更は別 PR にする）
- `core/io/template_writer.py`（B 用途別テンプレと同じファイル — 触る場合は健一確認）
- `web/` 配下 — c.7 以降のスコープ
- `mcp_server/tools/clo_tools.py` — c.7 で MCP ツール追加するときに触る

---

## 完了の定義

- F2 / J2 のロジックがコード化され、サンプル4社（製造/卸/小売/連鎖化）で動作する
- pytest 700+ 全 pass + 新規 30+ 件全 pass
- ruff check クリア
- PR を `feature/phase-5.0-scoring-engines` で作成し、Codex の助言反映点を PR 説明に明記
- HANDOFF_NEXT_SESSION.md を c.7（MCP/REST 公開）向けに更新

---

## 📦 リポジトリ整理（2026-05-06）

ローカルブランチを整理済（main のみ残存）。remote には `origin/feature/phase-5.0-industry-packages` が orphan として残るが、これは「リフレーミング commit ef30b2e」が main 取込されなかったため。次セッションで触る必要なし（必要なら健一が remote から削除）。

untracked: `docs/notebooklm/`, `docs/overview_for_review.md`, `docs/zenn_drafts/` は健一の WIP（触らない）。
