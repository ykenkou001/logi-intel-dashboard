# CLO 計画書・報告書 記載見本集（国交省公式記載事例集）

国土交通省・経済産業省が公開する「中長期計画書（様式第3）」および「定期報告書（様式第5）」の記載見本を Markdown 化したもの。

出典: [物流効率化法 理解促進ポータル（国交省）](https://www.revised-logistics-act-portal.mlit.go.jp/information/details/post_18.html)

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

### 定期報告書（様式第5）— 製造業向け（フェーズ4.5 で活用）

| ファイル | 業種 | 取組段階 | 特徴 |
|---------|------|---------|------|
| [manufacturing_report_starter.md](manufacturing_report_starter.md) | 製造業 | 着手初期 | 荷待ち・荷役等時間の切り分け未整備・合計値で報告 |
| [manufacturing_report_advanced.md](manufacturing_report_advanced.md) | 製造業 | 取組進行中 | 全車両動態管理・バース予約・実績データ完備 |

様式第5は**実績データ**の年次報告書。判断基準の遵守状況・計測データを記載。

---

## ディレクトリ構成

```
clo_plan_examples/
├── README.md           ← このファイル
├── PDF/                ← 国交省ダウンロードPDFの原本（.gitignore 対象）
│   ├── 中長期計画書記載事例（製造業）.pdf
│   ├── 中長期計画書記載事例（卸売業）.pdf
│   ├── 中長期計画書記載事例（小売業）.pdf
│   ├── 中長期計画書記載事例（連鎖化事業者）.pdf
│   └── 定期報告書記載事例（製造業）.pdf  ← フェーズ4.5 用先行
└── *.md                ← MD 化された事例（コード参照用）10 ファイル
```

---

## MD 化方針

- 各 PDF には「取組が進んでいる企業向け（advanced）」と「これから取組を深める企業向け（starter）」の 2 パターンが含まれる
- 1 PDF → 2 MD ファイル（`{industry}_advanced.md` と `{industry}_starter.md`）に分離
- 構造は国交省様式第3 別紙の 3 項目 × 3 軸（実施措置・計画内容・実施時期）= 9 セルで統一
- 取込状況: **5 PDF → 10 MD 化完了（2026-05-02 時点）**

---

## 利用方針

- `core/analytics/plan_draft.py` や `core/export/` からテンプレートとして参照
- 企業の業種・取組段階に応じて適切なファイルを選択して文案生成に活用
- 内容は公的資料に基づくが、記載例の企業名・数値は架空（実在しない）

---

## 著作権

- 国土交通省・経済産業省 公開資料
- 利用条件: 政府標準利用規約（CC BY 4.0 互換）
- リポジトリへの PDF 同梱可否: **PDF は .gitignore 対象**（再配布は出典明記すれば可だが、ファイルサイズ削減と更新追随のため）
- MD 化したテキストは出典明記の上で同梱可
