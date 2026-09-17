from __future__ import annotations

import json
import math

import pytest

from ncmemsim import DeviceBuilder
from ncmemsim.dtco import (
    BindingScope,
    DesignVariable,
    DesignVariableRole,
    ExperimentSpec,
    ParameterBinding,
)
from ncmemsim.hashing import canonical_hash
from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)


def _diameter_variable(values=(4.0, 5.0, 6.0)) -> DesignVariable:
    return DesignVariable(
        name="fg1_nc_diameter",
        binding=ParameterBinding(
            scope=BindingScope.DEVICE,
            path=("layers", "FG1", "nc_diameter_nm"),
        ),
        values=values,
        role=DesignVariableRole.GEOMETRY,
        unit="nm",
    )


def _active_fraction_variable(values=(0.15, 0.22, 0.30)) -> DesignVariable:
    return DesignVariable(
        name="fg1_active_fraction",
        binding=ParameterBinding(
            scope=BindingScope.DEVICE,
            path=("layers", "FG1", "electrically_active_fraction"),
        ),
        values=values,
        role=DesignVariableRole.MODEL,
        unit="1",
    )


def test_parameter_binding_serialization_and_hash_are_deterministic():
    binding = ParameterBinding(
        scope=BindingScope.DEVICE,
        path=("layers", "FG1", "nc_diameter_nm"),
    )
    assert binding.to_dict() == {
        "scope": "device",
        "path": ["layers", "FG1", "nc_diameter_nm"],
    }
    assert binding.binding_id == canonical_hash(binding.to_dict())


@pytest.mark.parametrize("path", [(), ("",), (" FG1",), ("FG1 ",)])
def test_parameter_binding_rejects_invalid_paths(path):
    with pytest.raises(ValueError):
        ParameterBinding(scope=BindingScope.DEVICE, path=path)


def test_design_variable_preserves_declared_domain_order():
    variable = _diameter_variable((6.0, 4.0, 5.0))
    assert variable.values == (6.0, 4.0, 5.0)
    assert variable.is_numeric


@pytest.mark.parametrize("values", [(1.0, 1.0), (1, 1.0)])
def test_numeric_design_variable_rejects_duplicate_values(values):
    with pytest.raises(ValueError):
        _diameter_variable(values)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_numeric_design_variable_rejects_nonfinite_values(bad):
    with pytest.raises(ValueError):
        _diameter_variable((4.0, bad))


def test_numeric_design_variable_requires_explicit_unit():
    with pytest.raises(ValueError):
        DesignVariable(
            name="diameter",
            binding=ParameterBinding(
                BindingScope.DEVICE,
                ("layers", "FG1", "nc_diameter_nm"),
            ),
            values=(4.0, 5.0),
            role=DesignVariableRole.GEOMETRY,
            unit=None,
        )


def test_dimensionless_numeric_variable_uses_unit_one():
    assert _active_fraction_variable().unit == "1"


def test_categorical_variable_is_supported_without_unit():
    variable = DesignVariable(
        name="program_mode",
        binding=ParameterBinding(BindingScope.OPERATING, ("program", "mode")),
        values=("electrical", "electro_optical"),
        role=DesignVariableRole.ELECTRICAL,
        unit=None,
    )
    assert not variable.is_numeric
    assert variable.to_dict()["values"] == ["electrical", "electro_optical"]


def test_categorical_variable_rejects_unit():
    with pytest.raises(ValueError):
        DesignVariable(
            name="mode",
            binding=ParameterBinding(BindingScope.OPERATING, ("program", "mode")),
            values=("a", "b"),
            role=DesignVariableRole.MODEL,
            unit="1",
        )


def test_design_variable_rejects_mixed_numeric_and_categorical_domain():
    with pytest.raises(TypeError):
        DesignVariable(
            name="mixed",
            binding=ParameterBinding(BindingScope.MODEL, ("x",)),
            values=(1.0, "two"),
            role=DesignVariableRole.MODEL,
            unit="1",
        )


def test_design_variable_serializes_parameter_provenance():
    provenance = ParameterProvenance(
        source="synthetic design study",
        status=ParameterStatus.ASSUMED,
        notes="G1 specification test",
        parameter_set="phase-g1-test",
    )
    variable = DesignVariable(
        name="active_fraction",
        binding=ParameterBinding(
            BindingScope.DEVICE,
            ("layers", "FG1", "electrically_active_fraction"),
        ),
        values=(0.15, 0.22),
        role=DesignVariableRole.MODEL,
        unit="1",
        provenance=provenance,
    )
    assert variable.to_dict()["provenance"]["status"] == "assumed"


def test_experiment_spec_from_device_records_exact_device_hash():
    device = DeviceBuilder.v2(n_fgs=1, name="g1_base")
    spec = ExperimentSpec.from_device(
        name="diameter-study",
        device=device,
        variables=(_diameter_variable(),),
    )
    assert spec.base_device_hash == canonical_hash(device.to_dict())
    assert spec.base_device_name == "g1_base"
    assert spec.matches_device(device)


def test_experiment_spec_hash_is_deterministic():
    device = DeviceBuilder.v2(n_fgs=1, name="g1_base")
    kwargs = dict(
        name="two-variable-study",
        device=device,
        variables=(_diameter_variable(), _active_fraction_variable()),
        description="Deterministic G1 test.",
    )
    a = ExperimentSpec.from_device(**kwargs)
    b = ExperimentSpec.from_device(**kwargs)
    assert a.experiment_hash == b.experiment_hash
    assert a.to_dict() == b.to_dict()


def test_experiment_spec_design_point_count_is_cartesian_product_size():
    device = DeviceBuilder.v2(n_fgs=1)
    spec = ExperimentSpec.from_device(
        name="count-test",
        device=device,
        variables=(
            _diameter_variable((4.0, 5.0, 6.0)),
            _active_fraction_variable((0.15, 0.22)),
        ),
    )
    assert spec.design_point_count == 6


def test_experiment_spec_rejects_duplicate_variable_names():
    device = DeviceBuilder.v2(n_fgs=1)
    a = _diameter_variable()
    b = DesignVariable(
        name=a.name,
        binding=ParameterBinding(
            BindingScope.DEVICE,
            ("layers", "FG1", "thickness_nm"),
        ),
        values=(10.0, 12.0),
        role=DesignVariableRole.GEOMETRY,
        unit="nm",
    )
    with pytest.raises(ValueError, match="names must be unique"):
        ExperimentSpec.from_device(
            name="duplicate-name",
            device=device,
            variables=(a, b),
        )


def test_experiment_spec_rejects_duplicate_bindings():
    device = DeviceBuilder.v2(n_fgs=1)
    a = _diameter_variable()
    b = DesignVariable(
        name="same_target_different_name",
        binding=a.binding,
        values=(4.5, 5.5),
        role=DesignVariableRole.GEOMETRY,
        unit="nm",
    )
    with pytest.raises(ValueError, match="unique binding"):
        ExperimentSpec.from_device(
            name="duplicate-binding",
            device=device,
            variables=(a, b),
        )


def test_experiment_spec_detects_base_device_change():
    device = DeviceBuilder.v2(n_fgs=1, nc_diameter_nm=5.0)
    spec = ExperimentSpec.from_device(
        name="base-integrity",
        device=device,
        variables=(_diameter_variable(),),
    )
    device.floating_gates()[0].nc_diameter_nm = 6.0
    assert not spec.matches_device(device)
    with pytest.raises(ValueError, match="base_device_hash"):
        spec.require_matching_device(device)


def test_experiment_hash_changes_when_domain_changes():
    device = DeviceBuilder.v2(n_fgs=1)
    a = ExperimentSpec.from_device(
        name="hash-change",
        device=device,
        variables=(_diameter_variable((4.0, 5.0)),),
    )
    b = ExperimentSpec.from_device(
        name="hash-change",
        device=device,
        variables=(_diameter_variable((4.0, 5.0, 6.0)),),
    )
    assert a.experiment_hash != b.experiment_hash


def test_experiment_variable_order_is_part_of_experiment_identity():
    device = DeviceBuilder.v2(n_fgs=1)
    diameter = _diameter_variable()
    active = _active_fraction_variable()
    a = ExperimentSpec.from_device(
        name="axis-order",
        device=device,
        variables=(diameter, active),
    )
    b = ExperimentSpec.from_device(
        name="axis-order",
        device=device,
        variables=(active, diameter),
    )
    assert a.experiment_hash != b.experiment_hash


def test_experiment_spec_is_json_serializable():
    device = DeviceBuilder.v2(n_fgs=1)
    spec = ExperimentSpec.from_device(
        name="json-test",
        device=device,
        variables=(_diameter_variable(),),
    )
    encoded = json.dumps(spec.to_dict(), sort_keys=True)
    assert '"schema_version": "dtco-experiment-v1"' in encoded
