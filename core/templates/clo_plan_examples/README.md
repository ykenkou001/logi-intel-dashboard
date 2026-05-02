# 国交省 公式記載事例集（中長期計画書・定期報告書）

国土交通省・経済産業省が公開している「中長期計画書・定期報告書 記載事例集」の取込先。

出典: [物流効率化法 理解促進ポータル（国交省）](https://www.revised-logistics-act-portal.mlit.go.jp/information/details/post_18.html)

## ディレクトリ構成

```
clo_plan_examples/
├── README.md           ← このファイル
├── PDF/                ← 国交省ダウンロードPDFの原本（gitignore 対象）
│   ├── 中長期計画書記載事例（製造業）.pdf
│   ├── 中長期計画書記載事例（卸売業）.pdf
│   ├── 中長期計画書記載事例（小売業）.pdf
│   ├── 中長期計画書記載事例（連鎖化事業者）.pdf
│   └── 定期報告書記載事例（製造業）.pdf  ← フェーズ4.5 用先行
└── *.md                ← MD 化された事例（コード参照用）
    ├── manufacturing_advanced.md
    ├── manufacturing_starter.md
    ├── wholesale_advanced.md
    ├── wholesale_starter.md
    ├── retail_advanced.md
    ├── retail_starter.md
    ├── chain_advanced.md
    └── chain_starter.md
```

## 取込状況

| ファイル | フェーズ | 状態 |
|---------|---------|------|
| 中長期計画書記載事例（製造業）.pdf | 3.0 | PDF 受領 / MD 化未着手 |
| 中長期計画書記載事例（卸売業）.pdf | 3.0 | PDF 受領 / MD 化未着手 |
| 中長期計画書記載事例（小売業）.pdf | 3.0 | PDF 受領 / MD 化未着手 |
| 中長期計画書記載事例（連鎖化事業者）.pdf | 3.0 | PDF 受領 / MD 化未着手 |
| 定期報告書記載事例（製造業）.pdf | 4.5 | PDF 受領 / MD 化未着手 |

## MD 化方針

- 各 PDF には「取組が進んでいる企業向け」と「これから取組を深める企業向け」の 2 パターンが含まれる
- 1 PDF → 2 MD ファイル（`{industry}_advanced.md` と `{industry}_starter.md`）に分離
- 構造は国交省様式第3 別紙の 3 項目 × 3 軸（実施措置・計画内容・実施時期）= 9 セルで統一
- MD 化作業は `scripts/convert_clo_examples.py`（フェーズ 2.5 Step 4 で実装）

## 著作権

- 国土交通省・経済産業省 公開資料
- 利用条件: 政府標準利用規約（CC BY 4.0 互換）
- リポジトリへの PDF 同梱可否: **PDF は gitignore 対象**（再配布は出典明記すれば可だが、ファイルサイズ削減と更新追随のため）
- MD 化したテキストは出典明記の上で同梱可
