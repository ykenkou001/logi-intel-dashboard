---
name: verify-clo-step
description: フェーズ3.5 CLO ツールの自動検証。Claude Desktop を起動せずローカルで全 CLO ツール × 3 サンプル一括検証し、ファイル生成・数値桁・docx/pptx 中身を機械チェック + LLM 妥当性判定。Step 完了時の動作確認に使用。
---

# verify-clo-step スキル

CLO ツール群の自動検証。Claude Desktop を起動せずに `scripts/verify_clo_step.py` を呼び出し、結果に **業界感覚に照らした妥当性判定** を加えてユーザーに報告する。

## 使い方

ユーザーが `/verify-clo-step` を呼んだ場合の動作:

| 入力 | 実行内容 |
|------|---------|
| `/verify-clo-step` | 全 10 ツール × 3 サンプル（全 30 件）を一括検証 |
| `/verify-clo-step plan_draft` | plan_draft × 3 サンプル |
| `/verify-clo-step plan_draft mfg_01` | plan_draft × sample_mfg_01 |
| `/verify-clo-step --json` | JSON 出力（機械処理用） |

サンプル ID の省略形:
- `mfg_01` → `sample_mfg_01`
- `wholesale_01` → `sample_wholesale_01`
- `chain_01` → `sample_chain_01`

## 実行手順

1. **引数を解析**:
   - 第1引数 → `--tool <name>`（ツール名・省略可）
   - 第2引数 → `--sample <id>`（sample_xxx_01・省略可）
   - `--json` フラグがあれば JSON 出力
   - 省略形（mfg_01 等）はフルネームに展開

2. **スクリプトを Bash で実行**:
   ```bash
   PYTHONIOENCODING=utf-8 uv run python scripts/verify_clo_step.py [args]
   ```
   - PYTHONIOENCODING=utf-8 は Windows コンソールの絵文字対策で必須
   - 全件実行はおおよそ 30 秒〜2 分（e-Stat キャッシュ次第）
   - timeout は `300000`（5 分）を指定

3. **結果を解析・要約してユーザーに報告**:
   - PASS/FAIL の総件数
   - FAIL があれば issue リスト
   - 数値の **業界感覚妥当性判定**（後述）

## 機械チェック（スクリプト側）

各ツールについて以下が自動検査される:

| ツール | チェック項目 |
|--------|-------------|
| benchmark | citations 存在 / revenue_vs_avg_pct 非負 |
| driver_gap | 全国従業者数が 100 万〜300 万人レンジ |
| eligibility | 連鎖化事業者フラグの伝播 |
| target_proposal | %目標値が ±100 以内 |
| simulate_measures | CO2/コスト/投資額が非負 |
| certified_match | 例外なし |
| playbook_search | 自社プロフィールで該当施策あり |
| **plan_draft** | 4 ファイル生成 + docx 必須セクション + pptx エグゼクサマリー(営業利益/炭素回避/NPV) |
| submission_validate | overall_pass=True かつ準拠率≥90% |
| financial_translate | 営業利益増 = コスト削減 / carbon_high ≥ low |

## LLM 妥当性判定（Claude 側で追加）

スクリプト出力後、以下の観点で **業界感覚に照らした判定** を追加せよ。
**判定基準は `core/static/industry_benchmarks.py` に集約**されており、coding 上の判定は同モジュールの定数（`OPERATING_PROFIT_MARGIN_PCT` / `SANITY` / `KPI_REACHABILITY`）と整合させること。LLM は同モジュールの定数値を起点に判定する。

### 1. 業種別の利益率改善（margin_lift_pp）

`industry_benchmarks.SANITY.profit_margin_lift_max_pp = 3.0pp` を超えると submission_validator が `PROFIT_MARGIN_LIFT_EXCESSIVE` warning を発行する。

| 業種 | 期待レンジ | 異常判定 |
|------|-----------|---------|
| 製造業（営業利益率 7%）| +0.5〜2.0pp | <0.3 か >3.0 で要調査 |
| 卸売業（営業利益率 2%）| +1.5〜4.0pp | <1.0 か >5.0 で要調査 |
| コンビニ本部（利益率 3.5%）| +0.5〜1.5pp | <0.3 か >2.5 で要調査 |

### 2. CO2 削減量

- 売上 100 億円規模で 1,000〜3,000 t-CO2/年
- 売上 1,000 億円規模で 5,000〜15,000 t-CO2/年
- これを大きく外れる場合は要調査

### 3. 5年累積 NPV と投資の比率

`industry_benchmarks.SANITY` に集約されたしきい値:
- `npv_to_investment_max_multiple = 100.0` 倍を超えると `NPV_RATIO_EXCESSIVE` warning（過大評価の疑い）
- `npv_to_investment_min_multiple = 0.5` 倍を下回ると `NPV_RATIO_TOO_LOW` warning（投資判断却下レベル）
- 通常レンジは 5〜50 倍

### 4. 営業利益増の妥当性

`SANITY.operating_profit_increase_max_ratio = 0.30`（現状営業利益の 30%）を超えると `OPERATING_PROFIT_INCREASE_EXCESSIVE` warning が出る。施策効果の重複・楽観前提を疑う。

### 5. 業界平均比の信頼性

benchmark.py の `revenue_ratio_reliability` フィールド（`industry_benchmarks.REVENUE_VS_AVG_*_THRESHOLD_PCT` で分類）:
- `normal` / `large_scale` → 通常表示
- `low_reliability`（>1000%）→ 経営会議では数値非表示・規模優位企業として相対参照

### 6. データ出所の確認

ToolResponse の `data_source` フィールド:
- `estimated`（サンプル3社・業界統計推計）→ 提出前には実測値への差し替えを推奨
- `actual`（自社実績）→ そのまま提出可

### 7. 業種特異な観察

- 連鎖化事業者は荷役等項目が docx に存在しない（仕様）
- 中継輸送が連鎖化事業者の form3 wait セクションに流用される（Step 6 後の修正）
- `playbook_search` で連鎖化事業者の matched_count は 5 件（多拠点・IT 前提の施策が外れる）

## 報告フォーマット

スクリプト出力をそのまま貼るのではなく、以下のように要約せよ:

```
## CLO ツール検証結果

✅ 全 30 件 PASS（10 ツール × 3 サンプル）  [または ❌ 失敗の指摘]

### サンプル別 主要数値
| サンプル | 営業利益増/年 | 利益率改善 | 5年NPV |
|----------|-------------|-----------|--------|
| 製造業    | +7.79億円    | +0.92pp   | 35.46億 |
| 卸売業    | +11.69億円   | +2.78pp   | 53.30億 |
| コンビニ  | +29.22億円   | +0.91pp   | 133.60億 |

### 妥当性判定（業界感覚に照らして）
- ✅ 製造業 +0.92pp は期待レンジ内
- ✅ 卸売業 +2.78pp は薄利業種として妥当
- ✅ コンビニ +0.91pp は規模優位 + 利益率中位として整合
- ⚠️ XXX が異常値（あれば指摘）

### 異常検出
- なし／ある場合は具体的に
```

## 失敗時の対応

- スクリプトが exit code 1 で終了 → FAIL 件数を必ず明示
- 個別の `issues` リストは原文のまま提示（コードでデバッグしやすくするため）
- スクリプト自体が exception で死んだ場合は traceback を抜粋して報告

## してはいけないこと

- スクリプトを書き換えない（検証ロジック追加が必要なら別タスクとして提案）
- `outputs/` フォルダを削除しない（既存ファイルへの影響があるため）
- 結果を「全部 OK でした」だけで終わらせない（数値の妥当性判定まで必ず添える）
