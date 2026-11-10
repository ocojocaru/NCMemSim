# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Compare synthetic finite- and infinite-barrier Ge optical responses."""

import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples.phase_t3_finite_confinement_reference import _baseline
from ncmemsim import DeviceBuilder, PhysicsModel, SimulationConfig
from ncmemsim._version import __version__
from ncmemsim.finite_confinement_context import (
    FiniteConfinementOpticalBinding, FiniteConfinementOpticalContext,
)
from ncmemsim.hashing import canonical_hash
from ncmemsim.materials import make_ge
from ncmemsim.materials.finite_confinement import evaluate_finite_confinement
from ncmemsim.materials.structural import ConfinementDomain, SphericalConfinementProfile
from ncmemsim.materials.temperature import GapKind
from ncmemsim.spectral_absorption import evaluate_floating_gate_spectrum
from ncmemsim.spectral_sources import SpectralEvidence, TabulatedSpectrum
from ncmemsim.structural_optical_context import StructuralOpticalBinding, StructuralOpticalContext
from ncmemsim.temperature_context import ThermalContext


SCOPE = (
    'Synthetic Ge Gamma gap diagnostic with independent carrier confinement. '
    'The L gap uses the common thermal baseline. Inputs are assumed. '
    'The study concerns absorption in one floating gate at fixed volume fraction, '
    'with no device calibration or excitonic contribution.'
)
WAVELENGTH_MIN_NM = 1200.0
WAVELENGTH_MAX_NM = 1850.0
SPECTRAL_EVIDENCE = SpectralEvidence(
    'T5 synthetic flat spectrum', 'controlled optical comparison', 'ASSUMED',
    'canonical units', (), 'same flat shape on nested wavelength grids',
    'unknown', SCOPE,
)


def _source(intervals):
    span = WAVELENGTH_MAX_NM - WAVELENGTH_MIN_NM
    nodes = tuple(WAVELENGTH_MIN_NM + span * index / intervals for index in range(intervals + 1))
    return TabulatedSpectrum(nodes, (1.0 / span,) * len(nodes), SPECTRAL_EVIDENCE)


def _problem(radius_nm, electron_depth_eV, hole_depth_eV):
    device = DeviceBuilder.v2(
        1, nc_material=make_ge(), nc_diameter_nm=2 * radius_nm,
        fg_thickness_nm=12, nc_volume_fraction=0.2,
    )
    thermal = ThermalContext.from_nominal(device, PhysicsModel.default(), SimulationConfig())
    resolution = thermal.resolve(temperature_K=300)
    layer = resolution.device.get_layer('FG1')
    radius = layer.nc_diameter_nm * 0.5e-9
    electron = replace(_baseline('electron', 0.2, electron_depth_eV), dot_material='Ge', radius_m=radius)
    hole = replace(_baseline('hole', 0.4, hole_depth_eV), dot_material='Ge', radius_m=radius)
    evidence = electron.applicability
    profile = SphericalConfinementProfile(
        'T5 infinite reference', layer.name, GapKind.GAMMA, 'effective_scalar',
        ConfinementDomain('Ge', 300, 300, 1e-9, 4e-9, evidence),
        electron.inside_mass_m0, hole.inside_mass_m0, evidence, evidence, evidence,
    )
    owner = StructuralOpticalContext(
        resolution, (StructuralOpticalBinding(layer.name, (), (profile,), 0.0),),
    )
    return owner, FiniteConfinementOpticalBinding(
        layer.name, GapKind.GAMMA, 'synthetic scalar hole', electron, hole,
    )


def _response(context, layer, model, source):
    identity = context.contract_hash + '/' + layer.name
    spectrum = evaluate_floating_gate_spectrum(
        source, layer, optical_model=model, model_identity=identity,
        wavelength_min_nm=WAVELENGTH_MIN_NM, wavelength_max_nm=WAVELENGTH_MAX_NM,
        evidence=SPECTRAL_EVIDENCE,
    )
    return {
        'model_identity': identity,
        'spectrum': spectrum.summary,
        'optical_points': [
            {
                'wavelength_nm': point.wavelength_nm,
                'gamma_gap_eV': point.direct_gap_eV,
                'l_gap_eV': point.indirect_gap_eV,
                'alpha_m_inv': point.absorption_coefficient_m_inv,
            }
            for point in (model.evaluate(layer.nc_material, nm) for nm in (1300, 1550, 1650))
        ],
    }


def _case(radius_nm, electron_depth_eV, hole_depth_eV, sources):
    owner, binding = _problem(radius_nm, electron_depth_eV, hole_depth_eV)
    layer = owner.thermal_resolution.device.get_layer(binding.layer_name)
    outcomes = {
        carrier: evaluate_finite_confinement(getattr(binding, carrier)).to_dict()
        for carrier in ('electron', 'hole')
    }
    finite = (
        FiniteConfinementOpticalContext(owner, (binding,))
        if all(result['status'] == 'bound' for result in outcomes.values())
        else None
    )
    infinite_model = owner.optical_model(layer.name)
    finite_model = None if finite is None else finite.optical_model(layer.name)
    return {
        'infinite_context': owner.to_dict(),
        'binding': binding.to_dict(),
        'carrier_outcomes': outcomes,
        'finite_status': 'available' if finite is not None else 'unavailable',
        'finite_context_hash': None if finite is None else finite.contract_hash,
        'responses': {
            str(intervals): {
                'infinite': _response(owner, layer, infinite_model, source),
                'finite': None if finite is None else _response(finite, layer, finite_model, source),
            }
            for intervals, source in sources.items()
        },
    }


def run_study():
    """Return fixed-physics wavelength refinement and fixed-grid sensitivity."""
    sources = {intervals: _source(intervals) for intervals in (16, 32, 64, 128)}
    fine = {128: sources[128]}
    report = {
        'schema_version': 't5-finite-confinement-optical-study-v1',
        'software_version': __version__,
        'scope': SCOPE,
        'sources_by_intervals': {str(key): source.to_dict() for key, source in sources.items()},
        'wavelength_refinement': _case(4, 0.8, 0.15, sources),
        'physical_sensitivity': {
            'smaller_radius': _case(2, 0.8, 0.15, fine),
            'shallower_electron_well': _case(4, 0.4, 0.15, fine),
            'unbound_hole': _case(4, 0.8, 0.0, fine),
        },
    }
    report['study_hash'] = canonical_hash(report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = run_study()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(report['study_hash'])
