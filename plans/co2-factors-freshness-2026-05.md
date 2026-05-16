# CO2 排出原単位データの鮮度更新計画

**計画策定日**: 2026-05-16
**実装ブランチ予定**: `fix/co2-factors-freshness`
**起票経緯**: PR #36（NTA 法人番号 API バグ修正）の動作確認時、`/dashboard/macro` の鮮度警告ペインで該当データの 1080 日経過（推奨間隔 +350 日超過）を確認

---

## 1. 問題

本番ダッシュボード <https://d1zei8qivkf3cr.cloudfront.net/dashboard/macro> の鮮度警告ペインに次の警告が表示されている:

```
⚠️ CO2 排出原単位（共同ガイドライン Ver.3.2）: データが 1080 日経過
（推奨間隔超過 +350 日）。最新化を検討してください:
https://www.greenpartnership.jp/guideline_ver3_2.pdf
```

CLO 計画書のモーダルシフト試算で参照される **全数値** に対する出典の鮮度が落ちている状態で、CLAUDE.md §1.5 ミッション「全数値に出典を付与」原則を損なう。

## 2. 該当データの現状

[core/static/co2_factors.py](../core/static/co2_factors.py):

```python
FRESHNESS = Freshness(
    label="CO2 排出原単位（共同ガイドライン Ver.3.2）",
    last_updated=date(2023, 6, 1),   # Ver.3.2 発行月（令和5年6月）
    update_cadence="biennial",        # 730 日
    source_url="https://www.greenpartnership.jp/guideline_ver3_2.pdf",
    notes=(
        "経産省・国交省共同ガイドライン Ver.3.2（2023年6月）。"
        "Ver.3.0→3.1→3.2 のリリース実績から概ね 2 年間隔で改訂チェック。"
    ),
)
```

データそのものは `Co2EmissionFactors` dataclass で輸送機関別 g-CO2/トンキロ 6 値を持つ:

| 機関 | 値 | 用途 |
|---|---|---|
| `truck_small_commercial` | 388 | 小型トラック 営業用（〜2t） |
| `truck_medium_commercial` | 196 | 普通トラック 営業用（2-10t） |
| `truck_large_commercial` | 76 | 大型トラック 営業用（10t〜） |
| `rail_freight` | 21 | 鉄道貨物 |
| `coastal_shipping` | 39 | 内航海運 |
| `air_freight` | 1490 | 航空貨物 |

鮮度メカニズム: [core/static/_freshness.py](../core/static/_freshness.py) の `register()` で集約 → `all_warnings()` が API レスポンスに警告文字列として混入。

## 3. 調査ステップ

### Step 1: 一次情報の最新版確認

- <https://www.greenpartnership.jp/co2> を開く（グリーン物流パートナーシップ会議のCO2公表値ページ）
- <https://www.greenpartnership.jp/guideline_ver3_2.pdf> が現行版か確認
- Ver.3.3 / Ver.4 / 改訂版 等の上位バージョン PDF へのリンクの有無をチェック
- 公表ページに「最新版」「現行ガイドライン」等の明示があるか確認

### Step 2: 値そのものの確認

新版が存在する場合のみ実施:

- 新版 PDF を取得（手動 DL → リポジトリ外で OK）
- §「輸送機関別 CO2 排出原単位」または相当の章を確認
- 表 2 に列挙した 6 値が変わっているか比較
- 「改良トンキロ法」「燃費基準達成考慮」「輸送機関別の典型値」の扱いを確認

## 4. 分岐シナリオ

### A) Ver.3.3 以降が存在する場合

- `core/static/co2_factors.py` を以下に従って更新:
  - `last_updated` → 新版発行月
  - `label` → 新バージョン番号
  - `source_url` → 新 PDF URL
  - `notes` → 改訂履歴を更新
  - `Co2EmissionFactors` の値 → 一次情報で変わっていた値のみ更新（**変わっていない値はそのまま**）
- 既存テストで `CO2_FACTORS` を直接参照しているものを点検:
  - `grep -r "CO2_FACTORS\|truck_small_commercial\|coastal_shipping\|rail_freight" tests/`
  - 期待値が古い値を埋めていれば PR で同時更新

### B) Ver.3.2 が最新で新版未公表の場合

- `core/static/co2_factors.py` の `last_updated` を **公式サイトで Ver.3.2 が現行版であることを確認した日** に更新
- `notes` に `「YYYY-MM-DD に公式サイトで Ver.3.2 が最新版である旨を確認」` を追記
- データ値は変更しない
- 鮮度警告は消える（last_updated 更新だけで `is_stale` が False に戻る）

## 5. 検証

1. `uv run ruff check core/static/co2_factors.py`
2. `uv run mypy core/static/co2_factors.py`
3. `uv run pytest --tb=short -q`（CO2 関連テストが残っていれば確実に通す）
4. `pwsh scripts/dev_api.ps1` + `pwsh scripts/dev_web.ps1`
5. `http://localhost:3000/dashboard/macro` を開く → **東京都 → マクロ概況を取得** → 鮮度警告ペインから当該行が消えていることを目視
6. PR マージ後、本番 <https://d1zei8qivkf3cr.cloudfront.net/dashboard/macro> でも同等確認（GitHub Actions が Lambda 自動デプロイする）

## 6. 作業ルール（CLAUDE.md 準拠）

- **NO GUESSING**: 一次情報 PDF で確認できない値は変更しない。推測で値を書かないこと
- **ブランチ**: `fix/co2-factors-freshness` を切る（main 直接 push 禁止）
- **PR タイトル例**: `fix(co2-factors): 共同ガイドライン Ver.X.X 対応で鮮度警告解消`
- **コミットメッセージ**: 一次情報 URL と確認日を必ず含める
- **CLAUDE.md §1.5 準拠**: 全数値の出典を維持
- **Codex 委譲判断**: 新版 PDF の数値抽出と単純なメタデータ更新は Codex 単独でも可（CLAUDE.md §9.2 の「静的データ取込」領域）

## 7. 完了条件

- [ ] `core/static/co2_factors.py` の `last_updated` または値が更新されている
- [ ] 一次情報 URL と確認日が `notes` フィールドまたはコミットメッセージに残っている
- [ ] 本番 `/dashboard/macro` の鮮度警告ペインから「CO2 排出原単位」行が消えた、または日数が許容範囲内に戻った
- [ ] pytest 全件 pass
- [ ] PR がマージされ Lambda 自動デプロイが成功している

## 8. 参考リンク

- 対象ファイル: [core/static/co2_factors.py](../core/static/co2_factors.py)
- 鮮度仕組み: [core/static/_freshness.py](../core/static/_freshness.py)
- 警告を載せる箇所: [api/routers/macro.py](../api/routers/macro.py)（`response.freshness_warnings = all_warnings()`）
- 関連 memory: `feedback_mock_only_tests_miss_api_bugs.md`（一次情報確認の重要性）
- 前例 PR: #34（フェーズ 5.5 β 既知課題の計画記録パターン）

## 9. 想定工数

- Step 1 公式サイト確認: 10〜20 分
- Step 2 値比較: 新版存在時のみ 30〜60 分
- 実装 + 検証: 30〜60 分
- **合計目安: 1〜2 時間**（新版なしなら 30〜45 分）
