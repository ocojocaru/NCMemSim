"""Portable, integrity-checked reports for Phase J advanced transport results."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from .._version import __version__
from ..hashing import canonical_hash
from .integration import (
    AdvancedTransportSpec,
    IntegratedTransportStepResult,
    MechanismEvaluationStatus,
)

_REPORT_SCHEMA = "advanced-transport-report-v1"
_RESULT_SCHEMA = "advanced-transport-step-v1"
_SCIENTIFIC_SCOPE = (
    "Mechanism-resolved compact-model evidence. Integrity hashes establish "
    "internal consistency, not authenticity, experimental calibration, "
    "fabricated-device prediction, or manufacturing yield."
)


def _json_snapshot(value: Any) -> str:
    """Return the canonical compact JSON representation used by this report."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _load_json(value: str) -> dict[str, Any]:
    def unique_keys(pairs):
        result = {}
        for key, item in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key!r}")
            result[key] = item
        return result

    def reject_constant(value: str):
        raise ValueError(f"non-finite JSON constant: {value}")

    raw = json.loads(
        value,
        object_pairs_hook=unique_keys,
        parse_constant=reject_constant,
    )
    if type(raw) is not dict:
        raise ValueError("advanced transport report must be a JSON object")
    return raw


def _baseline_snapshot(item) -> dict[str, Any]:
    return {
        "link_id": item.link_id,
        "kind": item.kind,
        "field_V_m": float(item.field_V_m),
        "potential_difference_V": float(item.potential_difference_V),
        "transmission": float(item.transmission),
        "forward_rate_Hz": float(item.forward_rate_Hz),
        "backward_rate_Hz": float(item.backward_rate_Hz),
        "net_electron_flux_m2_s": float(item.net_electron_flux_m2_s),
        "left_fg_index": item.left_fg_index,
        "right_fg_index": item.right_fg_index,
    }


def _result_snapshot(result, specification) -> dict[str, Any]:
    links = []
    for item in result.links:
        links.append(
            {
                "link_id": item.link_id,
                "kind": item.kind,
                "baseline": _baseline_snapshot(item.baseline),
                "contributions": [entry.to_dict() for entry in item.contributions],
                "total_forward_rate_Hz": float(item.total_forward_rate_Hz),
                "total_backward_rate_Hz": float(item.total_backward_rate_Hz),
                "total_net_electron_flux_m2_s": float(item.total_net_electron_flux_m2_s),
            }
        )
    return {
        "schema_version": _RESULT_SCHEMA,
        "advanced_transport_configuration_hash": specification.configuration_hash,
        "links": links,
        "net_electron_flux_by_fg_m2_s": np.asarray(
            result.net_electron_flux_by_fg_m2_s, dtype=float
        ).tolist(),
    }


def _summary(snapshot: dict[str, Any]) -> dict[str, int]:
    contributions = [
        entry
        for link in snapshot["links"]
        for entry in link["contributions"]
    ]
    return {
        "link_count": len(snapshot["links"]),
        "mechanism_contribution_count": len(contributions),
        "evaluated_contribution_count": sum(
            entry["status"]
            in {
                MechanismEvaluationStatus.EVALUATED.value,
                MechanismEvaluationStatus.DIAGNOSTIC_ONLY.value,
            }
            for entry in contributions
        ),
        "failed_contribution_count": sum(
            entry["status"] == MechanismEvaluationStatus.FAILED.value
            for entry in contributions
        ),
    }


def _check_finite_tree(value: Any) -> None:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)):
            raise ValueError("report contains a non-finite numeric value")
        return
    if isinstance(value, list):
        for item in value:
            _check_finite_tree(item)
        return
    if isinstance(value, dict):
        for item in value.values():
            _check_finite_tree(item)
        return
    raise ValueError(f"unsupported report value type: {type(value).__name__}")


def _check_payload(payload: dict[str, Any]) -> None:
    if set(payload) != {
        "schema_version", "name", "ncmemsim_version", "scientific_scope",
        "metadata", "advanced_transport", "result", "summary",
    } or payload.get("schema_version") != _REPORT_SCHEMA:
        raise ValueError("unsupported or incomplete advanced transport report schema")

    for key in ("name", "ncmemsim_version", "scientific_scope"):
        value = payload[key]
        if type(value) is not str or not value or value != value.strip():
            raise ValueError(f"{key} must be nonempty text without outer whitespace")
    if type(payload["metadata"]) is not dict:
        raise ValueError("report metadata must be a JSON object")

    advanced = payload["advanced_transport"]
    result = payload["result"]
    if type(advanced) is not dict or set(advanced) != {"configuration_hash", "data"}:
        raise ValueError("invalid advanced transport configuration section")
    if type(result) is not dict or set(result) != {"result_hash", "data"}:
        raise ValueError("invalid advanced transport result section")
    if canonical_hash(advanced["data"]) != advanced["configuration_hash"]:
        raise ValueError("advanced transport configuration hash differs")
    if canonical_hash(result["data"]) != result["result_hash"]:
        raise ValueError("advanced transport result hash differs")

    snapshot = result["data"]
    if (
        type(snapshot) is not dict
        or snapshot.get("schema_version") != _RESULT_SCHEMA
        or snapshot.get("advanced_transport_configuration_hash")
        != advanced["configuration_hash"]
        or type(snapshot.get("links")) is not list
        or type(snapshot.get("net_electron_flux_by_fg_m2_s")) is not list
    ):
        raise ValueError("invalid advanced transport result snapshot")

    attachments = advanced["data"].get("attachments")
    if advanced["data"].get("schema_version") != 1 or type(attachments) is not list:
        raise ValueError("invalid advanced transport configuration snapshot")
    attached_ids = set()
    for attachment in attachments:
        if type(attachment) is not dict:
            raise ValueError("invalid transport attachment")
        link_id = attachment.get("link_id")
        if type(link_id) is not str or not link_id or link_id in attached_ids:
            raise ValueError("invalid or duplicate transport attachment link id")
        attached_ids.add(link_id)
        tat = attachment.get("specification")
        correction = attachment.get("barrier_correction")
        if type(tat) is not dict or type(correction) is not dict:
            raise ValueError("incomplete transport attachment provenance")
        if tat.get("schema_version") != 1 or type(tat.get("species")) is not list:
            raise ValueError("invalid trap-assisted specification snapshot")
        if correction.get("schema_version") != 1:
            raise ValueError("invalid barrier-correction snapshot")

    seen_links = set()
    for link in snapshot["links"]:
        if type(link) is not dict or set(link) != {
            "link_id", "kind", "baseline", "contributions",
            "total_forward_rate_Hz", "total_backward_rate_Hz",
            "total_net_electron_flux_m2_s",
        }:
            raise ValueError("incomplete result link")
        if link["link_id"] in seen_links:
            raise ValueError("duplicate result link id")
        seen_links.add(link["link_id"])
        if type(link["contributions"]) is not list or not link["contributions"]:
            raise ValueError("result link requires mechanism contributions")

        mechanisms = set()
        for contribution in link["contributions"]:
            if type(contribution) is not dict:
                raise ValueError("invalid mechanism contribution")
            mechanism = contribution.get("mechanism")
            status = contribution.get("status")
            if mechanism in mechanisms:
                raise ValueError("duplicate mechanism contribution")
            mechanisms.add(mechanism)
            failure = contribution.get("failure")
            if status == MechanismEvaluationStatus.FAILED.value:
                if type(failure) is not dict:
                    raise ValueError("failed mechanism requires failure provenance")
                if any(float(contribution[key]) != 0.0 for key in (
                    "forward_rate_Hz", "backward_rate_Hz", "net_electron_flux_m2_s"
                )):
                    raise ValueError("failed mechanism must have zero rate and flux")
            elif failure is not None:
                raise ValueError("non-failed mechanism cannot retain failure provenance")

        if math.fsum(float(x["forward_rate_Hz"]) for x in link["contributions"]) != float(link["total_forward_rate_Hz"]):
            raise ValueError("mechanism totals do not reconstruct link totals")
        if math.fsum(float(x["backward_rate_Hz"]) for x in link["contributions"]) != float(link["total_backward_rate_Hz"]):
            raise ValueError("mechanism totals do not reconstruct link totals")
        if math.fsum(float(x["net_electron_flux_m2_s"]) for x in link["contributions"]) != float(link["total_net_electron_flux_m2_s"]):
            raise ValueError("mechanism totals do not reconstruct link totals")

    if payload["summary"] != _summary(snapshot):
        raise ValueError("advanced transport report summary differs")
    _check_finite_tree(payload)


def _csv(headers, rows) -> str:
    stream = StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return stream.getvalue()


def _text(value: Any) -> str:
    if value is None:
        return "—"
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace(
        "<", "&lt;"
    ).replace(">", "&gt;").replace("\r", "").replace("\n", "<br>")


def _table(headers, rows) -> list[str]:
    return [
        "| " + " | ".join(_text(value) for value in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(_text(value) for value in row) + " |" for row in rows),
    ]


@dataclass(frozen=True)
class AdvancedTransportReport:
    """Canonical J6 snapshot with mechanism and provenance exports."""

    payload_json: str

    def __post_init__(self) -> None:
        payload = _load_json(self.payload_json)
        _check_payload(payload)
        object.__setattr__(self, "payload_json", _json_snapshot(payload))

    @property
    def report_hash(self) -> str:
        return canonical_hash(json.loads(self.payload_json))

    def to_dict(self) -> dict[str, Any]:
        return {**json.loads(self.payload_json), "report_hash": self.report_hash}

    def to_json(self) -> str:
        return _json_snapshot(self.to_dict())

    @classmethod
    def from_json(cls, value: str) -> "AdvancedTransportReport":
        raw = _load_json(value)
        expected = raw.pop("report_hash", None)
        if expected != canonical_hash(raw):
            raise ValueError("advanced transport report hash differs")
        return cls(_json_snapshot(raw))

    def mechanisms_csv(self) -> str:
        payload = json.loads(self.payload_json)
        rows = []
        for link in payload["result"]["data"]["links"]:
            for contribution in link["contributions"]:
                failure = contribution["failure"]
                rows.append((
                    link["link_id"], link["kind"], contribution["mechanism"],
                    contribution["status"], contribution["forward_rate_Hz"],
                    contribution["backward_rate_Hz"],
                    contribution["net_electron_flux_m2_s"],
                    "" if failure is None else failure["exception_type"],
                    "" if failure is None else failure["message"],
                    _json_snapshot(contribution["evaluation"]),
                ))
        return _csv((
            "link_id", "link_kind", "mechanism", "status", "forward_rate_Hz",
            "backward_rate_Hz", "net_electron_flux_m2_s", "failure_type",
            "failure_message", "evaluation_json",
        ), rows)

    def provenance_csv(self) -> str:
        payload = json.loads(self.payload_json)
        rows = []
        advanced = payload["advanced_transport"]
        for attachment in advanced["data"]["attachments"]:
            link_id = attachment["link_id"]
            specification = attachment["specification"]
            tat_hash = canonical_hash(specification)
            for species in specification["species"]:
                rows.append((
                    "trap_species", link_id, species["name"],
                    species["parameter_status"], species["source"],
                    species["applicability"], canonical_hash(species), tat_hash,
                ))
            correction = attachment["barrier_correction"]
            rows.append((
                "barrier_correction", link_id, "image_force_barrier",
                correction["parameter_status"], correction["source"],
                correction["applicability"], canonical_hash(correction),
                advanced["configuration_hash"],
            ))
        return _csv((
            "record_type", "link_id", "name", "parameter_status", "source",
            "applicability", "evidence_hash", "parent_configuration_hash",
        ), rows)

    def to_markdown(self) -> str:
        payload = json.loads(self.payload_json)
        snapshot = payload["result"]["data"]
        summary = payload["summary"]
        lines = [
            f"# {_text(payload['name'])}", "",
            f"Report hash: `{self.report_hash}`", "",
            f"NCMemSim version: `{_text(payload['ncmemsim_version'])}`", "",
            f"Advanced transport configuration hash: `{payload['advanced_transport']['configuration_hash']}`", "",
            f"Result hash: `{payload['result']['result_hash']}`", "",
            "## Summary", "",
            f"Links: {summary['link_count']}; mechanism contributions: {summary['mechanism_contribution_count']}; "
            f"evaluated/diagnostic: {summary['evaluated_contribution_count']}; failed: {summary['failed_contribution_count']}.",
            "", "## Mechanism-resolved results", "",
        ]
        lines += _table((
            "Link", "Kind", "Mechanism", "Status", "Forward rate (Hz)",
            "Backward rate (Hz)", "Net electron flux (m^-2 s^-1)", "Failure",
        ), (
            (
                link["link_id"], link["kind"], entry["mechanism"], entry["status"],
                entry["forward_rate_Hz"], entry["backward_rate_Hz"],
                entry["net_electron_flux_m2_s"], entry["failure"],
            )
            for link in snapshot["links"] for entry in link["contributions"]
        ))
        lines += ["", "## Parameter provenance", ""]
        provenance_rows = []
        for attachment in payload["advanced_transport"]["data"]["attachments"]:
            for species in attachment["specification"]["species"]:
                provenance_rows.append((
                    attachment["link_id"], "trap_species", species["name"],
                    species["parameter_status"], species["source"], species["applicability"],
                ))
            correction = attachment["barrier_correction"]
            provenance_rows.append((
                attachment["link_id"], "barrier_correction", "image_force_barrier",
                correction["parameter_status"], correction["source"], correction["applicability"],
            ))
        lines += _table(("Link", "Record", "Name", "Status", "Source", "Applicability"), provenance_rows)
        lines += [
            "", "## Interpretation and limitations", "", payload["scientific_scope"], "",
            "A zero contribution from a disabled or unattached mechanism is not the same as a failed enabled mechanism. "
            "Failure details are retained explicitly and the direct-tunnelling baseline remains separately observable.",
            "", "Trap density and capture cross section remain structurally confounded in the compact active-path factor "
            "described by the J5 sensitivity contract. This report does not resolve that identifiability limitation.",
            "", "## Metadata", "", _text(_json_snapshot(payload["metadata"])), "",
        ]
        return "\n".join(lines)


def build_advanced_transport_report(
    result: IntegratedTransportStepResult,
    specification: AdvancedTransportSpec,
    *,
    name: str = "Advanced transport report",
    metadata: dict[str, Any] | None = None,
) -> AdvancedTransportReport:
    if not isinstance(result, IntegratedTransportStepResult):
        raise TypeError("result must be an IntegratedTransportStepResult")
    if not isinstance(specification, AdvancedTransportSpec):
        raise TypeError("specification must be an AdvancedTransportSpec")
    if type(name) is not str or not name or name != name.strip():
        raise ValueError("report name must be nonempty text without outer whitespace")
    if metadata is not None and type(metadata) is not dict:
        raise TypeError("metadata must be a JSON object")

    advanced = specification.to_dict()
    snapshot = _result_snapshot(result, specification)
    payload = {
        "schema_version": _REPORT_SCHEMA,
        "name": name,
        "ncmemsim_version": __version__,
        "scientific_scope": _SCIENTIFIC_SCOPE,
        "metadata": {} if metadata is None else metadata,
        "advanced_transport": {
            "configuration_hash": specification.configuration_hash,
            "data": advanced,
        },
        "result": {"result_hash": canonical_hash(snapshot), "data": snapshot},
        "summary": _summary(snapshot),
    }
    # Reject NaN/Inf explicitly before JSON serialization so callers receive
    # the report contract's stable validation error rather than the stdlib
    # serializer-specific message.
    _check_finite_tree(payload)
    return AdvancedTransportReport(_json_snapshot(payload))


def write_advanced_transport_report(
    report: AdvancedTransportReport,
    output_dir: str | Path,
) -> tuple[Path, ...]:
    """Write four portable UTF-8 artifacts after an all-target preflight."""
    if not isinstance(report, AdvancedTransportReport):
        raise TypeError("report must be an AdvancedTransportReport")
    contents = (
        ("manifest.json", report.to_json() + "\n"),
        ("mechanisms.csv", report.mechanisms_csv()),
        ("provenance.csv", report.provenance_csv()),
        ("report.md", report.to_markdown()),
    )
    directory = Path(output_dir).resolve()
    targets = tuple(directory / name for name, _ in contents)
    if any(target.exists() or target.is_symlink() for target in targets):
        raise FileExistsError("advanced transport report target already exists")
    directory.mkdir(parents=True, exist_ok=True)
    for target, (_, content) in zip(targets, contents):
        with target.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
    return targets


__all__ = [
    "AdvancedTransportReport",
    "build_advanced_transport_report",
    "write_advanced_transport_report",
]
