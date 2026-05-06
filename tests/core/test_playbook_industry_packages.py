"""core/playbook/industry_packages.py のテスト（フェーズ5.0 段階 c.1〜c.4）。

Codex レビュー反映済の 4 業種パッケージに対するインバリアントと
resolve_company_package の Override 4 分類挙動を確認する。

カバレッジ:
    - 4業種 × 5要素 = 20 セル全て非空（meetings/reports/data_items は最低 1 件）
    - measure_ids が ALL_MEASURES のサブセット（参照整合性）
    - 連鎖化に loading セクション施策（warehouse_dx_wms / pallet_standardization）
      が含まれない
    - load_factor_pct の target_value が国の 2028 年度目標 44 と整合
    - 推測排除：target_value=None の KPI は legal_basis も None or 制度 URL のみ
    - resolve_company_package: approved_better_practice / required_localization
      は上書き反映、unmanaged_deviation は無視、temporary_exception は期限制御
    - c.4 既存資産接続検証:
        * ALL_MEASURES.applicable_industries 側からの逆検証
          （業種パッケージの measure_ids が ALL_MEASURES の applicable_industries
            と矛盾していないか）
        * plan_template_paths のファイル実在性
        * logistics_cost_revenue_ratio_pct.baseline_value が
          industry_benchmarks.LOGISTICS_COST_RATIO と一致
        * measure_ids / KPI metric_id に重複がないこと

plan: plans/b-c-flickering-pixel.md §段階 c.4 / c.9
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from core.playbook.industry_packages import (
    ALL_PACKAGES,
    CHAIN_FRANCHISE_FORBIDDEN_FORM3_SECTIONS,
    CHAIN_FRANCHISE_FORBIDDEN_KPI_PREFIXES,
    CHAIN_FRANCHISE_REQUIRED_LEGAL_ARTICLE,
    CompanyPackageOverride,
    IndustryPackage,
    OverrideEntry,
    StandardKpiDef,
    StandardReportDef,
    get_package,
    list_packages,
    resolve_company_package,
    validate_chain_franchise_constraints,
)
from core.playbook.measures import ALL_MEASURES, get_measure
from core.static.industry_benchmarks import LOGISTICS_COST_RATIO
from core.static.jsic import JsicCategory

_REPO_ROOT = Path(__file__).resolve().parents[2]

_INDUSTRIES: list[JsicCategory] = [
    "manufacturing", "wholesale", "retail", "chain_franchise",
]


# ---------------------------------------------------------------------------
# 1. 4業種 × 5要素 マトリクス充足
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("industry", _INDUSTRIES)
def test_package_exists_for_each_industry(industry: JsicCategory) -> None:
    pkg = get_package(industry)
    assert pkg is not None
    assert pkg.category == industry


@pytest.mark.parametrize("industry", _INDUSTRIES)
def test_kpis_are_non_empty(industry: JsicCategory) -> None:
    pkg = get_package(industry)
    assert pkg is not None
    # 業種固有 + 共通 (wait_handling + cost_ratio) で最低 5 件
    assert len(pkg.kpis) >= 5


@pytest.mark.parametrize("industry", _INDUSTRIES)
def test_measure_ids_are_non_empty(industry: JsicCategory) -> None:
    pkg = get_package(industry)
    assert pkg is not None
    assert len(pkg.measure_ids) >= 3


@pytest.mark.parametrize("industry", _INDUSTRIES)
def test_meetings_are_non_empty(industry: JsicCategory) -> None:
    pkg = get_package(industry)
    assert pkg is not None
    assert len(pkg.meetings) >= 1


@pytest.mark.parametrize("industry", _INDUSTRIES)
def test_reports_are_non_empty(industry: JsicCategory) -> None:
    pkg = get_package(industry)
    assert pkg is not None
    assert len(pkg.reports) >= 1


@pytest.mark.parametrize("industry", _INDUSTRIES)
def test_data_items_are_non_empty(industry: JsicCategory) -> None:
    pkg = get_package(industry)
    assert pkg is not None
    assert len(pkg.data_items) >= 1


def test_list_packages_returns_four_in_stable_order() -> None:
    pkgs = list_packages()
    assert len(pkgs) == 4
    assert [p.category for p in pkgs] == _INDUSTRIES


# ---------------------------------------------------------------------------
# 2. 参照整合性（measure_ids ⊂ ALL_MEASURES）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("industry", _INDUSTRIES)
def test_measure_ids_subset_of_all_measures(industry: JsicCategory) -> None:
    pkg = get_package(industry)
    assert pkg is not None
    valid_ids = {m.measure_id for m in ALL_MEASURES}
    for mid in pkg.measure_ids:
        assert mid in valid_ids, f"{industry}: measure_id {mid!r} は ALL_MEASURES に存在しない"


def test_chain_excludes_loading_section_measures() -> None:
    """連鎖化事業者は荷役等セクション（loading）施策を必須から除外（c.8）。"""
    pkg = get_package("chain_franchise")
    assert pkg is not None
    loading_ids = {"warehouse_dx_wms", "pallet_standardization"}
    for mid in pkg.measure_ids:
        assert mid not in loading_ids, (
            f"連鎖化に loading 施策 {mid} が含まれている（form3 第5条関係 違反）"
        )


@pytest.mark.parametrize("industry", _INDUSTRIES)
def test_kpi_related_measure_ids_are_valid(industry: JsicCategory) -> None:
    """KPI.related_measure_ids が ALL_MEASURES のサブセット。"""
    pkg = get_package(industry)
    assert pkg is not None
    valid_ids = {m.measure_id for m in ALL_MEASURES}
    for kpi in pkg.kpis:
        for mid in kpi.related_measure_ids:
            assert mid in valid_ids, (
                f"{industry} KPI {kpi.metric_id}: related_measure_id "
                f"{mid!r} は ALL_MEASURES に存在しない"
            )


# ---------------------------------------------------------------------------
# 3. Codex レビュー反映の検証
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("industry", _INDUSTRIES)
def test_load_factor_target_matches_national_2028_goal(
    industry: JsicCategory,
) -> None:
    """積載率目標が国の 2028 年度全体目標 44% と整合（Codex 修正反映）。

    旧案 manufacturing 55% / wholesale 52% は業界実績 1.5-3pp/年 を超え根拠不足
    だったため取下げ。挑戦値は Override で各社が積み上げる設計。
    """
    pkg = get_package(industry)
    assert pkg is not None
    lf = next(
        (k for k in pkg.kpis if k.metric_id == "load_factor_pct"), None,
    )
    assert lf is not None, f"{industry}: load_factor_pct KPI が見つからない"
    assert lf.target_value == 44.0, (
        f"{industry}: load_factor target_value={lf.target_value} "
        f"（Codex レビューで国の 2028 年度目標 44.0 に統一済）"
    )
    assert lf.baseline_value == 38.0


def test_co2_target_matches_national_target() -> None:
    """製造業の CO2 削減目標は国家目標 23.4% と整合。"""
    pkg = get_package("manufacturing")
    assert pkg is not None
    co2 = next(
        (k for k in pkg.kpis if k.metric_id == "co2_intensity_reduction_pct"),
        None,
    )
    assert co2 is not None
    assert co2.target_value == 23.4


def test_wait_handling_per_run_kpi_is_60min_for_all_industries() -> None:
    """Codex 単独提案：1回受渡し当たり 荷待ち+荷役等時間 ≤60 分は全業種共通。"""
    for industry in _INDUSTRIES:
        pkg = get_package(industry)
        assert pkg is not None
        wh = next(
            (k for k in pkg.kpis
             if k.metric_id == "wait_handling_per_run_max_minutes"),
            None,
        )
        assert wh is not None, f"{industry}: wait+handling KPI 欠落"
        assert wh.target_value == 60.0
        assert wh.legal_basis is not None
        assert "revised-logistics-act-portal" in wh.legal_basis


@pytest.mark.parametrize("industry", _INDUSTRIES)
def test_logistics_cost_ratio_baseline_from_jils(industry: JsicCategory) -> None:
    """Codex 単独提案：物流コスト売上高比率 baseline は JILS から導出。"""
    pkg = get_package(industry)
    assert pkg is not None
    cost = next(
        (k for k in pkg.kpis
         if k.metric_id == "logistics_cost_revenue_ratio_pct"),
        None,
    )
    assert cost is not None
    assert cost.baseline_value is not None
    assert cost.target_value is None  # 自社前年比管理のため標準目標は持たない


@pytest.mark.parametrize("industry", _INDUSTRIES)
def test_no_target_means_no_unsupported_legal_basis(industry: JsicCategory) -> None:
    """target_value=None の KPI は legal_basis も「推測値の出典」を持たない。

    Codex 勧告: 推測で埋めない方針の徹底（CLAUDE.md §9.4）。
    """
    pkg = get_package(industry)
    assert pkg is not None
    for kpi in pkg.kpis:
        if kpi.target_value is None and kpi.legal_basis is not None:
            # 制度ポータルの参照は OK（指標の存在根拠として使う）
            assert (
                "revised-logistics-act-portal" in kpi.legal_basis
                or "logistics.or.jp" in kpi.legal_basis
                or "meti.go.jp" in kpi.legal_basis
                or "mlit.go.jp" in kpi.legal_basis
                or "greenpartnership.jp" in kpi.legal_basis
            ), (
                f"{industry} {kpi.metric_id}: target_value=None かつ "
                f"legal_basis={kpi.legal_basis} は出典の信頼性ヒエラルキー外"
            )


def test_chain_franchise_uses_article_65() -> None:
    """連鎖化のレポートは様式第5（第65条）に紐付く。"""
    pkg = get_package("chain_franchise")
    assert pkg is not None
    form5 = next(
        (r for r in pkg.reports if r.report_id == "annual_form5_chain"),
        None,
    )
    assert form5 is not None
    assert "第65条" in form5.name


def test_non_chain_uses_article_46() -> None:
    """製造/卸/小売は様式第5（第46条）に紐付く。"""
    for industry in ("manufacturing", "wholesale", "retail"):
        pkg = get_package(industry)
        assert pkg is not None
        form5_reports = [r for r in pkg.reports if "様式第5" in r.name]
        assert len(form5_reports) >= 1, f"{industry}: 様式第5 レポート欠落"
        for r in form5_reports:
            assert "第46条" in r.name


# ---------------------------------------------------------------------------
# 4. resolve_company_package の Override 挙動
# ---------------------------------------------------------------------------


def _kpi_target(pkg: IndustryPackage, metric_id: str) -> float | None:
    kpi = next((k for k in pkg.kpis if k.metric_id == metric_id), None)
    assert kpi is not None
    return kpi.target_value


def test_resolve_without_override_returns_base() -> None:
    base = get_package("manufacturing")
    assert base is not None
    resolved = resolve_company_package("manufacturing", override=None)
    assert resolved == base


def test_resolve_approved_better_practice_overrides_target() -> None:
    """approved_better_practice は target_value を上書き反映する。"""
    override = CompanyPackageOverride(
        company_id="acme_test",
        base_industry="manufacturing",
        entries=[
            OverrideEntry(
                target_kind="kpi",
                target_id="load_factor_pct",
                category="approved_better_practice",
                rationale="自社実証で 50% を達成済（METI 目指すべき水準）",
                approved_by="山田CLO",
                diff={"target_value": 50.0},
            ),
        ],
        last_reviewed=date.today(),
    )
    resolved = resolve_company_package("manufacturing", override)
    assert _kpi_target(resolved, "load_factor_pct") == 50.0


def test_resolve_unmanaged_deviation_does_not_override() -> None:
    """unmanaged_deviation は値を反映せず、F2 標準化スコア側で減点される。"""
    override = CompanyPackageOverride(
        company_id="bad_test",
        base_industry="manufacturing",
        entries=[
            OverrideEntry(
                target_kind="kpi",
                target_id="load_factor_pct",
                category="unmanaged_deviation",
                rationale="計測体制不十分のため独自値を使用",
                diff={"target_value": 30.0},
            ),
        ],
        last_reviewed=date.today(),
    )
    resolved = resolve_company_package("manufacturing", override)
    # 国家目標 44 のまま（unmanaged は無視）
    assert _kpi_target(resolved, "load_factor_pct") == 44.0


def test_resolve_temporary_exception_active_overrides() -> None:
    """temporary_exception は期限内なら上書きする。"""
    override = CompanyPackageOverride(
        company_id="temp_test",
        base_industry="manufacturing",
        entries=[
            OverrideEntry(
                target_kind="kpi",
                target_id="load_factor_pct",
                category="temporary_exception",
                rationale="新拠点立上げ中の暫定値（FY2026 末まで）",
                approved_by="山田CLO",
                expires_at=date.today() + timedelta(days=30),
                diff={"target_value": 40.0},
            ),
        ],
        last_reviewed=date.today(),
    )
    resolved = resolve_company_package("manufacturing", override)
    assert _kpi_target(resolved, "load_factor_pct") == 40.0


def test_resolve_temporary_exception_expired_returns_base() -> None:
    """temporary_exception は期限切れなら base に戻す。"""
    override = CompanyPackageOverride(
        company_id="expired_test",
        base_industry="manufacturing",
        entries=[
            OverrideEntry(
                target_kind="kpi",
                target_id="load_factor_pct",
                category="temporary_exception",
                rationale="期限切れの暫定値",
                approved_by="山田CLO",
                expires_at=date.today() - timedelta(days=1),
                diff={"target_value": 40.0},
            ),
        ],
        last_reviewed=date.today(),
    )
    resolved = resolve_company_package("manufacturing", override)
    assert _kpi_target(resolved, "load_factor_pct") == 44.0  # base


def test_resolve_required_localization_overrides() -> None:
    """required_localization は無条件に上書き（立地・規模特性）。"""
    override = CompanyPackageOverride(
        company_id="local_test",
        base_industry="wholesale",
        entries=[
            OverrideEntry(
                target_kind="kpi",
                target_id="wait_time_avg_minutes",
                category="required_localization",
                rationale="郊外型小規模拠点で実態 60 分以下を目標化",
                approved_by="山田CLO",
                diff={"target_value": 60.0},
            ),
        ],
        last_reviewed=date.today(),
    )
    resolved = resolve_company_package("wholesale", override)
    assert _kpi_target(resolved, "wait_time_avg_minutes") == 60.0


def test_resolve_unknown_industry_raises() -> None:
    """ALL_PACKAGES に存在しない業種カテゴリは ValueError。"""
    with pytest.raises(ValueError, match="未対応の業種カテゴリ"):
        resolve_company_package("transport")  # type: ignore[arg-type]


def test_resolve_returns_frozen_package() -> None:
    """合成結果は元と独立した IndustryPackage（model_copy 経由で frozen 維持）。"""
    override = CompanyPackageOverride(
        company_id="frozen_test",
        base_industry="manufacturing",
        entries=[
            OverrideEntry(
                target_kind="kpi",
                target_id="load_factor_pct",
                category="approved_better_practice",
                rationale="挑戦値",
                approved_by="山田CLO",
                diff={"target_value": 50.0},
            ),
        ],
        last_reviewed=date.today(),
    )
    base = get_package("manufacturing")
    assert base is not None
    resolved = resolve_company_package("manufacturing", override)

    # base は不変（44.0 のまま）
    assert _kpi_target(base, "load_factor_pct") == 44.0
    # resolved だけ書換わっている（50.0）
    assert _kpi_target(resolved, "load_factor_pct") == 50.0


# ---------------------------------------------------------------------------
# 5. ALL_PACKAGES 全 4 業種の出典 URL 健全性
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("industry", _INDUSTRIES)
def test_legal_basis_urls_are_https(industry: JsicCategory) -> None:
    """target_value が None でない KPI の legal_basis は https URL を持つ。"""
    pkg = get_package(industry)
    assert pkg is not None
    for kpi in pkg.kpis:
        if kpi.target_value is not None and kpi.legal_basis is not None:
            assert kpi.legal_basis.startswith("https://"), (
                f"{industry} {kpi.metric_id}: legal_basis={kpi.legal_basis}"
            )


# ---------------------------------------------------------------------------
# 6. c.4 既存資産接続検証（ALL_MEASURES / plan_template_paths / industry_benchmarks）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("industry", _INDUSTRIES)
def test_measure_ids_consistent_with_all_measures_applicable_industries(
    industry: JsicCategory,
) -> None:
    """逆方向検証: 業種パッケージの measure_ids が ALL_MEASURES.applicable_industries と矛盾しない。

    パッケージが採用している施策は、ALL_MEASURES 側で当該業種が
    applicable_industries に含まれている（または空 = 全業種対象）必要がある。
    chain_franchise への warehouse_dx_wms 混入等の事故を防ぐ。
    """
    pkg = get_package(industry)
    assert pkg is not None
    for mid in pkg.measure_ids:
        m = get_measure(mid)
        assert m is not None, f"{industry}: measure_id {mid!r} が ALL_MEASURES 未登録"
        if not m.applicable_industries:
            continue  # 空リスト = 全業種対象
        assert industry in m.applicable_industries, (
            f"{industry}: パッケージが採用する {mid!r} の "
            f"applicable_industries={m.applicable_industries} に "
            f"{industry!r} が含まれていない（整合性エラー）"
        )


@pytest.mark.parametrize("industry", _INDUSTRIES)
def test_kpi_related_measure_ids_consistent_with_applicable_industries(
    industry: JsicCategory,
) -> None:
    """KPI.related_measure_ids も applicable_industries と整合する。"""
    pkg = get_package(industry)
    assert pkg is not None
    for kpi in pkg.kpis:
        for mid in kpi.related_measure_ids:
            m = get_measure(mid)
            assert m is not None, (
                f"{industry} KPI {kpi.metric_id}: related_measure_id "
                f"{mid!r} が ALL_MEASURES 未登録"
            )
            if not m.applicable_industries:
                continue
            assert industry in m.applicable_industries, (
                f"{industry} KPI {kpi.metric_id}: related_measure_id "
                f"{mid!r} の applicable_industries={m.applicable_industries} に "
                f"{industry!r} が含まれていない"
            )


@pytest.mark.parametrize("industry", _INDUSTRIES)
def test_plan_template_paths_exist_when_specified(
    industry: JsicCategory,
) -> None:
    """plan_template_paths に登録された全パスが実在する（推測パス禁止）。

    空 dict は許容（c.4 時点で未整備の業種があっても可）。
    """
    pkg = get_package(industry)
    assert pkg is not None
    for stage, rel_path in pkg.plan_template_paths.items():
        full = _REPO_ROOT / rel_path
        assert full.is_file(), (
            f"{industry} plan_template_paths[{stage!r}]={rel_path} は実在しない"
        )


def test_plan_template_paths_cover_all_industries() -> None:
    """4 業種すべてに starter / advanced のテンプレが揃う（c.4 で全業種充足）。"""
    for industry in _INDUSTRIES:
        pkg = get_package(industry)
        assert pkg is not None
        assert "starter" in pkg.plan_template_paths, (
            f"{industry}: starter テンプレ未登録"
        )
        assert "advanced" in pkg.plan_template_paths, (
            f"{industry}: advanced テンプレ未登録"
        )


@pytest.mark.parametrize("industry", _INDUSTRIES)
def test_logistics_cost_baseline_matches_industry_benchmarks(
    industry: JsicCategory,
) -> None:
    """logistics_cost_revenue_ratio_pct の baseline は LOGISTICS_COST_RATIO に一致。

    c.1 で _common_kpis 経由で実装済。Codex レビューで採用した「業界平均比」の
    出所が JILS で一意に決まるため、industry_packages.py 側で値を持たず
    industry_benchmarks.py から動的に引く。乖離検出用のレグレッション。
    """
    pkg = get_package(industry)
    assert pkg is not None
    cost_kpi = next(
        (k for k in pkg.kpis if k.metric_id == "logistics_cost_revenue_ratio_pct"),
        None,
    )
    assert cost_kpi is not None
    expected_ratio = LOGISTICS_COST_RATIO.get(industry)
    assert expected_ratio is not None, (
        f"{industry}: industry_benchmarks に LOGISTICS_COST_RATIO が無い"
    )
    expected_pct = expected_ratio * 100.0
    assert cost_kpi.baseline_value == pytest.approx(expected_pct), (
        f"{industry}: cost baseline={cost_kpi.baseline_value} vs "
        f"benchmarks={expected_pct}"
    )


@pytest.mark.parametrize("industry", _INDUSTRIES)
def test_measure_ids_have_no_duplicates(industry: JsicCategory) -> None:
    """measure_ids 内に重複がない（list だが set 同等の意味で扱う）。"""
    pkg = get_package(industry)
    assert pkg is not None
    assert len(pkg.measure_ids) == len(set(pkg.measure_ids)), (
        f"{industry}: measure_ids に重複あり: {pkg.measure_ids}"
    )


@pytest.mark.parametrize("industry", _INDUSTRIES)
def test_kpi_metric_ids_are_unique(industry: JsicCategory) -> None:
    """KPI の metric_id が重複しない（_common_kpis 取込時の事故防止）。"""
    pkg = get_package(industry)
    assert pkg is not None
    metric_ids = [k.metric_id for k in pkg.kpis]
    assert len(metric_ids) == len(set(metric_ids)), (
        f"{industry}: KPI metric_id に重複あり: {metric_ids}"
    )


def test_all_packages_dict_keys_match_category() -> None:
    """ALL_PACKAGES の辞書キーと IndustryPackage.category が一致する。"""
    for key, pkg in ALL_PACKAGES.items():
        assert pkg.category == key, (
            f"ALL_PACKAGES[{key!r}].category={pkg.category!r}（不一致）"
        )


# ---------------------------------------------------------------------------
# 7. c.8 連鎖化事業者の強制ガード
# ---------------------------------------------------------------------------


def test_validate_chain_franchise_actual_package_has_no_violations() -> None:
    """現行 chain_franchise パッケージは強制ガード違反 0 件。

    モジュール load 時の sanity check と同じ判定を runtime で再確認する。
    """
    pkg = get_package("chain_franchise")
    assert pkg is not None
    assert validate_chain_franchise_constraints(pkg) == []


@pytest.mark.parametrize("industry", ["manufacturing", "wholesale", "retail"])
def test_validate_chain_franchise_returns_empty_for_non_chain(
    industry: JsicCategory,
) -> None:
    """連鎖化以外のパッケージはバリデーション対象外（常に空）。"""
    pkg = get_package(industry)
    assert pkg is not None
    assert validate_chain_franchise_constraints(pkg) == []


def test_validate_detects_handling_prefix_kpi_in_chain() -> None:
    """連鎖化に handling_* プレフィックス KPI が含まれると違反検出する。"""
    base = get_package("chain_franchise")
    assert base is not None
    bad_kpi = StandardKpiDef(
        metric_id="handling_time_avg_min",
        label="禁止プレフィックス KPI",
        target_value=30.0,
        unit="分",
        baseline_value=None,
        frequency="monthly",
        owner_role="物流部",
        legal_basis=None,
        related_measure_ids=[],
    )
    bad_pkg = base.model_copy(update={"kpis": [*base.kpis, bad_kpi]})
    errors = validate_chain_franchise_constraints(bad_pkg)
    assert any("handling_" in e for e in errors)
    assert any("handling_time_avg_min" in e for e in errors)


def test_validate_detects_loading_section_measure_in_chain() -> None:
    """連鎖化に form3_section='loading' の施策が含まれると違反検出する。"""
    base = get_package("chain_franchise")
    assert base is not None
    # warehouse_dx_wms は form3_section="loading"
    bad_pkg = base.model_copy(
        update={"measure_ids": [*base.measure_ids, "warehouse_dx_wms"]},
    )
    errors = validate_chain_franchise_constraints(bad_pkg)
    assert any("warehouse_dx_wms" in e for e in errors)
    assert any("loading" in e for e in errors)


def test_validate_detects_wrong_legal_article_in_form5_report() -> None:
    """連鎖化の様式第5 レポート name に第65条が無いと違反検出する。"""
    base = get_package("chain_franchise")
    assert base is not None
    # 既存レポートの一つを「第46条」表記に書き換える
    new_reports: list[StandardReportDef] = []
    for r in base.reports:
        if r.report_id == "annual_form5_chain":
            new_reports.append(
                r.model_copy(
                    update={"name": "年次 様式第5（定期報告書／第46条）"},
                ),
            )
        else:
            new_reports.append(r)
    bad_pkg = base.model_copy(update={"reports": new_reports})
    errors = validate_chain_franchise_constraints(bad_pkg)
    assert any("第65条" in e for e in errors)


def test_chain_franchise_constants_are_consistent() -> None:
    """禁止リスト系の定数が想定通りの値（c.8 仕様の自己ドキュメント）。"""
    assert "handling_" in CHAIN_FRANCHISE_FORBIDDEN_KPI_PREFIXES
    assert "loading" in CHAIN_FRANCHISE_FORBIDDEN_FORM3_SECTIONS
    assert CHAIN_FRANCHISE_REQUIRED_LEGAL_ARTICLE == "第65条"


def test_chain_package_form5_uses_article_65_only() -> None:
    """連鎖化の様式第5 は第46条を含まず第65条のみ（第46条混入の事故防止）。"""
    pkg = get_package("chain_franchise")
    assert pkg is not None
    form5 = [r for r in pkg.reports if "様式第5" in r.name]
    assert len(form5) >= 1
    for r in form5:
        assert "第65条" in r.name
        assert "第46条" not in r.name
