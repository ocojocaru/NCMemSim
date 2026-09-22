from __future__ import annotations

import csv
import importlib.util
from io import StringIO
from pathlib import Path

from ncmemsim.transport import (
    AdvancedTransportReport,
    MechanismEvaluationStatus,
    TransportMechanism,
)

ROOT = Path(__file__).resolve().parents[1]

def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "examples" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

NORMAL = _load("phase_j6_normal_reference", "phase_j6_advanced_transport_report.py")
FAILURE = _load(
    "phase_j6_failure_reference",
    "phase_j6_advanced_transport_failure_report.py",
)

def _rows(report):
    return list(csv.DictReader(StringIO(report.mechanisms_csv())))

def test_normal_reference_is_deterministic_and_has_no_failures():
    first = NORMAL.build_reference_report()
    second = NORMAL.build_reference_report()
    assert first.to_json() == second.to_json()
    assert first.to_dict()["summary"]["failed_contribution_count"] == 0
    rows = _rows(first)
    assert any(
        row["mechanism"] == TransportMechanism.TRAP_ASSISTED.value
        and row["status"] == MechanismEvaluationStatus.EVALUATED.value
        for row in rows
    )

def test_normal_reference_exports_and_round_trips(tmp_path):
    report = NORMAL.build_reference_report()
    paths = NORMAL.write_reference_report(tmp_path / "normal")
    assert {p.name for p in paths} == {
        "manifest.json", "mechanisms.csv", "provenance.csv", "report.md",
    }
    restored = AdvancedTransportReport.from_json(
        (tmp_path / "normal" / "manifest.json").read_text(encoding="utf-8")
    )
    assert restored.report_hash == report.report_hash

def test_normal_reference_provenance_is_explicit():
    rows = list(csv.DictReader(StringIO(
        NORMAL.build_reference_report().provenance_csv()
    )))
    assert {row["record_type"] for row in rows} == {
        "trap_species", "barrier_correction",
    }
    assert all(row["parameter_status"] == "assumed" for row in rows)
    assert all(row["source"] and row["applicability"] for row in rows)
    assert all(len(row["evidence_hash"]) == 64 for row in rows)

def test_deliberate_failure_is_deterministic_and_isolated():
    first = FAILURE.build_reference_report()
    second = FAILURE.build_reference_report()
    assert first.to_json() == second.to_json()
    assert first.to_dict()["summary"]["failed_contribution_count"] == 1
    rows = _rows(first)
    failed = next(
        row for row in rows
        if row["mechanism"] == TransportMechanism.TRAP_ASSISTED.value
        and row["status"] == MechanismEvaluationStatus.FAILED.value
    )
    assert failed["failure_type"] == "ArithmeticError"
    assert "non-finite optional mechanism flux" in failed["failure_message"]
    direct = next(
        row for row in rows
        if row["link_id"] == failed["link_id"]
        and row["mechanism"] == TransportMechanism.DIRECT_TUNNELLING.value
    )
    assert direct["status"] == MechanismEvaluationStatus.EVALUATED.value
    assert float(direct["forward_rate_Hz"]) > 0.0

def test_deliberate_failure_exports_and_round_trips(tmp_path):
    report = FAILURE.build_reference_report()
    paths = FAILURE.write_reference_report(tmp_path / "failure")
    assert {p.name for p in paths} == {
        "manifest.json", "mechanisms.csv", "provenance.csv", "report.md",
    }
    restored = AdvancedTransportReport.from_json(
        (tmp_path / "failure" / "manifest.json").read_text(encoding="utf-8")
    )
    assert restored.report_hash == report.report_hash
    assert report.to_dict()["metadata"]["reference_kind"] == "deliberate_failure"

def test_normal_and_failure_references_are_distinct_and_interpretable():
    normal = NORMAL.build_reference_report()
    failure = FAILURE.build_reference_report()
    assert normal.report_hash != failure.report_hash
    assert (
        normal.to_dict()["advanced_transport"]["configuration_hash"]
        != failure.to_dict()["advanced_transport"]["configuration_hash"]
    )
    text = failure.to_markdown()
    assert "failed: 1" in text
    assert "not authenticity, experimental calibration" in text
    assert "structurally confounded" in text
