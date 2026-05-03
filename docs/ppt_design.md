# PPT Design Direction

This project adopts **Logi-Intel CLO Report** as the default presentation style.
The goal is to make `logi_clo_plan_draft` usable in executive meetings without
manual visual cleanup.

## Default Direction

Use a midnight-navy and amber visual identity with large KPI typography,
ice-blue surfaces, and quiet source footers. The second slide, the executive
summary, must make the investment decision readable before the viewer enters the
detailed evidence.

## Slide Families

| Family | Slides | Design role |
|--------|--------|-------------|
| Title | Cover | Dark navy report cover with amber side rail |
| KPI Dashboard | Executive summary, simulation | Large numbers and compact decision cards |
| Benchmark / Alert | Benchmark, driver gap | Large statistics and operational evidence |
| Verdict | Legal judgment, submission review | Navy verdict block and law-reference panels |
| Appendix | Citations and next steps | Dark navy appendix surface |

## Required Layout Behavior

- Cover: dark navy, large white title, amber right-side rail.
- Executive summary: show four scan-friendly KPI cards, plus a dark decision
  panel.
- Body slides: use a clear title, a compact eyebrow, and readable evidence lines
  with no raw text dump.
- Citation slide: use a dark appendix layout with source list and next steps.
- Footer: include the product context and page number without competing with the
  slide's message.

## Implementation Notes

- The canonical design tokens live in `DESIGN.md`.
- The current implementation is in `core/export/ppt_writer.py`.
- A reproducible sample deck can be generated with:

```powershell
uv run python scripts/generate_sample_ppt_design.py
```

The script writes a stable preview file to:

```text
outputs/ppt/sample_clo_design_codex_recommended.pptx
```
