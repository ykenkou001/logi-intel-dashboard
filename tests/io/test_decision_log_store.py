"""DecisionLog 永続化（core/io/decision_log_store.py）のテスト。

Tier S1（フェーズ 5.5）。カバレッジ:
    T1  append_decision_log_entry の append-only 動作
    T2  query_decision_log_entries: decision_type フィルタ
    T3  query_decision_log_entries: from_date / to_date 範囲フィルタ
    T4  query_decision_log_entries: decided_by 完全一致フィルタ
    T5  append_decision (legacy) 後方互換 — 旧 outputs/decisions/<id>.jsonl に書ける
    T6  decision_log_entry が壊れた行をスキップして他は読める（前方互換）
    T7  query が include_legacy_cockpit=True で旧 jsonl を変換 merge し legacy_source=True
    T8  query が include_legacy_cockpit=False で旧 jsonl を無視
    T9  query が decided_at 降順 + limit 切り出し
    T10 ContextSnapshot.extra に list[str] / int / str / float の任意キー保存
    T18 S3 backend で append 後に _maybe_publish_to_s3 が呼ばれる
    T19 S3 backend で S3 上にファイルが無いとき local fallback
    T20 ContextSnapshot.compliance_overall に Literal 範囲外で ValidationError
    T21 linked_cockpit_record_id は全 decision_type で optional（cockpit_single でも必須化しない）
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from core.io.decision_log_store import (
    ContextSnapshot,
    DecisionLogEntry,
    DecisionRecord,
    _lift_legacy_record_to_entry,
    append_decision,
    append_decision_log_entry,
    load_pending_decisions,
    query_decision_log_entries,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entry(
    *,
    entry_id: str = "11111111-1111-1111-1111-111111111111",
    company_id: str = "sample_wholesale_01",
    decision_type: str = "free_form",
    decided_at: datetime | None = None,
    decided_by: str = "CLO_A",
    headline: str = "test headline",
    selected: list[str] | None = None,
    rejected: list[str] | None = None,
    snapshot_date: date | None = None,
    linked_cockpit_record_id: str | None = None,
) -> DecisionLogEntry:
    return DecisionLogEntry(
        entry_id=entry_id,
        company_id=company_id,
        decision_type=decision_type,  # type: ignore[arg-type]
        decided_at=decided_at or datetime(2026, 5, 17, 9, 0, tzinfo=UTC),
        decided_by=decided_by,
        headline=headline,
        rationale="rationale text",
        selected_measures=list(selected or []),
        rejected_measures=list(rejected or []),
        sources=[],
        context_snapshot=ContextSnapshot(
            snapshot_date=snapshot_date or date(2026, 5, 17),
            load_factor_pct=38.0,
        ),
        linked_cockpit_record_id=linked_cockpit_record_id,
    )


def _legacy(
    *,
    record_id: str = "22222222-2222-2222-2222-222222222222",
    company_id: str = "sample_wholesale_01",
    cockpit_item_id: str = "compl_wait_max_violation_20260517",
    decided_at: datetime | None = None,
    decided_by: str = "system",
    decision: str = "adopt",
    rationale: str = "from legacy",
) -> DecisionRecord:
    return DecisionRecord(
        record_id=record_id,
        company_id=company_id,
        cockpit_item_id=cockpit_item_id,
        decided_at=decided_at or datetime(2026, 5, 16, 8, 0, tzinfo=UTC),
        decided_by=decided_by,
        decision=decision,  # type: ignore[arg-type]
        rationale=rationale,
        expected_effect_jpy=12_000_000,
        linked_alerts=["alert-1"],
    )


# ---------------------------------------------------------------------------
# T1
# ---------------------------------------------------------------------------

def test_t1_append_decision_log_entry_creates_jsonl(tmp_path, monkeypatch):
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    e = _entry()
    path = append_decision_log_entry(e)
    assert path.exists()
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    loaded = DecisionLogEntry.model_validate_json(lines[0])
    assert loaded.entry_id == e.entry_id
    assert loaded.headline == e.headline
    assert loaded.legacy_source is False


# ---------------------------------------------------------------------------
# T2
# ---------------------------------------------------------------------------

def test_t2_query_filters_by_decision_type(tmp_path, monkeypatch):
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    append_decision_log_entry(
        _entry(entry_id="e1", decision_type="measure_eval_topbottom"),
    )
    append_decision_log_entry(
        _entry(entry_id="e2", decision_type="scenario_sim_baseline"),
    )
    only_top = query_decision_log_entries(
        "sample_wholesale_01",
        decision_type="measure_eval_topbottom",
    )
    assert len(only_top) == 1
    assert only_top[0].entry_id == "e1"


# ---------------------------------------------------------------------------
# T3
# ---------------------------------------------------------------------------

def test_t3_query_filters_by_date_range(tmp_path, monkeypatch):
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    early = datetime(2026, 5, 1, 9, tzinfo=UTC)
    mid = datetime(2026, 5, 10, 9, tzinfo=UTC)
    late = datetime(2026, 5, 20, 9, tzinfo=UTC)
    for i, d in enumerate([early, mid, late], start=1):
        append_decision_log_entry(_entry(entry_id=f"e{i}", decided_at=d))

    in_range = query_decision_log_entries(
        "sample_wholesale_01",
        from_date=date(2026, 5, 5),
        to_date=date(2026, 5, 15),
    )
    assert len(in_range) == 1
    assert in_range[0].entry_id == "e2"


# ---------------------------------------------------------------------------
# T4
# ---------------------------------------------------------------------------

def test_t4_query_filters_by_decided_by(tmp_path, monkeypatch):
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    append_decision_log_entry(_entry(entry_id="e1", decided_by="CLO_A"))
    append_decision_log_entry(_entry(entry_id="e2", decided_by="CLO_B"))
    only_a = query_decision_log_entries("sample_wholesale_01", decided_by="CLO_A")
    assert len(only_a) == 1
    assert only_a[0].decided_by == "CLO_A"


# ---------------------------------------------------------------------------
# T5
# ---------------------------------------------------------------------------

def test_t5_legacy_append_decision_backward_compat(tmp_path, monkeypatch):
    """旧 append_decision() で outputs/decisions/<id>.jsonl が引き続き書ける。"""
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    record = _legacy()
    path = append_decision(record)
    assert "decisions" in path.parts
    pending = load_pending_decisions(record.company_id)
    # decision="adopt" なので pending には含まれない
    assert pending == []


# ---------------------------------------------------------------------------
# T6
# ---------------------------------------------------------------------------

def test_t6_decision_log_entry_skips_invalid_lines(tmp_path, monkeypatch):
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    path = tmp_path / "decision_logs" / "sample_wholesale_01.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    valid = _entry()
    path.write_text(
        valid.model_dump_json() + "\n" + "BROKEN_LINE_NOT_JSON\n",
        encoding="utf-8",
    )
    loaded = query_decision_log_entries("sample_wholesale_01")
    assert len(loaded) == 1
    assert loaded[0].entry_id == valid.entry_id


# ---------------------------------------------------------------------------
# T7
# ---------------------------------------------------------------------------

def test_t7_query_merges_legacy_when_include_legacy_cockpit_true(
    tmp_path, monkeypatch
):
    """旧 jsonl のレコードが decision_type='cockpit_single' で merge され、
    legacy_source=True フラグが立つ。"""
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    append_decision(_legacy(record_id="legacy-1"))
    append_decision_log_entry(_entry(entry_id="new-1"))
    merged = query_decision_log_entries("sample_wholesale_01")
    assert len(merged) == 2
    legacy_entries = [e for e in merged if e.legacy_source]
    assert len(legacy_entries) == 1
    assert legacy_entries[0].decision_type == "cockpit_single"
    assert legacy_entries[0].entry_id == "legacy-1"
    assert legacy_entries[0].linked_cockpit_record_id == "legacy-1"


# ---------------------------------------------------------------------------
# T8
# ---------------------------------------------------------------------------

def test_t8_query_excludes_legacy_when_include_legacy_cockpit_false(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    append_decision(_legacy())
    append_decision_log_entry(_entry(entry_id="new-1"))
    only_new = query_decision_log_entries(
        "sample_wholesale_01", include_legacy_cockpit=False
    )
    assert len(only_new) == 1
    assert only_new[0].entry_id == "new-1"
    assert only_new[0].legacy_source is False


# ---------------------------------------------------------------------------
# T9
# ---------------------------------------------------------------------------

def test_t9_query_sorts_by_decided_at_desc_and_applies_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    base = datetime(2026, 5, 17, 9, tzinfo=UTC)
    for i in range(5):
        append_decision_log_entry(
            _entry(entry_id=f"e{i}", decided_at=base + timedelta(days=i)),
        )
    top3 = query_decision_log_entries("sample_wholesale_01", limit=3)
    assert len(top3) == 3
    assert [e.entry_id for e in top3] == ["e4", "e3", "e2"]


# ---------------------------------------------------------------------------
# T10
# ---------------------------------------------------------------------------

def test_t10_context_snapshot_extra_preserves_arbitrary_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    snapshot = ContextSnapshot(
        snapshot_date=date(2026, 5, 17),
        load_factor_pct=42.0,
        extra={
            "rank": 3,
            "total_score": 87.5,
            "comment": "Top 推薦",
            "linked_alerts": ["alert-1", "alert-2"],
            "nullable": None,
        },
    )
    entry = _entry()
    entry = entry.model_copy(update={"context_snapshot": snapshot})
    append_decision_log_entry(entry)
    loaded = query_decision_log_entries("sample_wholesale_01")[0]
    assert loaded.context_snapshot.extra["rank"] == 3
    assert loaded.context_snapshot.extra["total_score"] == 87.5
    assert loaded.context_snapshot.extra["comment"] == "Top 推薦"
    assert loaded.context_snapshot.extra["linked_alerts"] == ["alert-1", "alert-2"]
    assert loaded.context_snapshot.extra["nullable"] is None


# ---------------------------------------------------------------------------
# T18: S3 backend publish
# ---------------------------------------------------------------------------

def test_t18_s3_backend_publishes_after_append(tmp_path, monkeypatch):
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    monkeypatch.setenv("LOGI_STORAGE_BACKEND", "s3")
    published_paths: list[Path] = []

    class FakeStorage:
        def publish(self, path):
            published_paths.append(path)

        def read_bytes(self, key):
            return None

    with patch("core.storage.get_storage", return_value=FakeStorage()):
        append_decision_log_entry(_entry())
    assert len(published_paths) == 1
    assert "decision_logs" in published_paths[0].parts


# ---------------------------------------------------------------------------
# T19: S3 backend fallback
# ---------------------------------------------------------------------------

def test_t19_s3_backend_falls_back_to_local_when_s3_empty(tmp_path, monkeypatch):
    """S3 から read_bytes が None を返したら、ローカル jsonl で読める。"""
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))

    class EmptyS3Storage:
        def publish(self, path):
            pass

        def read_bytes(self, key):
            return None

    # 1. ローカル backend で append
    append_decision_log_entry(_entry(entry_id="local-1"))

    # 2. S3 backend に切替えて read。read_bytes は None → local fallback で読める
    monkeypatch.setenv("LOGI_STORAGE_BACKEND", "s3")
    with patch("core.storage.get_storage", return_value=EmptyS3Storage()):
        loaded = query_decision_log_entries("sample_wholesale_01")
    assert len(loaded) == 1
    assert loaded[0].entry_id == "local-1"


# ---------------------------------------------------------------------------
# T20: Literal validation
# ---------------------------------------------------------------------------

def test_t20_validation_error_on_invalid_compliance_overall():
    """ContextSnapshot.compliance_overall に Literal 範囲外値で ValidationError。"""
    with pytest.raises(ValidationError):
        ContextSnapshot(
            snapshot_date=date(2026, 5, 17),
            compliance_overall="unknown_value",  # Literal 範囲外
        )


# ---------------------------------------------------------------------------
# T21: linked_cockpit_record_id optional
# ---------------------------------------------------------------------------

def test_t21_linked_cockpit_record_id_is_optional_for_all_decision_types(
    tmp_path, monkeypatch
):
    """linked_cockpit_record_id は全 decision_type で optional。
    cockpit_single でも明示連携したい時のみ設定すれば良い仕様確認。"""
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    for dt in (
        "cockpit_single",
        "measure_eval_topbottom",
        "scenario_sim_baseline",
        "plan_draft_freeze",
        "free_form",
    ):
        entry = _entry(
            entry_id=f"e-{dt}",
            decision_type=dt,
            linked_cockpit_record_id=None,
        )
        append_decision_log_entry(entry)
    all_entries = query_decision_log_entries("sample_wholesale_01", limit=100)
    assert len(all_entries) == 5
    for e in all_entries:
        assert e.linked_cockpit_record_id is None


# ---------------------------------------------------------------------------
# 補助: _lift_legacy_record_to_entry の単体動作
# ---------------------------------------------------------------------------

def test_lift_legacy_record_to_entry_preserves_linked_alerts():
    """旧 DecisionRecord の linked_alerts / expected_effect_jpy が
    新 entry.context_snapshot.extra に詰め直されることを確認。"""
    record = _legacy(decision="postpone")
    entry = _lift_legacy_record_to_entry(record)
    assert entry.legacy_source is True
    assert entry.decision_type == "cockpit_single"
    assert entry.linked_cockpit_record_id == record.record_id
    assert entry.tags == ["decision:postpone"]
    assert entry.context_snapshot.extra["expected_effect_jpy"] == 12_000_000
    assert entry.context_snapshot.extra["linked_alerts"] == ["alert-1"]


# ---------------------------------------------------------------------------
# append_decision_log_entry: entry_id 必須の防御的検証
# ---------------------------------------------------------------------------

def test_append_decision_log_entry_rejects_empty_entry_id(tmp_path, monkeypatch):
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    bad = _entry(entry_id="")
    with pytest.raises(ValueError, match="entry_id is required"):
        append_decision_log_entry(bad)


def test_append_decision_log_entry_rejects_legacy_source_true(tmp_path, monkeypatch):
    """legacy_source=True のエントリは write 不可（read-only flag）。"""
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    bad = DecisionLogEntry(
        entry_id="x",
        company_id="sample_wholesale_01",
        decision_type="free_form",
        decided_at=datetime(2026, 5, 17, 9, tzinfo=UTC),
        decided_by="CLO",
        headline="x",
        context_snapshot=ContextSnapshot(snapshot_date=date(2026, 5, 17)),
        legacy_source=True,
    )
    with pytest.raises(ValueError, match="legacy_source=True"):
        append_decision_log_entry(bad)


# ---------------------------------------------------------------------------
# Codex 最終レビュー指摘 1: S3 backend で既存ログを失わない append
# ---------------------------------------------------------------------------

def test_s3_backend_append_preserves_existing_remote_jsonl(tmp_path, monkeypatch):
    """S3 上に既存 1 行 + ローカル空（Lambda コールドスタート）状態で append すると、
    S3 既存ログを失わず合計 2 行になる。Codex 最終レビュー指摘 1 への回帰テスト。"""
    monkeypatch.setenv("LOGI_OUTPUTS_DIR", str(tmp_path))
    monkeypatch.setenv("LOGI_STORAGE_BACKEND", "s3")

    # 既存 S3 1 行（別 entry_id）
    existing_entry = _entry(
        entry_id="remote-1", decided_at=datetime(2026, 5, 15, 9, tzinfo=UTC),
    )
    existing_jsonl = existing_entry.model_dump_json() + "\n"

    class FakeS3Storage:
        published_content: str = ""

        def publish(self, path):
            # publish 時点でローカルに何が書かれているかを記録
            self.published_content = path.read_text(encoding="utf-8")

        def read_bytes(self, key):
            return existing_jsonl.encode("utf-8")

    fake = FakeS3Storage()
    with patch("core.storage.get_storage", return_value=fake):
        append_decision_log_entry(
            _entry(entry_id="new-1", decided_at=datetime(2026, 5, 17, 9, tzinfo=UTC)),
        )

    # publish 内容に S3 既存 1 行 + 新規 1 行の計 2 行が含まれる
    assert "remote-1" in fake.published_content
    assert "new-1" in fake.published_content
    assert fake.published_content.count("\n") == 2
