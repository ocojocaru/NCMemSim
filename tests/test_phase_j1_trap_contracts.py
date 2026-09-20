from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
from pathlib import Path

import pytest

from ncmemsim.transport import (
    TrapAssistedModel,
    TrapAssistedTransportSpec,
    TrapCarrier,
    TrapEnergyReference,
    TrapParameterStatus,
    TrapSpecies,
)


ROOT = Path(__file__).resolve().parents[1]


def species(**overrides) -> TrapSpecies:
    values = {
        "name": "oxide-electron-trap",
        "energy_depth_J": 2.403264951e-19,
        "position_fraction": 0.5,
        "density_m3": 1.0e23,
        "capture_cross_section_m2": 1.0e-19,
        "attempt_frequency_Hz": 1.0e13,
        "parameter_status": TrapParameterStatus.ASSUMED,
        "source": "synthetic J1 contract example",
        "applicability": "homogeneous dielectric link; contract validation only",
    }
    values.update(overrides)
    return TrapSpecies(**values)


def test_public_contract_and_fixed_conventions():
    item = species()
    assert item.carrier is TrapCarrier.ELECTRON
    assert item.energy_reference is TrapEnergyReference.CONDUCTION_BAND_DEPTH
    assert item.energy_depth_J > 0
    assert item.density_m3 == 1.0e23
    assert TrapAssistedModel.SEQUENTIAL_TWO_STEP_WKB.value == "sequential_two_step_wkb"


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("energy_depth_J", 0.0, ValueError),
        ("energy_depth_J", -1.0, ValueError),
        ("energy_depth_J", float("nan"), ValueError),
        ("position_fraction", 0.0, ValueError),
        ("position_fraction", 1.0, ValueError),
        ("density_m3", -1.0, ValueError),
        ("density_m3", float("inf"), ValueError),
        ("capture_cross_section_m2", 0.0, ValueError),
        ("attempt_frequency_Hz", 0.0, ValueError),
        ("density_m3", True, TypeError),
    ],
)
def test_numeric_contract_rejects_invalid_values(field, value, error):
    with pytest.raises(error):
        species(**{field: value})


@pytest.mark.parametrize("field", ["name", "source", "applicability"])
@pytest.mark.parametrize("value", ["", " padded ", None])
def test_provenance_text_is_explicit(field, value):
    with pytest.raises(ValueError):
        species(**{field: value})


def test_enums_are_strict_and_no_unit_aliases_are_accepted():
    with pytest.raises(TypeError):
        species(parameter_status="assumed")
    with pytest.raises(TypeError):
        species(carrier="electron")
    with pytest.raises(TypeError):
        species(energy_reference="conduction_band_depth")
    with pytest.raises(TypeError):
        TrapSpecies(
            name="bad-units",
            energy_eV=1.5,
            position_fraction=0.5,
            density_cm3=1e17,
            capture_cross_section_m2=1e-19,
            attempt_frequency_Hz=1e13,
            parameter_status=TrapParameterStatus.ASSUMED,
            source="test",
            applicability="test",
        )


def test_species_is_immutable_and_has_deterministic_hash():
    item = species()
    with pytest.raises(FrozenInstanceError):
        item.density_m3 = 2.0e23
    assert item.species_hash == species().species_hash
    assert item.species_hash != species(density_m3=2.0e23).species_hash


def test_species_round_trip_is_exact():
    item = species(parameter_status=TrapParameterStatus.LITERATURE)
    assert TrapSpecies.from_dict(item.to_dict()) == item
    invalid = item.to_dict() | {"unexpected": True}
    with pytest.raises(ValueError, match="schema"):
        TrapSpecies.from_dict(invalid)


def test_disabled_empty_configuration_is_the_inert_default():
    spec = TrapAssistedTransportSpec()
    assert spec.enabled is False
    assert spec.species == ()
    assert spec.model is TrapAssistedModel.SEQUENTIAL_TWO_STEP_WKB


def test_enabled_configuration_requires_positive_density():
    with pytest.raises(ValueError, match="positive-density"):
        TrapAssistedTransportSpec(enabled=True)
    with pytest.raises(ValueError, match="positive-density"):
        TrapAssistedTransportSpec(enabled=True, species=(species(density_m3=0.0),))
    assert TrapAssistedTransportSpec(enabled=True, species=(species(),)).enabled


def test_species_collection_is_typed_ordered_and_unique():
    with pytest.raises(TypeError):
        TrapAssistedTransportSpec(species=[species()])
    with pytest.raises(TypeError):
        TrapAssistedTransportSpec(species=(object(),))
    with pytest.raises(ValueError, match="unique"):
        TrapAssistedTransportSpec(species=(species(), species()))


def test_canonical_json_round_trip_and_integrity():
    spec = TrapAssistedTransportSpec(enabled=True, species=(species(),))
    encoded = spec.to_json()
    assert '": "' not in encoded and '", "' not in encoded
    assert TrapAssistedTransportSpec.from_json(encoded) == spec
    assert json.loads(encoded)["configuration_hash"] == spec.configuration_hash
    damaged = encoded.replace('"density_m3":1e+23', '"density_m3":2e+23')
    with pytest.raises(ValueError, match="hash mismatch"):
        TrapAssistedTransportSpec.from_json(damaged)


def test_json_rejects_duplicate_keys_nonfinite_and_missing_hash():
    with pytest.raises(ValueError, match="duplicate"):
        TrapAssistedTransportSpec.from_json(
            '{"configuration_hash":"x","schema_version":1,"enabled":false,'
            '"enabled":false,"model":"sequential_two_step_wkb","species":[]}'
        )
    with pytest.raises(ValueError, match="non-finite"):
        TrapAssistedTransportSpec.from_json(
            '{"configuration_hash":"x","schema_version":1,"enabled":false,'
            '"model":"sequential_two_step_wkb","species":[NaN]}'
        )
    with pytest.raises(ValueError, match="required"):
        TrapAssistedTransportSpec.from_json(
            '{"schema_version":1,"enabled":false,'
            '"model":"sequential_two_step_wkb","species":[]}'
        )


def test_j1_does_not_integrate_or_execute_new_transport_physics():
    module = (ROOT / "ncmemsim/transport/traps.py").read_text(encoding="utf-8")
    assert "def evaluate" not in module
    assert "def rate" not in module
    engine = (ROOT / "ncmemsim/transport/engine.py").read_text(encoding="utf-8")
    assert "TrapAssisted" not in engine


def test_v1_baseline_remains_204_paths_while_j1_is_additive():
    proposal = json.loads(
        (ROOT / "docs/stable_api_proposal.json").read_text(encoding="utf-8")
    )
    paths = {entry["import_path"] for entry in proposal["entries"]}
    assert len(paths) == 204
    assert "ncmemsim.transport.TrapSpecies" not in paths
    assert "ncmemsim.transport.TransportEngine" in paths


def test_j1_documentation_records_model_basis_and_limitations():
    page = (ROOT / "docs/advanced_transport.md").read_text(encoding="utf-8")
    for token in (
        "J1 contract state",
        "sequential two-step WKB",
        "E_C - E_trap",
        "10.1109/TED.2003.813236",
        "10.1109/16.954471",
        "not the full multiphonon",
        "does not execute a rate",
    ):
        assert token in page
