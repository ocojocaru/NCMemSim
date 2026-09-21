from __future__ import annotations

import csv
from io import StringIO
import json

import numpy as np
import pytest

from ncmemsim import DeviceBuilder, DeviceState, PhysicsModel
from ncmemsim.fieldsolver import FieldSolver1D
from ncmemsim.hashing import canonical_hash
def _json_snapshot(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


from ncmemsim.transport import (
    AdvancedTransportEngine,
    AdvancedTransportReport,
    AdvancedTransportSpec,
    ImageForceBarrierSpec,
    IntegratedLinkTransportResult,
    IntegratedTransportStepResult,
    MechanismContribution,
    MechanismEvaluationStatus,
    MechanismFailure,
    TATLinkAttachment,
    TransportConfig,
    TransportEngine,
    TransportMechanism,
    TrapAssistedTransportSpec,
    TrapParameterStatus,
    TrapSpecies,
    build_advanced_transport_report,
    write_advanced_transport_report,
)


def _context():
    device = DeviceBuilder.v2(n_fgs=2, inter_fg_sio2_nm=1.0, name="j6-report-test")
    physics = PhysicsModel.default()
    baseline = TransportEngine(
        physics.tunneling,
        TransportConfig(attempt_frequency_Hz=1.0e13, default_barrier_eV=0.25, max_transfer_fraction_per_step=0.05),
    )
    link_id = next(link.link_id for link in baseline.build_network(device).links if link.kind == "inter_fg")
    trap = TrapSpecies(
        name="j6-synthetic-electron-trap",
        energy_depth_J=0.18 * 1.602176634e-19,
        position_fraction=0.5,
        density_m3=8.0e22,
        capture_cross_section_m2=2.0e-20,
        attempt_frequency_Hz=2.0e11,
        parameter_status=TrapParameterStatus.ASSUMED,
        source="synthetic J6 report test",
        applicability="report serialization and mechanism accounting only",
    )
    tat = TrapAssistedTransportSpec(enabled=True, species=(trap,))
    correction = ImageForceBarrierSpec(
        enabled=True,
        relative_permittivity=3.9,
        parameter_status=TrapParameterStatus.LITERATURE,
        source="J6 reporting test literature-like provenance",
        applicability="compact symmetric two-interface reporting test",
    )
    specification = AdvancedTransportSpec((TATLinkAttachment(link_id, tat, correction),))
    engine = AdvancedTransportEngine(baseline, specification)
    state = DeviceState.empty_for_device(device)
    state.floating_gates[0].P0[:] = 0.0
    state.floating_gates[0].P1[:] = 1.0
    state.floating_gates[0].P2[:] = 0.0
    profile = FieldSolver1D().solve(device, 4.0, np.zeros(device.number_of_fgs()))
    result = engine.evaluate(device, state, profile, physics.occupancy)
    return result, specification, link_id


def _report():
    result, specification, _ = _context()
    return build_advanced_transport_report(
        result, specification,
        name="J6 synthetic advanced transport report",
        metadata={"purpose": "software verification"},
    )


def test_report_is_deterministic_and_round_trips():
    first = _report(); second = _report()
    assert first.to_json() == second.to_json()
    restored = AdvancedTransportReport.from_json(first.to_json())
    assert restored.to_dict() == first.to_dict()


def test_report_hash_detects_manifest_tampering():
    raw = json.loads(_report().to_json()); raw["name"] = "tampered"
    with pytest.raises(ValueError, match="report hash differs"):
        AdvancedTransportReport.from_json(_json_snapshot(raw))


def test_nested_result_hash_is_checked():
    raw = _report().to_dict(); raw.pop("report_hash")
    raw["result"]["data"]["links"][0]["kind"] = "tampered-kind"
    with pytest.raises(ValueError, match="result hash differs"):
        AdvancedTransportReport(_json_snapshot(raw))


def test_configuration_hash_is_checked():
    raw = _report().to_dict(); raw.pop("report_hash")
    raw["advanced_transport"]["configuration_hash"] = "0" * 64
    with pytest.raises(ValueError, match="configuration hash differs"):
        AdvancedTransportReport(_json_snapshot(raw))


def test_mechanism_totals_are_reconstructed():
    raw = _report().to_dict(); raw.pop("report_hash")
    raw["result"]["data"]["links"][0]["total_forward_rate_Hz"] += 1.0
    raw["result"]["result_hash"] = canonical_hash(raw["result"]["data"])
    with pytest.raises(ValueError, match="do not reconstruct"):
        AdvancedTransportReport(_json_snapshot(raw))


def test_mechanisms_csv_retains_mechanism_status_and_evaluation():
    rows = list(csv.DictReader(StringIO(_report().mechanisms_csv())))
    mechanisms = {row["mechanism"] for row in rows}
    assert "direct_tunnelling" in mechanisms and "trap_assisted" in mechanisms
    attached = next(row for row in rows if row["mechanism"] == "trap_assisted" and row["status"] == "evaluated")
    assert attached["evaluation_json"] not in {"", "null"}
    assert attached["failure_type"] == ""


def test_provenance_csv_retains_sources_statuses_and_hashes():
    rows = list(csv.DictReader(StringIO(_report().provenance_csv())))
    assert {row["record_type"] for row in rows} == {"trap_species", "barrier_correction"}
    trap = next(row for row in rows if row["record_type"] == "trap_species")
    correction = next(row for row in rows if row["record_type"] == "barrier_correction")
    assert trap["parameter_status"] == "assumed"
    assert trap["source"] == "synthetic J6 report test"
    assert len(trap["evidence_hash"]) == 64
    assert correction["parameter_status"] == "literature"


def test_markdown_states_interpretation_and_limitations():
    text = _report().to_markdown()
    assert "Mechanism-resolved results" in text
    assert "Parameter provenance" in text
    assert "not authenticity, experimental calibration" in text
    assert "not the same as a failed enabled mechanism" in text
    assert "structurally confounded" in text


def test_writer_emits_four_portable_artifacts(tmp_path):
    report = _report(); targets = write_advanced_transport_report(report, tmp_path / "bundle")
    assert tuple(path.name for path in targets) == ("manifest.json", "mechanisms.csv", "provenance.csv", "report.md")
    restored = AdvancedTransportReport.from_json((tmp_path / "bundle" / "manifest.json").read_text(encoding="utf-8"))
    assert restored.report_hash == report.report_hash


def test_writer_refuses_existing_target_before_writing_anything(tmp_path):
    target = tmp_path / "bundle"; target.mkdir(); (target / "mechanisms.csv").write_text("occupied\n", encoding="utf-8")
    with pytest.raises(FileExistsError, match="target already exists"):
        write_advanced_transport_report(_report(), target)
    assert not (target / "manifest.json").exists()
    assert not (target / "provenance.csv").exists()


def test_metadata_must_be_json_object():
    result, specification, _ = _context()
    with pytest.raises(TypeError, match="metadata"):
        build_advanced_transport_report(result, specification, metadata=["bad"])


def test_deliberate_failed_mechanism_is_reported_without_hiding_direct_baseline():
    result, specification, link_id = _context(); links = []
    for link in result.links:
        if link.link_id != link_id:
            links.append(link); continue
        direct = link.contribution(TransportMechanism.DIRECT_TUNNELLING)
        failed = MechanismContribution(
            mechanism=TransportMechanism.TRAP_ASSISTED,
            status=MechanismEvaluationStatus.FAILED,
            forward_rate_Hz=0.0,
            backward_rate_Hz=0.0,
            net_electron_flux_m2_s=0.0,
            failure=MechanismFailure("DeliberateReferenceFailure", "intentional J6 reporting failure fixture"),
        )
        links.append(IntegratedLinkTransportResult(
            baseline=link.baseline,
            contributions=(direct, failed),
            total_forward_rate_Hz=direct.forward_rate_Hz,
            total_backward_rate_Hz=direct.backward_rate_Hz,
            total_net_electron_flux_m2_s=direct.net_electron_flux_m2_s,
        ))
    failed_result = IntegratedTransportStepResult(
        baseline=result.baseline,
        links=tuple(links),
        net_electron_flux_by_fg_m2_s=result.baseline.net_electron_flux_by_fg_m2_s,
    )
    report = build_advanced_transport_report(failed_result, specification, name="J6 deliberate failure reporting reference")
    assert report.to_dict()["summary"]["failed_contribution_count"] == 1
    rows = list(csv.DictReader(StringIO(report.mechanisms_csv())))
    failed_row = next(row for row in rows if row["status"] == "failed")
    assert failed_row["failure_type"] == "DeliberateReferenceFailure"
    direct_row = next(row for row in rows if row["link_id"] == link_id and row["mechanism"] == "direct_tunnelling")
    assert float(direct_row["forward_rate_Hz"]) == direct.forward_rate_Hz


def test_report_rejects_nonfinite_metadata_values():
    result, specification, _ = _context()
    with pytest.raises(ValueError, match="non-finite"):
        build_advanced_transport_report(result, specification, metadata={"bad": float("nan")})
