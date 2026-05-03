"""Generate a stable sample PPT for the Codex-recommended CLO deck design."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.export.citation import Citation  # noqa: E402
from core.export.ppt_writer import SlideContent, write_clo_plan_draft  # noqa: E402

SAMPLE_PATH = Path("outputs/ppt/sample_clo_design_codex_recommended.pptx")


def main() -> None:
    generated_path = write_clo_plan_draft(
        company_name="サンプル物流株式会社",
        company_id="sample_design",
        plan_period="2026〜2030",
        executive_summary=[
            "推奨: 共同配送と積載率改善を先行し、初年度から営業利益 +1.2 億円を狙う",
            "投資額: 2.4 億円 / 回収期間: 2.1 年",
            "CO2削減: 年間 4,800 t-CO2 / 国家目標と整合",
            "リスク: CLO未選任・計画未提出は取引先監査で説明不能",
            "次アクション: 90日以内に対象拠点・主管部門・月次KPIを確定",
        ],
        body_slides=[
            SlideContent(
                title="物流KPI・施策ポートフォリオ",
                body_lines=[
                    "積載率: 現状 38% → 目標 50%（年 +2.4pp 改善）",
                    "優先施策: 共同配送、TMS導入、荷待ち時間可視化",
                    "Top 3 推薦は ROI、実現可能性、法令寄与で選定",
                    "月次KPI: 積載率、拘束時間、CO2原単位、燃料費感度",
                    "Bottom 3 は投資回収と業種適合の観点で一旦見送り",
                ],
                footnote="出典: e-Stat / 物流効率化法 認定事業 / 社内推計",
            ),
            SlideContent(
                title="施策効果シミュレーション",
                body_lines=[
                    "標準ケース: 営業利益 +1.2 億円、CO2 ▲4,800 t-CO2",
                    "燃料 +20% ケースでも黒字維持",
                    "保守ケースでは投資回収 3.0 年以内を基準に採否判断",
                    "上振れケースは共同配送の参加社数拡大を前提に設定",
                ],
                footnote="出典: 国交省資料 / 燃料価格履歴 / 業界ベンチマーク",
            ),
            SlideContent(
                title="法令区分・提出準備レビュー",
                body_lines=[
                    "特定第一種荷主: 物流効率化法 第46条の中長期計画作成義務",
                    "CLO選任: 物流効率化法 第66条",
                    "様式第3: 実施措置、計画内容、実施時期を網羅",
                    "提出準備: 法人番号、代表者情報、指定通知書番号を確認",
                    "出典URLと引用条文は成果物末尾で追跡可能",
                ],
                footnote="出典: 物流効率化法 / 国交省 CLO ポータル",
            ),
        ],
        citations=[
            Citation(label="物流効率化法", url="https://www.mlit.go.jp/"),
            Citation(label="e-Stat", url="https://www.e-stat.go.jp/"),
            Citation(label="国交省 CLO ポータル", url="https://www.mlit.go.jp/"),
        ],
    )
    SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(generated_path, SAMPLE_PATH)
    print(SAMPLE_PATH)


if __name__ == "__main__":
    main()
