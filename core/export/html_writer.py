"""HTML 形式の成果物生成。

経営会議では PPT が主役（投影用）、Word/Excel が法定提出物、HTML は
「ブラウザでダブルクリックで開ける詳細閲覧用」の位置づけ。
self-contained（外部 CSS/JS なし）にして、社内メールに添付して
誰でも開けるようにする。

設計方針:
    - DESIGN.md のデザイントークン（ネイビー + アンバー）をインライン CSS で適用
    - 本文は <pre class="section-body"> で原文を保持（読み流し用途）
    - 出典は <a target="_blank"> でリンク化（Defensibility 担保）
    - @media print で Ctrl+P → PDF 化したときも体裁が崩れないようにする
    - β-3a スコープ: write_clo_plan_draft のみ。他成果物は β-3b 以降で拡張。
"""

from __future__ import annotations

import html
from pathlib import Path

from core.export.citation import Citation
from core.export.response import make_output_path

# DESIGN.md のトークンに対応した CSS（self-contained）。
# 変更時は docs/ppt_design.md と同期させること。
_BASE_CSS = """
:root {
  --primary: #1E2761;
  --primary-dk: #141A45;
  --secondary: #CADCFC;
  --surface: #EAF1FE;
  --on-primary: #FFFFFF;
  --muted: #5B6478;
  --border: #B8C0CE;
  --accent: #F5B82E;
  --positive: #2DD4BF;
  --negative: #EF6F6C;
}
* { box-sizing: border-box; }
html, body {
  margin: 0;
  padding: 0;
  background: #F8FAFD;
  color: var(--primary);
  font-family: "Yu Gothic UI", "Hiragino Sans", "Meiryo", sans-serif;
  font-size: 14px;
  line-height: 1.7;
}
.container {
  max-width: 960px;
  margin: 0 auto;
  padding: 48px 32px 64px;
}
.cover {
  background: var(--primary-dk);
  color: var(--on-primary);
  padding: 40px 32px;
  border-left: 8px solid var(--accent);
  border-radius: 4px;
  margin-bottom: 32px;
}
.cover h1 {
  margin: 0 0 8px;
  font-size: 28px;
  font-weight: 700;
  line-height: 1.3;
}
.cover .period {
  font-size: 13px;
  color: var(--secondary);
  letter-spacing: 0.04em;
}
.exec-summary {
  background: var(--surface);
  border-left: 4px solid var(--accent);
  padding: 24px 28px;
  border-radius: 4px;
  margin-bottom: 32px;
}
.exec-summary h2 {
  margin: 0 0 12px;
  font-size: 16px;
  font-weight: 700;
  color: var(--primary);
  letter-spacing: 0.04em;
}
.exec-summary pre {
  margin: 0;
  font-family: inherit;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.8;
  color: var(--primary-dk);
}
section.body-section {
  background: #FFFFFF;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 24px 28px;
  margin-bottom: 20px;
}
section.body-section h2 {
  margin: 0 0 16px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--accent);
  font-size: 18px;
  font-weight: 700;
  color: var(--primary);
}
section.body-section pre {
  margin: 0;
  font-family: inherit;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.75;
  color: #2C3142;
}
.citations {
  margin-top: 32px;
  padding: 24px 28px;
  background: var(--primary-dk);
  color: var(--on-primary);
  border-radius: 4px;
}
.citations h2 {
  margin: 0 0 16px;
  font-size: 14px;
  letter-spacing: 0.06em;
  color: var(--secondary);
}
.citations ul {
  margin: 0;
  padding: 0 0 0 20px;
  font-size: 12px;
  line-height: 1.8;
}
.citations li {
  margin-bottom: 4px;
  color: var(--secondary);
}
.citations a {
  color: var(--accent);
  text-decoration: none;
  word-break: break-all;
}
.citations a:hover { text-decoration: underline; }
.citations .meta {
  color: #8C95A8;
  margin-left: 6px;
  font-size: 11px;
}
.footer {
  margin-top: 32px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
  text-align: center;
  color: var(--muted);
  font-size: 11px;
}
@media print {
  body { background: #FFFFFF; font-size: 12px; }
  .container { padding: 0; max-width: none; }
  section.body-section, .exec-summary, .citations, .cover {
    page-break-inside: avoid;
    box-shadow: none;
  }
  a { color: var(--primary) !important; text-decoration: underline; }
}
"""


def _render_citation_li(c: Citation) -> str:
    """出典 1 件分の <li> 文字列。"""
    label = html.escape(c.label)
    url = html.escape(c.url, quote=True)
    parts = [f'<a href="{url}" target="_blank" rel="noreferrer">{label}</a>']
    meta_bits: list[str] = []
    if c.stats_data_id:
        meta_bits.append(f"statsDataId={html.escape(c.stats_data_id)}")
    if c.notice_number:
        meta_bits.append(html.escape(c.notice_number))
    if c.ordinance_number:
        meta_bits.append(html.escape(c.ordinance_number))
    if meta_bits:
        parts.append(f'<span class="meta">— {" / ".join(meta_bits)}</span>')
    return f"<li>{''.join(parts)}</li>"


def write_clo_plan_draft(
    company_name: str,
    company_id: str,
    plan_period: str,
    executive_summary: str,
    sections: list[tuple[str, str]],
    citations: list[Citation],
) -> Path:
    """CLO 中長期計画ドラフトの HTML を生成する（self-contained）。

    シグネチャは markdown_writer.write_clo_plan_draft と同一。
    """
    path = make_output_path(
        file_type="html",
        purpose="clo_plan",
        company_id=company_id,
        extension="html",
    )

    body_sections_html = "\n".join(
        f'<section class="body-section">'
        f"<h2>{html.escape(heading)}</h2>"
        f"<pre>{html.escape(body)}</pre>"
        f"</section>"
        for heading, body in sections
    )
    citations_html = "\n".join(_render_citation_li(c) for c in citations)

    document = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>中長期計画書ドラフト — {html.escape(company_name)}</title>
<style>{_BASE_CSS}</style>
</head>
<body>
<div class="container">
  <header class="cover">
    <h1>中長期計画書ドラフト — {html.escape(company_name)}</h1>
    <div class="period">計画期間: {html.escape(plan_period)}</div>
  </header>

  <section class="exec-summary">
    <h2>エグゼクティブサマリー</h2>
    <pre>{html.escape(executive_summary)}</pre>
  </section>

  {body_sections_html}

  <section class="citations">
    <h2>出典</h2>
    <ul>
{citations_html}
    </ul>
  </section>

  <div class="footer">
    Logi-Intel CLO Report — 物流効率化法（第46条／第65条）対応ドラフト
  </div>
</div>
</body>
</html>
"""
    path.write_text(document, encoding="utf-8")
    return path
