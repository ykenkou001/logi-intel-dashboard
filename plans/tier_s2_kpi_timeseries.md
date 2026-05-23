# Tier S2: KPI 時系列トラッキング 実装計画

**ステータス**: ドラフト v1.0（2026-05-23）
**目的**: フェーズ5.5 Tier S2 を最終ピースとして実装し、CLO の月次レビューで「悪化中か / 計画線に乗っているか」を一目で判定可能にする。
**完了条件**: pytest 全 pass / ruff check pass / Next.js build pass / cockpit に時系列ペイン追加 / HANDOFF + roadmap + dashboard_feature_guide 更新

---

## 1. 既存資産マッピング（実装着手前の確認）

| 既存 | 粒度 | 永続化 | 用途 |
|---|---|---|---|
| `OperationKpiSnapshot` ([core/analytics/operation_cockpit.py:237](../core/analytics/operation_cockpit.py#L237)) | 日次 | `outputs/cockpit_snapshots/<id>/<yyyymmdd>.json` | 当日 cockpit の delta_from_yesterday |
| `_load_prior_snapshot()` ([:1098](../core/analytics/operation_cockpit.py#L1098)) | 日次 | 直近 7 日のみ | 前日比のみ |
| `KpiHistoryEntry` ([core/static/sample_company.py:90](../core/static/sample_company.py#L90)) | 年度（fy） | profile JSON 同梱 | trend 検出 / Excel `kpi_history` 取込 |
| F2 `build_standardization_score()` | 都度計算 | なし | スナップショット非永続化 |
| J2 `build_waste_traps()` | 都度計算 | なし | スナップショット非永続化 |

**欠けているピース**: **月次粒度の時系列**。日次は持続するが集約なし、年度はあるが粒度が荒い。

## 2. 設計方針

**新規 `core/io/kpi_timeseries_store.py` を作る**（measure_run_store.py 拡張ではない）。
理由: 施策単位（measure_id 1 件 = 1 record）と KPI 月次（year_month × 指標）は次元が違う。 `decision_log_store.py` の jsonl + S3 backend + legacy 統合読出パターンを踏襲。

**最小機能セット（v1）**:
1. `MonthlyKpiSnapshot` Pydantic モデル（year_month / 5 KPI + F2 + J2 罠件数）
2. `append_monthly_snapshot()` / `load_monthly_snapshots()` / `query_monthly_kpi_series()`
3. `core/analytics/kpi_timeseries.py` で日次 cockpit_snapshots を月次にロールアップする `build_monthly_from_daily_snapshots()`
4. `core/analytics/kpi_timeseries.py` で「悪化アラート」を生成する `detect_kpi_deterioration()`（前月比悪化 + 3 ヶ月連続悪化）
5. REST `GET /api/v1/clo/kpi-timeseries/{company_id}` + MCP `logi_clo_kpi_timeseries`
6. Web `/dashboard/cockpit` に時系列ペインを追加（既存ページの下部に Recharts LineChart）

**v1 で含めないこと**（フェーズ 6.0 以降）:
- 月次会議で更新される計画値との差分（plan_draft の expected_effect_jpy を一次値として使い、月次計画更新は v2）
- decision_log との自動連動
- CSV/PPT エクスポート（既存 export レイヤを再利用するのは別 PR）

## 3. データモデル詳細

```python
# core/io/kpi_timeseries_store.py

class MonthlyKpiSnapshot(BaseModel):
    """1 ヶ月分の KPI スナップショット（cockpit_snapshots 日次の月平均 + F2/J2）。"""

    model_config = ConfigDict(frozen=True)

    company_id: str
    year_month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="ISO 年月 YYYY-MM")

    # KPI 5 種（cockpit と同形）
    load_factor_pct: float | None = None
    wait_time_avg_min: float | None = None
    wait_time_max_min: float | None = None
    handling_time_avg_min: float | None = None
    co2_intensity_g_per_tonkm: float | None = None

    # F2 標準化スコア
    standardization_score: float | None = Field(default=None, ge=0, le=100)

    # J2 罠件数（high/medium/low の合計）
    waste_trap_count_high: int = Field(default=0, ge=0)
    waste_trap_count_medium: int = Field(default=0, ge=0)
    waste_trap_count_low: int = Field(default=0, ge=0)

    # メタ
    source: Literal["rolled_up_from_daily", "manual_entry", "merged"] = "rolled_up_from_daily"
    daily_sample_count: int = Field(default=0, ge=0, description="ロールアップ元の日次サンプル数")
    recorded_at: datetime
```

```python
# core/analytics/kpi_timeseries.py

class KpiTimeSeriesResult(BaseModel):
    company_id: str
    months: list[MonthlyKpiSnapshot]               # 古→新 順 / 最大 24 ヶ月ウィンドウ
    deteriorations: list[KpiDeteriorationAlert]    # 悪化アラート
    citations: list[Citation]
    freshness_warnings: list[str]


class KpiDeteriorationAlert(BaseModel):
    metric: str                                    # 'load_factor_pct' 等
    severity: Literal["watch", "warn", "critical"]
    direction: Literal["down", "up"]               # 積載率は down が悪、荷待ちは up が悪
    consecutive_months: int                        # 連続悪化月数
    latest_value: float | None
    baseline_value: float | None                   # 3 ヶ月前 or plan_draft 由来
    delta_pct: float | None                        # baseline 比 %（None なら不明）
    message: str                                   # CLO 説明文
```

## 4. 悪化判定ルール（v1）

| 指標 | 悪化方向 | watch | warn | critical |
|---|---|---|---|---|
| load_factor_pct | 低下 | -2pt 以上 | -5pt 以上 | -10pt 以上 or 3 ヶ月連続低下 |
| wait_time_avg_min | 増加 | +10% 以上 | +25% 以上 | +50% 以上 or 3 ヶ月連続増 |
| handling_time_avg_min | 増加 | +10% 以上 | +25% 以上 | +50% 以上 or 3 ヶ月連続増 |
| co2_intensity_g_per_tonkm | 増加 | +5% 以上 | +10% 以上 | +20% 以上 or 3 ヶ月連続増 |
| standardization_score (F2) | 低下 | -3pt | -10pt | -20pt or 連続低下 |
| waste_trap_count_high | 増加 | +1 件 | +3 件 | +5 件 or 連続増 |

baseline = 3 ヶ月前（あれば）または最古 snapshot。
業界感覚レンジ（memory `reference_industry_sense_ranges`）に整合する閾値（F2 PT は感覚値・他は業界平均改善幅から逆算）。

## 5. ファイル変更計画

### 新規ファイル
- `core/io/kpi_timeseries_store.py`（≒180 行）
- `core/analytics/kpi_timeseries.py`（≒250 行）
- `tests/io/test_kpi_timeseries_store.py`（≒120 行）
- `tests/core/test_kpi_timeseries_analytics.py`（≒200 行）

### 既存ファイル変更
- `api/routers/clo.py`: `/kpi-timeseries/{id}` 追加
- `mcp_server/tools/clo_tools.py`: `logi_clo_kpi_timeseries` 追加
- `web/lib/api.ts`: 型 3 種（MonthlyKpiSnapshot / KpiTimeSeriesResult / KpiDeteriorationAlert）追加 + fetcher
- `web/app/dashboard/cockpit/page.tsx`: 下部に時系列ペイン追加（Recharts LineChart）
- `web/lib/labels.ts`: 悪化アラート severity 日本語化

### ドキュメント更新
- `HANDOFF_NEXT_SESSION.md`: Tier S2 完了反映 + フェーズ5.5 全完了
- `docs/roadmap.md`: §フェーズ5.5 進捗反映
- `docs/dashboard_feature_guide.md`: 「KPI 時系列ペイン」セクション追加
- `CLAUDE.md`: §3 現在フェーズ更新（フェーズ5.5 完了 → 次は記事化のみ）

## 6. 検証チェックリスト

- [ ] pytest 全 pass（既存 + 新規 ≒320 件）
- [ ] ruff check pass
- [ ] mypy（strict）pass
- [ ] Next.js build 全ページ pass
- [ ] cockpit ページ ローカル起動で時系列ペイン表示確認（scripts/dev_api.ps1 + dev_web.ps1）
- [ ] 4 業種サンプルプロフィール（sample_mfg_01 等）すべてで月次データなしの場合のフォールバック確認
- [ ] CLAUDE.md §7「Step 検証ルール」: MCP 実機呼び出しで現実的な数値が返ることを確認

## 7. 持ち越し（v2 候補・別 PR）

1. 月次計画値（プランナーが更新できる目標線）の保存と差分表示
2. decision_log との連動（悪化アラートを cockpit カードに自動エスカレーション）
3. CSV / PPT エクスポート（既存 export レイヤ拡張）
4. プラン残差予測（線形回帰 + 燃料変動シナリオ）

## 8. Codex レビュー依頼との関係

`tasks/codex_review_request_tier_s2.md`（別途ユーザーが手動で ChatGPT 投入）と並行で Claude 側で本計画に沿って実装着手。Codex 結果が返り次第、Critical / Major 指摘は本計画に反映（v1.1）し、必要なら実装途中で軌道修正する。

## 9. Codex 独立評価（2026-05-23）との対応（CLAUDE.md §9.4 準拠）

Codex 評価は [tier_s2_kpi_timeseries_codex_review.md](tier_s2_kpi_timeseries_codex_review.md) を参照。

| Codex 勧告 | Claude 判断 | 反映先 |
|---|---|---|
| ① 新規 `core/io/kpi_timeseries_store.py` を作る（measure_run_store 拡張ではない） | ◎ 採用 | 本計画 §2 と一致 |
| ② `OperationKpiSnapshot` / `KpiHistoryEntry` / F2/J2 は「入力ソース」として再利用、新 store 側で月次レコードに正規化 | ◎ 採用 | §2 / §3 と一致 |
| ③ 24 ヶ月ウィンドウ + decided_at 降順ソート相当 + 同月再記録は append+最新採用 | ◎ 採用 | §3 / 実装の `load_monthly_snapshots()` 仕様 |
| ④ 悪化アラートの baseline は「plan_draft_freeze ／ target_proposal 由来の計画値」推奨 | △ 修正のうえ採用 | v1 は「3 ヶ月前または最古月」ベースで実装。計画値線は v2（持ち越し §7-#1） |
| ⑤ Web 配置は `/dashboard/cockpit` に 12 ヶ月時系列ペイン追加 | ✕ 却下のうえ別案採用 | 別ページ `/dashboard/kpi-timeseries` を新設し 24 ヶ月可視化（cockpit はすでに重いため。ナビからの導線で日次↔月次は接続） |
| ⑥ 閾値は計画比 ベース（例: 積載率 -1.0pp watch / -3.0pp warn / -5.0pp critical） | △ 修正のうえ採用 | v1 は baseline 比の絶対 pp / % 閾値（積載率 -2pp watch / -5pp warn / -10pp critical）。計画線が整った段階で計画比方式に切替 |
| ⑦ 業界感覚レンジ（積載率 38→50%）と整合する閾値設計 | ◎ 採用 | §4 閾値表が業界感覚レンジに整合（積載率の年 1.5pp 改善目安に対し watch -2pp は妥当） |
| ⑧ 後方互換ガード: 既存 OperationKpiSnapshot / KpiHistoryEntry / cockpit ページの形式を変えない | ◎ 採用 | 新 store のみ追加。既存ファイルは触らない |

**不採用理由の補足（⑤）**: Codex 案では cockpit に追加ペインを置くのが「日次↔月次の体験統合」観点で優位。しかし cockpit ページは既に 3 軸カード + 意思決定ボタン + decision_log 履歴を保持しており、月次 24 ヶ月の折れ線（5 系列）を追加すると視覚的負荷が大きい。代わりにナビバーに「月次推移」リンクを置き、cockpit カードからのワンクリック遷移で接続する設計を採用した。
