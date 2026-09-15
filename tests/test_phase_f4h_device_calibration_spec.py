from __future__ import annotations

import numpy as np
import pytest

from ncmemsim.device_calibration import (
    DeviceCalibrationContext,
    DeviceCalibrationSpec,
    DeviceFitParameterBinding,
    DeviceFitTarget,
    apply_device_calibration_parameters,
)
from ncmemsim.fitting import FitParameter, FitParameterSet
from ncmemsim.physics import PhysicsModel
from ncmemsim.reference import make_v53_reference_device
from ncmemsim.simulator import SimulationConfig
from ncmemsim.tunneling import TunnelingEngine


def _parameter(name, initial, lower, upper, unit=None):
    return FitParameter(
        name=name,
        initial_value=initial,
        lower_bound=lower,
        upper_bound=upper,
        unit=unit,
    )


def _single_spec(parameter, target, fg_index=None):
    return DeviceCalibrationSpec(
        parameter_set=FitParameterSet((parameter,)),
        bindings=(
            DeviceFitParameterBinding(
                parameter.name,
                target,
                fg_index=fg_index,
            ),
        ),
    )


def _baseline():
    return (
        make_v53_reference_device(),
        PhysicsModel.default(),
        SimulationConfig(),
    )


def test_binding_normalizes_name_and_target():
    binding = DeviceFitParameterBinding(
        "  nu0  ",
        "kinetics.nu0_Hz",
    )
    assert binding.parameter_name == "nu0"
    assert binding.target == DeviceFitTarget.KINETICS_NU0_HZ


def test_binding_requires_fg_index_for_fg_target():
    with pytest.raises(TypeError, match="fg_index"):
        DeviceFitParameterBinding(
            "active",
            DeviceFitTarget.FG_ELECTRICALLY_ACTIVE_FRACTION,
        )


def test_binding_rejects_fg_index_for_global_target():
    with pytest.raises(ValueError, match="only valid"):
        DeviceFitParameterBinding(
            "nu0",
            DeviceFitTarget.KINETICS_NU0_HZ,
            fg_index=0,
        )


def test_binding_target_key_and_unit():
    binding = DeviceFitParameterBinding(
        "barrier",
        DeviceFitTarget.FG_PHI_BARRIER_PROG_EV,
        fg_index=1,
    )
    assert binding.target_key == "fg[1].phi_barrier_prog_eV"
    assert binding.canonical_unit == "eV"


def test_spec_requires_binding_order_to_match_parameters():
    parameter_set = FitParameterSet(
        (
            _parameter("a", 0.5, 0.1, 0.9),
            _parameter("b", 1.0e12, 1.0e10, 1.0e13),
        )
    )
    with pytest.raises(ValueError, match="names and order"):
        DeviceCalibrationSpec(
            parameter_set=parameter_set,
            bindings=(
                DeviceFitParameterBinding(
                    "b",
                    DeviceFitTarget.KINETICS_NU0_HZ,
                ),
                DeviceFitParameterBinding(
                    "a",
                    DeviceFitTarget.FG_ELECTRICALLY_ACTIVE_FRACTION,
                    fg_index=0,
                ),
            ),
        )


def test_spec_rejects_duplicate_target():
    parameter_set = FitParameterSet(
        (
            _parameter("a", 1.0e12, 1.0e10, 1.0e13),
            _parameter("b", 2.0e12, 1.0e10, 1.0e13),
        )
    )
    with pytest.raises(ValueError, match="only once"):
        DeviceCalibrationSpec(
            parameter_set=parameter_set,
            bindings=(
                DeviceFitParameterBinding(
                    "a",
                    DeviceFitTarget.KINETICS_NU0_HZ,
                ),
                DeviceFitParameterBinding(
                    "b",
                    DeviceFitTarget.KINETICS_NU0_HZ,
                ),
            ),
        )


def test_spec_rejects_qfix_qit_structural_degeneracy():
    parameter_set = FitParameterSet(
        (
            _parameter("qfix", 0.0, -1e-2, 1e-2),
            _parameter("qit", 0.0, -1e-2, 1e-2),
        )
    )
    with pytest.raises(ValueError, match="structurally non-identifiable"):
        DeviceCalibrationSpec(
            parameter_set=parameter_set,
            bindings=(
                DeviceFitParameterBinding(
                    "qfix",
                    DeviceFitTarget.SIMULATION_QFIX_C_M2,
                ),
                DeviceFitParameterBinding(
                    "qit",
                    DeviceFitTarget.SIMULATION_QIT_C_M2,
                ),
            ),
        )


def test_spec_rejects_active_volume_fraction_same_fg():
    parameter_set = FitParameterSet(
        (
            _parameter("active", 0.5, 0.1, 0.9),
            _parameter("volume", 0.4, 0.1, 0.9),
        )
    )
    with pytest.raises(ValueError, match="their product"):
        DeviceCalibrationSpec(
            parameter_set=parameter_set,
            bindings=(
                DeviceFitParameterBinding(
                    "active",
                    DeviceFitTarget.FG_ELECTRICALLY_ACTIVE_FRACTION,
                    fg_index=0,
                ),
                DeviceFitParameterBinding(
                    "volume",
                    DeviceFitTarget.FG_NC_VOLUME_FRACTION,
                    fg_index=0,
                ),
            ),
        )


def test_spec_warns_nu0_program_barrier():
    parameter_set = FitParameterSet(
        (
            _parameter("nu0", 1e12, 1e10, 1e13),
            _parameter("barrier", 2.5, 1.0, 4.0),
        )
    )
    spec = DeviceCalibrationSpec(
        parameter_set=parameter_set,
        bindings=(
            DeviceFitParameterBinding(
                "nu0",
                DeviceFitTarget.KINETICS_NU0_HZ,
            ),
            DeviceFitParameterBinding(
                "barrier",
                DeviceFitTarget.FG_PHI_BARRIER_PROG_EV,
                fg_index=0,
            ),
        ),
    )
    assert any("strongly correlated" in x for x in spec.identifiability_warnings)


def test_spec_warns_wkb_barrier_correlation():
    parameter_set = FitParameterSet(
        (
            _parameter("mass", 0.15, 0.05, 0.5),
            _parameter("barrier", 2.5, 1.0, 4.0),
        )
    )
    spec = DeviceCalibrationSpec(
        parameter_set=parameter_set,
        bindings=(
            DeviceFitParameterBinding(
                "mass",
                DeviceFitTarget.TUNNELING_OXIDE_EFFECTIVE_MASS_M0,
            ),
            DeviceFitParameterBinding(
                "barrier",
                DeviceFitTarget.FG_PHI_BARRIER_PROG_EV,
                fg_index=0,
            ),
        ),
    )
    assert any("WKB barrier" in x for x in spec.identifiability_warnings)


def test_spec_hash_is_deterministic():
    p = _parameter("nu0", 1e12, 1e10, 1e13)
    a = _single_spec(p, DeviceFitTarget.KINETICS_NU0_HZ)
    b = _single_spec(p, DeviceFitTarget.KINETICS_NU0_HZ)
    assert a.specification_hash() == b.specification_hash()


def test_apply_active_fraction_isolated_from_baseline():
    device, physics, config = _baseline()
    baseline = device.floating_gates()[0].electrically_active_fraction
    spec = _single_spec(
        _parameter("active", 0.5, 0.1, 0.9),
        DeviceFitTarget.FG_ELECTRICALLY_ACTIVE_FRACTION,
        fg_index=0,
    )
    context = apply_device_calibration_parameters(
        device, physics, config, spec, [0.7]
    )
    assert (
        context.device.floating_gates()[0].electrically_active_fraction
        == pytest.approx(0.7)
    )
    assert (
        device.floating_gates()[0].electrically_active_fraction
        == pytest.approx(baseline)
    )


def test_apply_volume_fraction():
    device, physics, config = _baseline()
    spec = _single_spec(
        _parameter("volume", 0.4, 0.1, 0.9),
        DeviceFitTarget.FG_NC_VOLUME_FRACTION,
        fg_index=0,
    )
    context = apply_device_calibration_parameters(
        device, physics, config, spec, [0.35]
    )
    assert context.device.floating_gates()[0].nc_volume_fraction == pytest.approx(0.35)


def test_apply_diameter():
    device, physics, config = _baseline()
    spec = _single_spec(
        _parameter("diameter", 5.0, 2.0, 10.0, "nm"),
        DeviceFitTarget.FG_NC_DIAMETER_NM,
        fg_index=0,
    )
    context = apply_device_calibration_parameters(
        device, physics, config, spec, [6.5]
    )
    assert context.device.floating_gates()[0].nc_diameter_nm == pytest.approx(6.5)


@pytest.mark.parametrize(
    ("target", "field_name", "value"),
    [
        (
            DeviceFitTarget.FG_PHI_BARRIER_PROG_EV,
            "phi_barrier_prog_eV",
            2.3,
        ),
        (
            DeviceFitTarget.FG_PHI_BARRIER_ERASE_EV,
            "phi_barrier_erase_eV",
            2.2,
        ),
    ],
)
def test_apply_barrier_updates_scalar_and_property(target, field_name, value):
    device, physics, config = _baseline()
    baseline_material = device.floating_gates()[0].nc_material
    spec = _single_spec(
        _parameter("barrier", 2.5, 1.0, 4.0, "eV"),
        target,
        fg_index=0,
    )
    context = apply_device_calibration_parameters(
        device, physics, config, spec, [value]
    )
    material = context.device.floating_gates()[0].nc_material
    assert getattr(material, field_name) == pytest.approx(value)
    if field_name in material.properties:
        assert material.properties[field_name].value == pytest.approx(value)
    assert device.floating_gates()[0].nc_material is baseline_material


@pytest.mark.parametrize(
    ("target", "field_name", "value"),
    [
        (DeviceFitTarget.KINETICS_NU0_HZ, "nu0_Hz", 2e12),
        (DeviceFitTarget.KINETICS_NU1_HZ, "nu1_Hz", 2e10),
        (DeviceFitTarget.KINETICS_NU2_HZ, "nu2_Hz", 5e9),
        (
            DeviceFitTarget.KINETICS_CAPACITANCE_EPS_R,
            "capacitance_eps_r",
            10.0,
        ),
    ],
)
def test_apply_kinetics_target(target, field_name, value):
    device, physics, config = _baseline()
    baseline = getattr(physics.occupancy.config, field_name)
    spec = _single_spec(
        _parameter("kinetic", value, value * 0.5, value * 1.5),
        target,
    )
    context = apply_device_calibration_parameters(
        device, physics, config, spec, [value]
    )
    assert getattr(context.physics.occupancy.config, field_name) == pytest.approx(value)
    assert getattr(physics.occupancy.config, field_name) == pytest.approx(baseline)


@pytest.mark.parametrize(
    ("target", "field_name", "value", "lower", "upper"),
    [
        (
            DeviceFitTarget.TUNNELING_INJECTION_ENERGY_EV,
            "injection_energy_eV",
            0.2,
            0.0,
            0.5,
        ),
        (
            DeviceFitTarget.TUNNELING_OXIDE_EFFECTIVE_MASS_M0,
            "oxide_effective_mass_m0",
            0.2,
            0.05,
            0.5,
        ),
        (
            DeviceFitTarget.TUNNELING_FIELD_COUPLING_FACTOR,
            "field_coupling_factor",
            0.9,
            0.1,
            1.5,
        ),
        (
            DeviceFitTarget.TUNNELING_ACTIVATION_BETA_V_INV,
            "activation_beta_V_inv",
            1.0,
            0.1,
            2.0,
        ),
    ],
)
def test_apply_tunneling_target_preserves_shared_engine(
    target, field_name, value, lower, upper
):
    device, physics, config = _baseline()
    spec = _single_spec(
        _parameter("tunnel", value, lower, upper),
        target,
    )
    context = apply_device_calibration_parameters(
        device, physics, config, spec, [value]
    )
    assert getattr(context.physics.tunneling.config, field_name) == pytest.approx(value)
    assert context.physics.occupancy.tunneling is context.physics.tunneling
    transport_tunneling = getattr(
        context.physics.transport,
        "tunneling",
        context.physics.tunneling,
    )
    assert transport_tunneling is context.physics.tunneling


@pytest.mark.parametrize(
    ("target", "field_name", "value"),
    [
        (DeviceFitTarget.SIMULATION_QFIX_C_M2, "qfix_C_m2", 1e-3),
        (DeviceFitTarget.SIMULATION_QIT_C_M2, "qit_C_m2", -2e-3),
    ],
)
def test_apply_simulation_charge(target, field_name, value):
    device, physics, config = _baseline()
    spec = _single_spec(
        _parameter("charge", 0.0, -1e-2, 1e-2, "C/m^2"),
        target,
    )
    context = apply_device_calibration_parameters(
        device, physics, config, spec, [value]
    )
    assert getattr(context.simulation_config, field_name) == pytest.approx(value)
    assert getattr(config, field_name) == pytest.approx(0.0)


def test_apply_rejects_out_of_range_fg_index():
    device, physics, config = _baseline()
    spec = _single_spec(
        _parameter("active", 0.5, 0.1, 0.9),
        DeviceFitTarget.FG_ELECTRICALLY_ACTIVE_FRACTION,
        fg_index=1,
    )
    with pytest.raises(ValueError, match="contains 1 floating gate"):
        apply_device_calibration_parameters(
            device, physics, config, spec, [0.5]
        )


def test_apply_rejects_fit_value_outside_bounds():
    device, physics, config = _baseline()
    spec = _single_spec(
        _parameter("active", 0.5, 0.1, 0.9),
        DeviceFitTarget.FG_ELECTRICALLY_ACTIVE_FRACTION,
        fg_index=0,
    )
    with pytest.raises(ValueError, match="parameter bounds"):
        apply_device_calibration_parameters(
            device, physics, config, spec, [0.95]
        )


@pytest.mark.parametrize(
    ("target", "value", "lower", "upper", "fg_index"),
    [
        (
            DeviceFitTarget.FG_ELECTRICALLY_ACTIVE_FRACTION,
            -0.1,
            -1.0,
            1.0,
            0,
        ),
        (
            DeviceFitTarget.FG_NC_DIAMETER_NM,
            0.0,
            -1.0,
            10.0,
            0,
        ),
        (
            DeviceFitTarget.KINETICS_NU0_HZ,
            0.0,
            -1.0,
            1.0,
            None,
        ),
        (
            DeviceFitTarget.TUNNELING_OXIDE_EFFECTIVE_MASS_M0,
            0.0,
            -1.0,
            1.0,
            None,
        ),
        (
            DeviceFitTarget.TUNNELING_INJECTION_ENERGY_EV,
            -0.1,
            -1.0,
            1.0,
            None,
        ),
    ],
)
def test_apply_rejects_physically_invalid_bounded_value(
    target, value, lower, upper, fg_index
):
    device, physics, config = _baseline()
    spec = _single_spec(
        _parameter("bad", 0.5, lower, upper),
        target,
        fg_index=fg_index,
    )
    with pytest.raises(ValueError):
        apply_device_calibration_parameters(
            device, physics, config, spec, [value]
        )


def test_apply_rejects_broken_tunneling_sharing():
    device, physics, config = _baseline()
    physics.occupancy.tunneling = TunnelingEngine()
    spec = _single_spec(
        _parameter("nu0", 1e12, 1e10, 1e13),
        DeviceFitTarget.KINETICS_NU0_HZ,
    )
    with pytest.raises(ValueError, match="share the same TunnelingEngine"):
        apply_device_calibration_parameters(
            device, physics, config, spec, [1e12]
        )


def test_two_applications_are_independent():
    device, physics, config = _baseline()
    spec = _single_spec(
        _parameter("active", 0.5, 0.1, 0.9),
        DeviceFitTarget.FG_ELECTRICALLY_ACTIVE_FRACTION,
        fg_index=0,
    )
    first = apply_device_calibration_parameters(
        device, physics, config, spec, [0.3]
    )
    second = apply_device_calibration_parameters(
        device, physics, config, spec, [0.8]
    )
    assert first.device.floating_gates()[0].electrically_active_fraction == pytest.approx(0.3)
    assert second.device.floating_gates()[0].electrically_active_fraction == pytest.approx(0.8)


def test_context_manifest_and_hash_are_deterministic():
    device, physics, config = _baseline()
    spec = _single_spec(
        _parameter("nu0", 1e12, 1e10, 1e13, "Hz"),
        DeviceFitTarget.KINETICS_NU0_HZ,
    )
    first = apply_device_calibration_parameters(
        device, physics, config, spec, np.asarray([2e12])
    )
    second = apply_device_calibration_parameters(
        device, physics, config, spec, [2e12]
    )
    assert isinstance(first, DeviceCalibrationContext)
    assert first.parameter_application_manifest()["parameter_values"] == {
        "nu0": 2e12
    }
    assert first.parameter_application_hash() == second.parameter_application_hash()


def test_structural_qfix_qit_rule_matches_current_electrostatics():
    device, physics, _ = _baseline()
    electrostatics = physics.electrostatics
    q = 1e-3
    a = electrostatics.flatband_zero(
        device,
        qfix_C_m2=q,
        qit_C_m2=0.0,
    )
    b = electrostatics.flatband_zero(
        device,
        qfix_C_m2=0.0,
        qit_C_m2=q,
    )
    assert a == pytest.approx(b)
