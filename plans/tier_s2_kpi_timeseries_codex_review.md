# Tier S2 KPI 時系列トラッキング Codex 独立評価

**作成日**: 2026-05-23
**作成者**: Codex
**位置づけ**: フェーズ 5.5 Tier S2「KPI 時系列トラッキング」の実装着手前レビュー。特に「既存資産を再利用するか、新規 store を作るか」の方針判断を Claude に渡すための調査報告。

---

## 1. 結論

`measure_run_store.py` 拡張ではなく、`core/io/kpi_timeseries_store.py` 新設を推奨する。

理由は、既存 `measure_run_store.py` が施策単位の実行記録である一方、Tier S2 は `月次 x KPI 指標 x 計画/実績/アラート` の時系列管理であり、主キーも更新頻度も利用目的も異なるためである。

`OperationKpiSnapshot`、Excel `kpi_history`、F2/J2 スコアは「入力ソース」として再利用し、S2 store 側で月次レコードに正規化するのが後方互換上もっとも安全。

---

## 2. 既存資産の責務確認

| 既存資産 | 現在の責務 | S2 での扱い |
|---|---|---|
| `core/analytics/operation_cockpit.py` `OperationKpiSnapshot` | 日次 cockpit の状態保存。`outputs/cockpit_snapshots/<company_id>/<yyyymmdd>.json` に当日 1 件保存 | 月次 rollup の入力ソースとして使う。既存保存形式は変えない |
| `_load_prior_snapshot()` / `_compute_delta()` | 直近 7 日以内の prior snapshot と前日差分を計算 | 月次トレンドの主ロジックには流用しない。日次 cockpit 用に温存 |
| Excel `kpi_history` / `KpiHistoryEntry` | `fy, metric, value, unit` の年度粒度履歴。テンプレから取込可能 | 初期値・手入力実績の補助ソース。月次 schema に破壊変更しない |
| `measure_run_store.py` | `MeasureExecutionRecord` を `outputs/measure_runs/<company_id>.json` に保存。J2 waste trap の施策実行記録 | S2 store にはしない。J2 の入力として参照するだけ |
| `decision_log_store.py` | jsonl append + S3 backend + legacy 統合読出 | S2 store の実装パターンとして踏襲 |
| F2 `standardization_score.py` | 呼び出し時点の標準化スコアを算出 | 月次 snapshot 作成時に値を保存する |
| J2 `waste_trap.py` | 呼び出し時点の罠検出を算出 | 月次 snapshot 作成時に high/medium/low 件数を保存する |

---

## 3. 推奨アーキテクチャ

### 3.1 新規 store

新規 `core/io/kpi_timeseries_store.py` を作る。

推奨する永続化形式:

- `outputs/kpi_timeseries/<company_id>.jsonl`
- 1 行 1 月次 snapshot
- `LOGI_STORAGE_BACKEND=s3` のときは `decision_log_store.py` と同様に S3 既存内容を読んでから append/publish
- query は年月降順/昇順、months 上限、metric filter を持つ

推奨モデルの最小構成:

```python
class MonthlyKpiSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    company_id: str
    year_month: str  # YYYY-MM

    load_factor_pct: float | None = None
    wait_time_avg_min: float | None = None
    wait_time_max_min: float | None = None
    handling_time_avg_min: float | None = None
    logistics_cost_ratio_pct: float | None = None
    co2_intensity_g_per_tonkm: float | None = None

    standardization_score: float | None = None
    waste_trap_count_high: int = 0
    waste_trap_count_medium: int = 0
    waste_trap_count_low: int = 0

    planned_values: dict[str, float | None] = Field(default_factory=dict)
    source: Literal["rolled_up_from_daily", "manual_kpi_history", "computed", "merged"]
    daily_sample_count: int = 0
    recorded_at: datetime
```

### 3.2 analytics 層

新規 `core/analytics/kpi_timeseries.py` に以下を置く。

- `build_kpi_timeseries(company_id, months=12)`
- `rollup_cockpit_snapshots(company_id, year_month)`
- `merge_manual_kpi_history(profile)`
- `detect_kpi_deterioration(series)`
- `build_kpi_timeseries_summary(result)`

REST / MCP / Web はこの analytics 層を呼ぶだけにし、悪化判定や source merge のビジネスロジックは `api/` や `web/` に置かない。

---

## 4. データソース統合方針

### 推奨案

`cockpit_snapshots` と Excel `kpi_history` を直接足し合わせず、S2 store で正規化する。

- `cockpit_snapshots`: 日次実測の rollup。荷待ち、荷役、積載率に強い
- `kpi_history`: ユーザー入力の実績・年度履歴。初期状態や補助線に使う
- F2/J2: 月次 snapshot 作成時点の算出結果を保存する

### 代替案

初期版では `kpi_history` を主ソースにし、`cockpit_snapshots` は参考値にする。実装は速いが、自動トラッキング感は弱い。

### 不採用案

`cockpit_snapshots` を唯一の真実にする。現状の日次 snapshot は前日差分用で、物流コスト比率や F2/J2 履歴を持たない。

---

## 5. 悪化アラート設計

### 前回計画値の出所

推奨順:

1. `plan_draft_freeze` または月次会議で確定した計画値を S2 store の `planned_values` に保存
2. `target_proposal` の数値目標を初期計画値として採用
3. 計画値がない場合は 3 か月前または最古月を baseline にする

`expected_effect_jpy` は施策の財務効果であり、KPI の計画値そのものではないため、荷待ち時間・積載率・物流コスト比率の plan line として直接使わない。

### 初期閾値案

| 指標 | 悪化方向 | watch | warn | critical |
|---|---|---|---|---|
| 積載率 | 低下 | 計画比 -1.0pp | 計画比 -3.0pp | 計画比 -5.0pp or 3 か月連続低下 |
| 荷待ち平均 | 増加 | 計画比 +10% or +10分 | 計画比 +25% or +20分 | 計画比 +50% or 3 か月連続増 |
| 荷待ち最大 | 増加 | +15分 | +30分 | 120分超が継続 |
| 物流コスト比率 | 増加 | +0.3pp | +0.5pp | +1.0pp or 3 か月連続増 |
| F2 標準化スコア | 低下 | -3pt | -10pt | -20pt or 3 か月連続低下 |
| J2 high 罠件数 | 増加 | +1件 | +3件 | +5件 or 3 か月連続増 |

業界感覚レンジと特に整合させるべき指標:

- 積載率: 業界平均 38%、目標 50%、年 1.5pp 程度の改善幅
- 物流コスト比率: JILS 物流コスト調査由来の業種別平均
- 荷待ち/荷役: 改善基準告示や 120 分超過の扱い

---

## 6. Web 表示方針

### 推奨案

`/dashboard/cockpit` に 12 か月 KPI トレンドペインを追加する。

理由:

- Tier S2 は「CLO の継続運用」を cockpit に接続する機能
- 既存 cockpit は当日 snapshot、前日比、decision log をすでに表示している
- 別ページにすると、日次判断と月次レビューが分断される

表示案:

- 既定 12 か月
- ユーザー選択で 6 / 12 / 24 か月
- `LineChart` または `ComposedChart`
- KPI 指標はタブまたは segmented control で切替
- アラートは chart 直下に severity badge 付きで表示

### 代替案

`/dashboard/kpi-history` を新設する。データ量が増える Phase 6 以降には有効だが、S2 初期版では cockpit 内ペインがよい。

### 不採用案

全期間固定表示。データが増えると読みづらく、CLO 月次レビューには 12 か月 window の方が実務的。

---

## 7. 後方互換ガード

必須:

- `OperationKpiSnapshot` の既存 field と保存先を変えない
- `_persist_snapshot()` の挙動を変えない
- Excel `kpi_history` の既存列 `fy, metric, value, unit` を壊さない
- cockpit の既存 summary / 3 判断カード / decision log 表示を壊さない
- REST 既存 endpoint の response metadata を破壊変更しない

避けるべき変更:

- `kpi_history` に月次列を直接追加する
- `OperationKpiSnapshot` に plan line / F2 / J2 を詰め込む
- `measure_run_store.py` に KPI 月次 record を混在させる

---

## 8. Claude への実装前確認ポイント

Claude 側で確認してほしい点:

1. 既に作成済みの `plans/tier_s2_kpi_timeseries.md` が、`measure_run_store.py` 拡張案から新規 `kpi_timeseries_store.py` 案へ完全に更新されているか
2. `core/analytics/kpi_timeseries.py` が API/Web ではなく core 層にビジネスロジックを置いているか
3. 物流コスト比率を v1 に入れる場合、どの入力から取るかが明確か
4. F2/J2 は「都度再計算」ではなく、月次 snapshot 作成時点の値を保存する設計になっているか
5. 悪化アラートが前月比だけに閉じず、計画比または 3 か月連続悪化を扱える余地を残しているか
6. 既存 Excel `kpi_history` を破壊変更していないか
7. Web を `/dashboard/cockpit` に足す場合、既存 UI を押し下げすぎず、折りたたみまたは下部ペインにしているか

---

## 9. Claude への調査報告用プロンプト

以下を Claude にそのまま渡す。

```text
フェーズ5.5 Tier S2「KPI 時系列トラッキング」について、Codex 独立評価を plans/tier_s2_kpi_timeseries_codex_review.md に追加しました。

あなたの既存実装計画 plans/tier_s2_kpi_timeseries.md と、現在の実装差分を照合してください。

確認してほしいこと:
1. measure_run_store.py 拡張ではなく core/io/kpi_timeseries_store.py 新設に寄せる方針で問題ないか
2. OperationKpiSnapshot / cockpit_snapshots は日次 cockpit 用として後方互換を維持し、月次 rollup の入力に限定できているか
3. Excel kpi_history は既存 fy, metric, value, unit を壊さず、manual source として扱えているか
4. F2/J2 は都度再計算表示ではなく、月次 snapshot 作成時点の値を保存する設計になっているか
5. 悪化アラートの baseline を expected_effect_jpy に寄せすぎていないか。target_proposal / plan_draft_freeze / 月次計画値を plan line として扱う余地があるか
6. 物流コスト比率の実績値ソースが未定義なら、v1 では optional にするか、入力 source を明記してください
7. /dashboard/cockpit 追加ペインが既存 cockpit UI を破壊しないか。別ページ化が必要な場合は理由を示してください

出力は以下の形式でお願いします:
- Codex 評価への採用 / 修正のうえ採用 / 却下
- 実装計画への反映箇所
- 追加で直すべきファイル
- リスクが残る点
- 次に Codex にレビュー依頼すべき観点
```

