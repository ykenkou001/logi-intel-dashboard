# Tier S3: 報告単位 Facility 管理レイヤ 詳細計画

**ブランチ**: `docs/facility-store`（worktree: `../logi-intel-dashboard.facility-store`）
**起票日**: 2026-05-17
**起票方法**: フェーズ 5.5 並列実装計画（セッション B 担当）
**並列進行**: セッション A（Tier S1 DecisionLog）/ セッション C（Tier S4 罰則 PPT）

---

## 1. 目的

様式第5 定期報告で実務負荷になる「**施設・測定期間・把握条件・除外理由**」を構造化して管理し、`wait_time_heatmap` 出力を施設単位に紐付けられる状態を作る。

法令上は「**測定単位**」が論点になりやすい領域:

- 改善基準告示の遵守判定は「測定対象施設」「測定期間」「除外理由（改修・新設等）」を明示することが求められる
- 様式第5 Ⅳ セクションの計測データは「施設ごとに測定期間を揃えること」「除外理由を必ず注記すること」が記載要件
- 寄託先（特定倉庫業者・物流子会社）は自社測定外であり、扱いを明確化する必要がある

---

## 2. CLAUDE.md §1.5 整合性

| 7 本柱 | 効果 |
|--------|------|
| Compliance Assurance | ◎ 測定単位を構造化し、提出時の説明責任を担保 |
| Defensibility | ◎ 「どの施設の・いつの・どの条件の」測定値かを記録 |
| Continuous Operation | ○ wait_heatmap を施設単位で継続監視可能に |
| Decision Support | ○ 罠検出（J2 waste_traps）を施設粒度で評価する地ならし |

---

## 3. データモデル設計

### 3.1 Facility（新規）

`core/io/facility_store.py` に Pydantic v2 モデルとして定義。

```python
class FacilityMeasurementPeriod(BaseModel):
    """測定期間（様式第5 Ⅳ で必須）。"""
    start_on: date
    end_on: date
    unit_label: str  # 例: "月次", "四半期", "年次"


class Facility(BaseModel):
    """報告単位 1 施設。"""
    facility_id: str       # 例: "fac_mfg01_tokyo_dc"（英数字 + アンダースコア）
    company_id: str        # CompanyProfile.company_id への参照
    name: str              # 施設名（例: "東京流通センター"）
    address: str           # 住所（任意精度）
    prefecture: str        # 都道府県名（正式名称）
    industry_code: str     # JSIC 4 桁（施設単位で別業種となる場合に備える）
    site_name: str | None  # CompanyProfile.sites[].name と WaitTimeRow.site_name の連結キー
    measurement_period: FacilityMeasurementPeriod
    measurement_conditions: list[str]  # 例: ["ドライバー手動計測", "パレット便のみ対象"]
    exclusion_reasons: list[str]       # 例: ["2025-04 改修工事中", "夜間便は対象外"]
    is_consigned_warehouse: bool       # 寄託先か（自社測定外か）
    notes: str | None                  # 補足（個別の事情）
    created_at: datetime
    updated_at: datetime
```

### 3.2 保存形式

- 保存先: `outputs/facilities/<company_id>.json`
- 1 ファイル = 1 社の全施設リスト `list[Facility]`
- LOGI_STORAGE_BACKEND=s3 のとき S3 にも複製（`measure_run_store.py` と同じ pattern）
- `LOGI_OUTPUTS_DIR` を実行時解決（テスト・本番で base_dir 差し替え可能）

### 3.3 既存 wait_time_rows との連結キー

`WaitTimeRow.site_name`（既存）⇄ `Facility.site_name`（新規）で連結する。

**理由**: WaitTimeRow を破壊変更すると下流（plan_draft, periodic_report, docx_form5_writer）に大量の修正が波及するため、**新規キー `facility_id` を WaitTimeRow に追加せず**、`site_name` で間接的に解決する。

トレードオフ:
- ❌ 同一施設名が複数施設で重複したらマッチ衝突
- ✅ 既存数値挙動は完全互換、CompanyProfile を一切変更しない

---

## 4. wait_time_heatmap 拡張

### 4.1 API シグネチャ

```python
def build_wait_time_heatmap(
    profile: CompanyProfile,
    facility_id: str | None = None,  # 新規。指定時のみ該当施設の site_name でフィルタ
) -> HeatmapResult: ...
```

### 4.2 facility_id 指定時の挙動

1. `load_facility(facility_id, company_id=profile.company_id)` で Facility をロード
2. `facility.site_name` が `None` なら ValueError（測定単位未紐付け）
3. `profile.wait_time_rows` を `row.site_name == facility.site_name` でフィルタしてから集計
4. HeatmapResult に `facility_id` / `facility_name` / `measurement_period` / `exclusion_reasons` を任意フィールドとして追加（既存フィールドは保持）

### 4.3 後方互換

- `facility_id=None`（デフォルト）→ 既存挙動（全 site 集計）
- 既存テストはシグネチャ変更なしでパスすること

---

## 5. MCP / REST 公開仕様

### 5.1 MCP ツール 2 件（`mcp_server/tools/clo_tools.py` に追記）

```python
@mcp.tool()
async def logi_clo_facility_register(
    facility: dict,  # Facility のフィールド一式
) -> dict[str, object]: ...
    """施設マスタを登録 / 更新する。同一 facility_id があれば上書き。"""

@mcp.tool()
async def logi_clo_facility_list(
    company_id: str,
) -> dict[str, object]: ...
    """指定企業の施設一覧を返す（測定期間・除外理由・寄託先フラグ込み）。"""
```

### 5.2 REST 2 エンドポイント（`api/routers/clo.py` に追記）

```
POST /api/v1/clo/facilities       # body: Facility（id 重複は upsert）
GET  /api/v1/clo/facilities?company_id={id}
```

レスポンスは `ToolResponseModel` 統一（metadata に Facility リスト）。

### 5.3 wait-heatmap への facility_id クエリ追加

```
GET /api/v1/clo/wait-heatmap?company_id={cid}&facility_id={fid}
```

- `facility_id` 省略時は既存挙動
- 不正な facility_id は 404、`facility.site_name=None` の場合は 422

---

## 6. Web /dashboard/wait-heatmap 拡張

- `web/lib/api.ts` に `Facility` 型と `fetchFacilities(companyId)` / `registerFacility(payload)` を追加
- `web/app/dashboard/wait-heatmap/page.tsx` に施設フィルタ `<select>` を追加
  - 「全社集計（既定）」+ ロードした Facility 一覧
  - 選択時に `fetchWaitHeatmap(companyId, facilityId)` を呼ぶ
  - 集計上部に施設情報（測定期間 / 除外理由 / 寄託先フラグ）を表示

---

## 7. テスト計画（最低 12 件）

`tests/io/test_facility_store.py`（新規）:
1. save → load round trip
2. 未登録 facility_id → load_facility が None
3. 同一 facility_id の upsert（updated_at が更新される）
4. base_dir 実行時解決（LOGI_OUTPUTS_DIR の monkeypatch で切替）
5. company_id でのフィルタ（複数社のファイル分離）
6. JSON 直接編集に対する model_validate（前方互換）

`tests/analytics/test_wait_time_heatmap.py`（拡張）:
7. facility_id 指定時に site_name でフィルタされる
8. facility.site_name=None なら ValueError
9. facility_id=None の既存挙動完全互換
10. 寄託先 Facility（is_consigned_warehouse=True）でも集計は動く（警告だけ）

`tests/api/test_clo_router.py`（拡張）:
11. POST /facilities → GET /facilities で round trip
12. GET /wait-heatmap?facility_id=... で metadata に facility 情報が乗る
13. 不明 facility_id → 404

合計 13 件以上。

---

## 8. 寄託先施設の扱い（Codex 二者議論で確定する）

論点:

1. **取込ルール**: 寄託先施設を自社 Facility として登録すべきか、別タイプとすべきか
   - 案 A: `is_consigned_warehouse=True` フラグで同一テーブルに混在（提案中）
   - 案 B: ConsignedFacility を別モデルとして分離
2. **集計時の扱い**: heatmap に含めるか / 除外するか / 警告表示か
3. **法令観点**: 国交省手引書（特定倉庫業者編 / 特定荷主編）で寄託先の測定責任主体はどう定義されるか

→ Codex に二者議論を依頼（Tier A 相当 `--model gpt-5.5`）。結論はこの計画書 §8 末尾に追記。

---

## 9. 衝突回避（CLAUDE.md §9.3）

| 触らない領域 | 担当 |
|--------------|------|
| `core/io/decision_log_store.py` | セッション A |
| `core/analytics/operation_cockpit.py` | セッション A |
| `core/export/ppt_writer.py` | セッション C |

| 共通領域（追記のみ・既存関数編集禁止） |
|----------------------------------------|
| `mcp_server/tools/clo_tools.py` |
| `api/routers/clo.py` |
| `web/lib/api.ts` |
| `web/app/dashboard/wait-heatmap/page.tsx` |

---

## 10. 完了基準（プロンプト準拠）

- [ ] pytest 全 pass（新規 13 件以上）
- [ ] wait_heatmap が施設単位で集計可能（後方互換維持）
- [ ] MCP 2 件 + REST 2 件 動作確認済み
- [ ] Web /dashboard/wait-heatmap に施設フィルタ表示
- [ ] PR 作成（タイトル: `feat(facility): Tier S3 報告単位 Facility 管理レイヤ`）
- [ ] worktree 片付け

---

## 11. ロールバック

- 機能は独立コミットで積む（model → store → analytics → MCP/REST → Web）
- 問題発覚時は対応コミットだけ revert すれば残りは活きる
- 最悪ブランチごと破棄しても main に影響なし
