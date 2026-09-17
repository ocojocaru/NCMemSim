from __future__ import annotations

import pytest

from ncmemsim import DeviceBuilder
from ncmemsim.dtco import (
    BindingApplicationError,
    BindingScope,
    DesignVariable,
    DesignVariableRole,
    ExperimentSpec,
    ParameterBinding,
    apply_device_binding,
    apply_device_bindings,
    apply_experiment_design_point,
)
from ncmemsim.hashing import canonical_hash
from ncmemsim.materials import make_gesn


def _device():
    return DeviceBuilder.v2(
        n_fgs=1,
        control_sio2_nm=20.0,
        fg_thickness_nm=12.0,
        tunnel_sio2_nm=8.0,
        nc_diameter_nm=5.0,
        nc_volume_fraction=0.60,
        active_fraction=0.22,
        name="g1b-base",
    )


def _binding(*path: str) -> ParameterBinding:
    return ParameterBinding(BindingScope.DEVICE, path)


def _diameter_variable() -> DesignVariable:
    return DesignVariable(
        name="diameter",
        binding=_binding("layers", "FG1", "nc_diameter_nm"),
        values=(4.0, 5.0, 6.0),
        role=DesignVariableRole.GEOMETRY,
        unit="nm",
    )


def _active_variable() -> DesignVariable:
    return DesignVariable(
        name="active_fraction",
        binding=_binding("layers", "FG1", "electrically_active_fraction"),
        values=(0.15, 0.22, 0.30),
        role=DesignVariableRole.MODEL,
        unit="1",
    )


def test_apply_device_binding_returns_new_device_and_preserves_base():
    base = _device()
    base_hash = canonical_hash(base.to_dict())
    candidate = apply_device_binding(
        base,
        _binding("layers", "FG1", "nc_diameter_nm"),
        6.0,
    )
    assert candidate is not base
    assert candidate.floating_gates()[0].nc_diameter_nm == 6.0
    assert base.floating_gates()[0].nc_diameter_nm == 5.0
    assert canonical_hash(base.to_dict()) == base_hash


def test_apply_regular_layer_thickness_by_semantic_layer_name():
    base = _device()
    candidate = apply_device_binding(
        base,
        _binding("layers", "tunnel_sio2", "thickness_nm"),
        9.5,
    )
    assert candidate.get_layer("tunnel_sio2").thickness_nm == 9.5
    assert base.get_layer("tunnel_sio2").thickness_nm == 8.0


def test_apply_top_level_device_temperature():
    base = _device()
    candidate = apply_device_binding(base, _binding("temperature_K"), 325)
    assert candidate.temperature_K == 325.0
    assert base.temperature_K == 300.0


def test_apply_multiple_bindings_is_atomic_and_uses_one_candidate():
    base = _device()
    candidate = apply_device_bindings(
        base,
        (
            (_binding("layers", "FG1", "nc_diameter_nm"), 6.0),
            (_binding("layers", "FG1", "electrically_active_fraction"), 0.30),
            (_binding("temperature_K"), 325.0),
        ),
    )
    assert candidate.floating_gates()[0].nc_diameter_nm == 6.0
    assert candidate.floating_gates()[0].electrically_active_fraction == 0.30
    assert candidate.temperature_K == 325.0
    assert base.floating_gates()[0].nc_diameter_nm == 5.0
    assert base.temperature_K == 300.0


def test_apply_device_bindings_rejects_duplicate_binding():
    base = _device()
    binding = _binding("temperature_K")
    with pytest.raises(BindingApplicationError, match="duplicate"):
        apply_device_bindings(base, ((binding, 310.0), (binding, 320.0)))


def test_non_device_scope_is_rejected():
    base = _device()
    binding = ParameterBinding(
        BindingScope.OPERATING,
        ("program", "voltage_V"),
    )
    with pytest.raises(BindingApplicationError, match="only BindingScope.DEVICE"):
        apply_device_binding(base, binding, 4.0)


def test_unknown_top_level_device_path_is_rejected():
    with pytest.raises(BindingApplicationError, match="unsupported device"):
        apply_device_binding(_device(), _binding("architecture"), "V1")


def test_unknown_layer_name_is_rejected():
    with pytest.raises(BindingApplicationError, match="unknown layer"):
        apply_device_binding(
            _device(),
            _binding("layers", "missing", "thickness_nm"),
            10.0,
        )


def test_unsupported_regular_layer_attribute_is_rejected():
    with pytest.raises(BindingApplicationError, match="unsupported attribute"):
        apply_device_binding(
            _device(),
            _binding("layers", "tunnel_sio2", "role"),
            "control_dielectric",
        )


def test_nested_material_mutation_is_rejected():
    with pytest.raises(BindingApplicationError, match="unsupported device"):
        apply_device_binding(
            _device(),
            _binding("layers", "FG1", "nc_material", "bandgap_eV"),
            0.08,
        )


def test_post_application_validation_rejects_nonpositive_thickness():
    base = _device()
    base_hash = canonical_hash(base.to_dict())
    with pytest.raises(BindingApplicationError, match="validation failed"):
        apply_device_binding(
            base,
            _binding("layers", "tunnel_sio2", "thickness_nm"),
            0.0,
        )
    assert canonical_hash(base.to_dict()) == base_hash


def test_post_application_validation_rejects_invalid_volume_fraction():
    base = _device()
    with pytest.raises(BindingApplicationError, match="validation failed"):
        apply_device_binding(
            base,
            _binding("layers", "FG1", "nc_volume_fraction"),
            1.2,
        )
    assert base.floating_gates()[0].nc_volume_fraction == 0.60


def test_integer_target_rejects_float_even_when_numerically_integral():
    with pytest.raises(BindingApplicationError, match="integer value"):
        apply_device_binding(
            _device(),
            _binding("layers", "FG1", "grid_points"),
            41.0,
        )


def test_integer_target_accepts_integer():
    candidate = apply_device_binding(
        _device(),
        _binding("layers", "FG1", "grid_points"),
        41,
    )
    assert candidate.floating_gates()[0].grid_points == 41


def test_spatial_profile_binding_is_rejected_until_semantics_are_supported():
    with pytest.raises(BindingApplicationError, match="unsupported attribute"):
        apply_device_binding(
            _device(),
            _binding("layers", "FG1", "spatial_profile"),
            "uniform",
        )


def test_experiment_design_point_applies_all_declared_variables():
    base = _device()
    spec = ExperimentSpec.from_device(
        name="two-axis",
        device=base,
        variables=(_diameter_variable(), _active_variable()),
    )
    candidate = apply_experiment_design_point(
        spec,
        base,
        {"diameter": 6.0, "active_fraction": 0.30},
    )
    fg = candidate.floating_gates()[0]
    assert fg.nc_diameter_nm == 6.0
    assert fg.electrically_active_fraction == 0.30
    assert base.floating_gates()[0].nc_diameter_nm == 5.0


def test_experiment_design_point_rejects_missing_assignment():
    base = _device()
    spec = ExperimentSpec.from_device(
        name="two-axis",
        device=base,
        variables=(_diameter_variable(), _active_variable()),
    )
    with pytest.raises(BindingApplicationError, match="missing"):
        apply_experiment_design_point(spec, base, {"diameter": 6.0})


def test_experiment_design_point_rejects_extra_assignment():
    base = _device()
    spec = ExperimentSpec.from_device(
        name="one-axis",
        device=base,
        variables=(_diameter_variable(),),
    )
    with pytest.raises(BindingApplicationError, match="extra"):
        apply_experiment_design_point(
            spec,
            base,
            {"diameter": 6.0, "unknown": 1.0},
        )


def test_experiment_design_point_rejects_value_outside_declared_domain():
    base = _device()
    spec = ExperimentSpec.from_device(
        name="one-axis",
        device=base,
        variables=(_diameter_variable(),),
    )
    with pytest.raises(BindingApplicationError, match="outside declared domain"):
        apply_experiment_design_point(spec, base, {"diameter": 7.0})


def test_experiment_design_point_rejects_changed_base_device():
    base = _device()
    spec = ExperimentSpec.from_device(
        name="base-check",
        device=base,
        variables=(_diameter_variable(),),
    )
    base.floating_gates()[0].nc_diameter_nm = 5.5
    with pytest.raises(ValueError, match="base_device_hash"):
        apply_experiment_design_point(spec, base, {"diameter": 6.0})


def test_experiment_design_point_rejects_non_device_variable_scope():
    base = _device()
    operating = DesignVariable(
        name="program_voltage",
        binding=ParameterBinding(
            BindingScope.OPERATING,
            ("program", "voltage_V"),
        ),
        values=(3.0, 4.0),
        role=DesignVariableRole.ELECTRICAL,
        unit="V",
    )
    spec = ExperimentSpec.from_device(
        name="operating-scope",
        device=base,
        variables=(operating,),
    )
    with pytest.raises(BindingApplicationError, match="device-scope"):
        apply_experiment_design_point(
            spec,
            base,
            {"program_voltage": 4.0},
        )


def test_gesn_composition_binding_rebuilds_material_and_preserves_base():
    base = DeviceBuilder.v2(
        n_fgs=1,
        nc_material=make_gesn(0.08),
        name="gesn-base",
    )
    base_hash = canonical_hash(base.to_dict())
    original = base.floating_gates()[0].nc_material

    candidate = apply_device_binding(
        base,
        _binding("layers", "FG1", "nc_material", "sn_fraction"),
        0.12,
    )

    updated = candidate.floating_gates()[0].nc_material
    assert updated.sn_fraction == pytest.approx(0.12)
    assert updated.name == "GeSn_12.0atpctSn"
    assert updated.bandgap_eV != pytest.approx(original.bandgap_eV)
    assert updated.phi_barrier_prog_eV != pytest.approx(
        original.phi_barrier_prog_eV
    )
    assert base.floating_gates()[0].nc_material.sn_fraction == pytest.approx(0.08)
    assert canonical_hash(base.to_dict()) == base_hash


@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_gesn_composition_binding_rejects_fraction_outside_unit_interval(value):
    base = DeviceBuilder.v2(n_fgs=1, nc_material=make_gesn(0.08))
    with pytest.raises(BindingApplicationError, match=r"\[0, 1\]"):
        apply_device_binding(
            base,
            _binding("layers", "FG1", "nc_material", "sn_fraction"),
            value,
        )


def test_gesn_composition_binding_rejects_non_gesn_material():
    with pytest.raises(BindingApplicationError, match="requires a GeSnModel"):
        apply_device_binding(
            _device(),
            _binding("layers", "FG1", "nc_material", "sn_fraction"),
            0.08,
        )


def test_gesn_composition_binding_rejects_custom_parameterization():
    custom = make_gesn(0.08, phi_ge_prog_eV=3.1)
    base = DeviceBuilder.v2(n_fgs=1, nc_material=custom)
    with pytest.raises(BindingApplicationError, match="canonical default GeSn"):
        apply_device_binding(
            base,
            _binding("layers", "FG1", "nc_material", "sn_fraction"),
            0.12,
        )


@pytest.mark.parametrize("value", [True, "0.12"])
def test_gesn_composition_binding_rejects_non_numeric_values(value):
    base = DeviceBuilder.v2(n_fgs=1, nc_material=make_gesn(0.08))
    with pytest.raises(BindingApplicationError, match="numeric value"):
        apply_device_binding(
            base,
            _binding("layers", "FG1", "nc_material", "sn_fraction"),
            value,
        )


def test_experiment_design_point_applies_gesn_composition_variable():
    base = DeviceBuilder.v2(
        n_fgs=1,
        nc_material=make_gesn(0.08),
        name="gesn-experiment-base",
    )
    composition = DesignVariable(
        name="sn_fraction",
        binding=_binding("layers", "FG1", "nc_material", "sn_fraction"),
        values=(0.06, 0.08, 0.10),
        role=DesignVariableRole.MATERIAL,
        unit="1",
    )
    spec = ExperimentSpec.from_device(
        name="composition-study",
        device=base,
        variables=(composition,),
    )

    candidate = apply_experiment_design_point(
        spec,
        base,
        {"sn_fraction": 0.10},
    )

    assert candidate.floating_gates()[0].nc_material.sn_fraction == pytest.approx(0.10)
    assert base.floating_gates()[0].nc_material.sn_fraction == pytest.approx(0.08)
