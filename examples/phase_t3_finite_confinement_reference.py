# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Controlled finite/infinite spherical-well comparisons with synthetic inputs."""

import argparse
from collections import Counter
from dataclasses import replace
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ncmemsim._version import __version__
from ncmemsim.constants import ELECTRON_MASS_KG, PLANCK_J_S
from ncmemsim.hashing import canonical_hash
from ncmemsim.materials.finite_confinement import evaluate_finite_confinement
from ncmemsim.materials.finite_confinement_contracts import (
    FiniteConfinementRequest,
    confinement_depth_eV_to_J,
)
from ncmemsim.materials.provenance import ParameterStatus
from ncmemsim.materials.structural import StructuralEvidence


SCOPE = (
    "Synthetic spherical l=0 independent-particle study. Inputs are assumed. "
    "Pair sums are kinetic confinement contributions. Coulomb attraction, "
    "dielectric polarization and optical transition energies are outside scope."
)


def _baseline(carrier, mass, depth_eV):
    evidence = StructuralEvidence(
        "T3 synthetic fixture", "controlled numerical comparison",
        ParameterStatus.ASSUMED, SCOPE,
    )
    return FiniteConfinementRequest(
        carrier=carrier,
        dot_material="synthetic dot",
        host_material="synthetic host",
        radius_m=2e-9,
        inside_mass_m0=mass,
        outside_mass_m0=mass,
        depth_J=confinement_depth_eV_to_J(depth_eV),
        temperature_K=300,
        radius_evidence=evidence,
        inside_mass_evidence=evidence,
        outside_mass_evidence=evidence,
        depth_evidence=evidence,
        applicability=evidence,
    )


def _compare(request):
    finite = evaluate_finite_confinement(request)
    infinite_energy = PLANCK_J_S**2 / (
        8 * ELECTRON_MASS_KG * request.inside_mass_m0 * request.radius_m**2
    )
    return {
        "finite": finite.to_dict(),
        "infinite_energy_J": infinite_energy,
    }


def run_reference():
    """Evaluate matched controls, including radii with unavailable pair sums."""
    electron = _baseline("electron", 0.2, 0.8)
    hole = _baseline("hole", 0.4, 0.15)
    sweeps = {
        "radius_m": (1e-9, 2e-9, 4e-9),
        "depth_J": tuple(confinement_depth_eV_to_J(v) for v in (0.05, 0.8, 10_000)),
        "inside_mass_m0": (0.1, 0.2, 0.4),
        "outside_mass_m0": (0.1, 0.2, 0.4),
    }
    single = {
        axis: [_compare(replace(electron, **{axis: value})) for value in values]
        for axis, values in sweeps.items()
    }
    pairs = []
    for radius, electron_row in zip(sweeps["radius_m"], single["radius_m"]):
        hole_row = _compare(replace(hole, radius_m=radius))
        statuses = (electron_row["finite"]["status"], hole_row["finite"]["status"])
        both_bound = statuses == ("bound", "bound")
        pairs.append({
            "radius_m": radius,
            "electron": electron_row,
            "hole": hole_row,
            "status": "available" if both_bound else "unavailable",
            "finite_kinetic_sum_J": (
                electron_row["finite"]["energy_J"] + hole_row["finite"]["energy_J"]
                if both_bound else None
            ),
            "infinite_kinetic_sum_J": (
                electron_row["infinite_energy_J"] + hole_row["infinite_energy_J"]
            ),
        })
    counts = Counter(pair["status"] for pair in pairs)
    report = {
        "schema_version": "t3-finite-confinement-reference-v1",
        "software_version": __version__,
        "scope": SCOPE,
        "single_carrier_sweeps": single,
        "pairs": pairs,
        "pair_counts": {"attempted": len(pairs), **dict(counts)},
    }
    report["reference_hash"] = canonical_hash(report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = run_reference()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"pair_counts": report["pair_counts"], "reference_hash": report["reference_hash"]}))
