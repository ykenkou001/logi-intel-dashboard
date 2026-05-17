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

## 8. 寄託先施設の扱い（Codex 二者議論結果反映 — 2026-05-17）

### 8.1 論点と初期 Claude 案

1. **取込ルール**: 寄託先施設を自社 Facility として登録すべきか、別タイプとすべきか
   - 案 A: `is_consigned_warehouse=True` フラグで同一テーブルに混在（PR #50 で採用）
   - 案 B: `ConsignedFacility` を別モデルとして分離
2. **集計時の扱い**: heatmap に含めるか / 除外するか / 警告表示か
3. **法令観点**: 国交省手引書（特定倉庫業者編 / 特定荷主編）で寄託先の測定責任主体はどう定義されるか

### 8.2 Codex 回答（2026-05-17 / `--model gpt-5.5`）

> **注記（CLAUDE.md §9.4-3 準拠）**: Codex は条番号 / 告示番号 / 様式第5 必須文言を「**不明（推測）**」と明示している。条文出典は二次調査が必要。

#### 論点 1: テーブル設計

- **Codex 判断**: 案 A（同一 Facility + `is_consigned_warehouse`）のままでは弱い。行政提出・経営会議では「自社管理施設」と「寄託先管理施設」の責任境界が説明単位になるため、単なる bool では混入リスクが残る。ただし別モデル完全分離（案 B）よりも、同一保存形式で `facility_control_type` と証跡項目を必須化する案が強い。
- **根拠（Codex 提示）**: 特定荷主編手引書 3-5-3「寄託先施設との混同」、IV-4・IV-5（条番号は不明・推測）
- **Codex の修正提案**:
  - `facility_control_type: Literal["owned", "leased", "operated_by_3pl", "consigned"]` を追加
  - `measurement_source: str | None`（測定主体名）
  - `consigned_partner_name: str | None`（寄託契約相手の事業者名）
  - `contract_scope_note: str | None`（寄託契約のスコープ注記）

#### 論点 2: heatmap 集計時の寄託先扱い

- **Codex 判断**: 法令整合上、寄託先を自社管理施設の heatmap KPI に既定混入させる設計は弱い。最も強いのは「警告付き集計」だが、自社管理施設の主集計と分離し、寄託先は参考値レイヤとして出すこと。完全除外は改善連携の実務価値を捨て、既定集計対象は責任境界を曖昧にする。
- **根拠（Codex 提示）**: 特定荷主編手引書 3-5-2 / 03 IV-4・IV-5、特定倉庫業者編 様式第8 IV「荷待ち時間等の状況等」（告示番号は不明・推測）
- **Codex の修正提案**: `include_consigned=false` を既定にし、ON 時は「寄託先（自社直接測定外・参考値）」バナー、主 KPI 非混入、別系列 / 別凡例で表示する。

#### 論点 3: 測定責任主体と様式第5 注記

- **Codex 判断**: 荷主が様式第5 に記載する値の提出責任は荷主に残る。特定倉庫業者は自ら管理する施設について様式第8 で計測・報告する責任を持つ。荷主が寄託先から値を受領して使う場合は、「寄託先提供値」「把握範囲」「計測条件」「自社直接計測外」を明記するのが防御的。
- **根拠（Codex 提示）**: 特定荷主編手引書 3-5-2 / 03 IV-5「把握している範囲」「任意項目」、特定倉庫業者編 様式第8 IV 1-3（様式第5 の必須文言は不明・推測）
- **Codex の修正提案**:
  - `measurement_conditions` に標準文言「寄託先○○から提供を受けた参考値。計測期間・対象運行・計測方法は寄託先記録に基づく（自社直接計測外）。」を入れる
  - `exclusion_reasons` に「寄託契約先管理施設のため自社管理施設の主集計から除外。IV-4/IV-5 に連携状況・把握範囲を記載。」を入れる

### 8.3 Claude 評価と次 PR タスク

| 論点 | Claude 評価 | 反映方針 |
|------|------------|----------|
| 1: 設計拡張 | **修正のうえ採用** | `is_consigned_warehouse: bool` を残しつつ（後方互換）、`facility_control_type` Enum + `measurement_source` / `consigned_partner_name` / `contract_scope_note` を追加する。型分離（案 B）は採用しない（PR #50 のテーブル設計と JSON 形式を破壊するため） |
| 2: 集計分離 | **修正のうえ採用** | 全社集計（`facility_id=None`）時に寄託先を既定除外する `include_consigned: bool = False` 引数を `build_wait_time_heatmap` に追加。ただし `facility_id` 直接指定時は意図的選択なので集計対象（既存挙動維持） |
| 3: 標準注記 | **採用** | `Facility` に `consigned_disclaimer_default()` ヘルパーを追加し、`is_consigned_warehouse=True` のとき `measurement_conditions` 未入力なら推奨文言を自動付与（運用負荷低減）。Web 側でも標準文言の自動挿入ボタンを追加 |

### 8.4 持ち越し（フォロー PR で対応）

1. **論点 1 の設計拡張**: `facility_control_type` 追加 + Pydantic マイグレーション（既存 JSON は `is_consigned_warehouse` から逆算して `consigned` / `owned` のいずれかにフォールバック）
2. **論点 2 の集計分離**: `include_consigned: bool = False` 引数追加 + heatmap metadata に「主集計件数」「除外された寄託先件数」を併記
3. **論点 3 の標準文言**: `core/io/facility_store.py` に `default_consigned_disclaimer()` を追加し、`upsert_facility` 時に自動付与
4. **条文出典の二次調査**: Codex が「不明」と明示した条番号 / 告示番号 / 様式第5 文言を一次資料（特定荷主編手引書 PDF）で確認し、`Citation` に登録

タスク #1-#3 は別 PR `feat(facility): Codex 二者議論 §8 反映（control_type / include_consigned / standard disclaimer）` として段階的に進める。タスク #4 は健一 + Codex で二次調査依頼。

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
