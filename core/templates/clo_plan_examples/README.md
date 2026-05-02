# CLO 計画書・報告書 記載見本集

経済産業省・国土交通省が公開する「中長期計画書（様式第3）」および「定期報告書（様式第5）」の記載見本を Markdown 化したもの。

---

## ファイル一覧

### 中長期計画書（様式第3）— 特定荷主向け（第46条関係）

| ファイル | 業種 | 取組段階 | 特徴 |
|---------|------|---------|------|
| [manufacturing_starter.md](manufacturing_starter.md) | 製造業 | 着手初期 | KPI未整備・ヒアリングから着手 |
| [manufacturing_advanced.md](manufacturing_advanced.md) | 製造業 | 取組進行中 | AI配車・バース予約・CLO体制確立 |
| [wholesale_starter.md](wholesale_starter.md) | 卸売業 | 着手初期 | 主要拠点・代表ルートから段階的着手 |
| [wholesale_advanced.md](wholesale_advanced.md) | 卸売業 | 取組進行中 | グループ内共同配送・トラック予約システム全拠点 |
| [retail_starter.md](retail_starter.md) | 小売業 | 着手初期 | モデル店舗から横展開 |
| [retail_advanced.md](retail_advanced.md) | 小売業 | 取組進行中 | AI活用配車・一貫パレチゼーション・共同配送 |

各ファイルは特定第一種荷主（発荷主）と特定第二種荷主（着荷主）の2区分で記載。  
記載項目: **Ⅱ 積載率向上 / Ⅲ 荷待ち時間短縮 / Ⅳ 荷役等時間短縮**（様式第3別紙）

### 中長期計画書（様式第3）— 特定連鎖化事業者向け（第5条関係）

| ファイル | 業種 | 取組段階 | 特徴 |
|---------|------|---------|------|
| [chain_starter.md](chain_starter.md) | コンビニ等 | 着手初期 | 動態管理から着手・積載状況調査中 |
| [chain_advanced.md](chain_advanced.md) | コンビニ等 | 取組進行中 | AI配送ルート最適化全社展開・複数温度帯対応 |

根拠法: **第65条**（荷主は第46条）。記載項目は **Ⅱ 荷待ち時間 / Ⅲ 積載率** の2本のみ（荷役等はなし）。

### 定期報告書（様式第5）— 製造業向け

| ファイル | 業種 | 取組段階 | 特徴 |
|---------|------|---------|------|
| [manufacturing_report_starter.md](manufacturing_report_starter.md) | 製造業 | 着手初期 | 荷待ち・荷役等時間の切り分け未整備・合計値で報告 |
| [manufacturing_report_advanced.md](manufacturing_report_advanced.md) | 製造業 | 取組進行中 | 全車両動態管理・バース予約・実績データ完備 |

様式第5は**実績データ**の年次報告書。判断基準の遵守状況・計測データを記載。

---

## PDF 元資料

元の PDF ファイルは `PDF/` サブディレクトリに保存（`.gitignore` 対象）。

| PDF ファイル | MD 変換先 |
|-------------|----------|
| 特定連鎖化事業者向け記載見本（2種） | `chain_starter.md` / `chain_advanced.md` |
| 小売業向け記載見本（2種） | `retail_starter.md` / `retail_advanced.md` |
| 卸売業向け記載見本（2種） | `wholesale_starter.md` / `wholesale_advanced.md` |
| 製造業向け中長期計画記載見本（2種） | `manufacturing_starter.md` / `manufacturing_advanced.md` |
| 製造業向け定期報告書記載見本（2種） | `manufacturing_report_starter.md` / `manufacturing_report_advanced.md` |

---

## 利用方針

- `core/logic/plan_draft.py` や `core/export/` からテンプレートとして参照
- 企業の業種・取組段階に応じて適切なファイルを選択して文案生成に活用
- 内容は公的資料に基づくが、記載例の企業名・数値は架空（実在しない）
