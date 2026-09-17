from __future__ import annotations

from dataclasses import replace

import pytest

from ncmemsim import DeviceBuilder
from ncmemsim.dtco import (
    BindingScope,
    DesignVariable,
    DesignVariableRole,
    ExperimentSpec,
    OperatingBindingError,
    ParameterBinding,
    apply_experiment_point,
    apply_operating_binding,
)
from ncmemsim.electro_optical_program_protocol import (
    ElectroOpticalProgramPulseReadProtocol,
)
from ncmemsim.hashing import canonical_hash
from ncmemsim.optics import LightSource
from ncmemsim.photo import PhotoTransitionWeights
from ncmemsim.program_protocol import ProgramPulseReadProtocol


def _device():
    return DeviceBuilder.v2(n_fgs=1, name="g1c2b-base")


def _electrical():
    return ProgramPulseReadProtocol(
        program_voltage_V=5.0,
        programming_time_s=1.0e-3,
        read_voltage_V=0.0,
    )


def _electro_optical():
    return ElectroOpticalProgramPulseReadProtocol(
        electrical_protocol=_electrical(),
        light_source=LightSource.led(
            wavelength_nm=1300.0,
            power_density_W_m2=100.0,
        ),
        photo_weights=PhotoTransitionWeights(),
    )


def _temperature_variable():
    return DesignVariable(
        name="temperature",
        binding=ParameterBinding(
            BindingScope.DEVICE,
            ("temperature_K",),
        ),
        values=(300.0, 325.0),
        role=DesignVariableRole.MODEL,
        unit="K",
    )


def _program_voltage_variable():
    return DesignVariable(
        name="program_voltage",
        binding=ParameterBinding(
            BindingScope.OPERATING,
            ("program", "voltage_V"),
        ),
        values=(5.0, 6.0),
        role=DesignVariableRole.ELECTRICAL,
        unit="V",
    )


def test_device_only_serialization_remains_backward_compatible():
    spec = ExperimentSpec.from_device(
        name="device-only",
        device=_device(),
        variables=(_temperature_variable(),),
    )
    payload = spec.to_dict()
    assert "base_operating_hash" not in payload
    assert "base_operating_kind" not in payload
    assert spec.base_operating_hash is None
    assert spec.base_operating_kind is None


def test_operating_variable_requires_operating_baseline():
    with pytest.raises(ValueError, match="operating baseline identity"):
        ExperimentSpec.from_device(
            name="invalid-operating-study",
            device=_device(),
            variables=(_program_voltage_variable(),),
        )


def test_program_protocol_identity_is_recorded():
    protocol = _electrical()
    spec = ExperimentSpec.from_device(
        name="program-identity",
        device=_device(),
        variables=(_program_voltage_variable(),),
        operating_protocol=protocol,
    )
    expected = canonical_hash(
        {
            "kind": "program_pulse_read",
            "protocol": protocol.to_dict(),
        }
    )
    assert spec.base_operating_kind == "program_pulse_read"
    assert spec.base_operating_hash == expected
    assert spec.matches_operating(protocol)


def test_program_protocol_change_is_detected():
    protocol = _electrical()
    spec = ExperimentSpec.from_device(
        name="program-integrity",
        device=_device(),
        variables=(_program_voltage_variable(),),
        operating_protocol=protocol,
    )
    changed = apply_operating_binding(
        protocol,
        ParameterBinding(
            BindingScope.OPERATING,
            ("program", "voltage_V"),
        ),
        6.0,
    )
    assert not spec.matches_operating(changed)
    with pytest.raises(ValueError, match="base_operating_hash"):
        spec.require_matching_operating(changed)


def test_electro_optical_identity_is_recorded():
    protocol = _electro_optical()
    spec = ExperimentSpec.from_device(
        name="eo-identity",
        device=_device(),
        variables=(_temperature_variable(),),
        operating_protocol=protocol,
    )
    assert (
        spec.base_operating_kind
        == "electro_optical_program_pulse_read"
    )
    assert spec.matches_operating(protocol)


def test_optical_wavelength_change_is_detected():
    protocol = _electro_optical()
    wavelength = DesignVariable(
        name="wavelength",
        binding=ParameterBinding(
            BindingScope.OPERATING,
            ("optical", "wavelength_nm"),
        ),
        values=(1300.0, 1550.0),
        role=DesignVariableRole.OPTICAL,
        unit="nm",
    )
    spec = ExperimentSpec.from_device(
        name="wavelength-integrity",
        device=_device(),
        variables=(wavelength,),
        operating_protocol=protocol,
    )
    changed = apply_operating_binding(
        protocol,
        wavelength.binding,
        1550.0,
    )
    assert not spec.matches_operating(changed)


def test_fixed_operating_baseline_is_allowed_for_device_only_study():
    protocol = _electrical()
    spec = ExperimentSpec.from_device(
        name="fixed-operating",
        device=_device(),
        variables=(_temperature_variable(),),
        operating_protocol=protocol,
    )
    assert spec.base_operating_hash is not None
    assert spec.matches_operating(protocol)


def test_mixed_experiment_point_applies_both_scopes_and_preserves_bases():
    device = _device()
    protocol = _electrical()
    spec = ExperimentSpec.from_device(
        name="mixed",
        device=device,
        variables=(
            _temperature_variable(),
            _program_voltage_variable(),
        ),
        operating_protocol=protocol,
    )

    point = apply_experiment_point(
        spec,
        device,
        protocol,
        {
            "temperature": 325.0,
            "program_voltage": 6.0,
        },
    )

    assert point.device.temperature_K == 325.0
    assert point.operating_protocol.program_voltage_V == 6.0
    assert device.temperature_K == 300.0
    assert protocol.program_voltage_V == 5.0
    assert point.values_by_name == (
        ("temperature", 325.0),
        ("program_voltage", 6.0),
    )


def test_mixed_point_rejects_missing_assignment():
    device = _device()
    protocol = _electrical()
    spec = ExperimentSpec.from_device(
        name="missing",
        device=device,
        variables=(
            _temperature_variable(),
            _program_voltage_variable(),
        ),
        operating_protocol=protocol,
    )
    with pytest.raises(OperatingBindingError, match="missing"):
        apply_experiment_point(
            spec,
            device,
            protocol,
            {"temperature": 325.0},
        )


def test_mixed_point_rejects_extra_assignment():
    device = _device()
    protocol = _electrical()
    spec = ExperimentSpec.from_device(
        name="extra",
        device=device,
        variables=(_program_voltage_variable(),),
        operating_protocol=protocol,
    )
    with pytest.raises(OperatingBindingError, match="extra"):
        apply_experiment_point(
            spec,
            device,
            protocol,
            {
                "program_voltage": 6.0,
                "unexpected": 1.0,
            },
        )


def test_mixed_point_rejects_value_outside_domain():
    device = _device()
    protocol = _electrical()
    spec = ExperimentSpec.from_device(
        name="domain",
        device=device,
        variables=(_program_voltage_variable(),),
        operating_protocol=protocol,
    )
    with pytest.raises(
        OperatingBindingError,
        match="outside declared domain",
    ):
        apply_experiment_point(
            spec,
            device,
            protocol,
            {"program_voltage": 7.0},
        )


def test_model_scope_is_not_silently_applied():
    device = _device()
    protocol = _electrical()
    model_variable = DesignVariable(
        name="eta",
        binding=ParameterBinding(
            BindingScope.MODEL,
            ("photo", "capture_efficiency"),
        ),
        values=(1.0e-7, 2.0e-7),
        role=DesignVariableRole.MODEL,
        unit="1",
    )
    spec = ExperimentSpec.from_device(
        name="model-scope",
        device=device,
        variables=(model_variable,),
        operating_protocol=protocol,
    )
    with pytest.raises(OperatingBindingError, match="MODEL"):
        apply_experiment_point(
            spec,
            device,
            protocol,
            {"eta": 2.0e-7},
        )


def test_changed_device_baseline_is_rejected_before_application():
    device = _device()
    protocol = _electrical()
    spec = ExperimentSpec.from_device(
        name="device-baseline",
        device=device,
        variables=(_program_voltage_variable(),),
        operating_protocol=protocol,
    )
    changed_device = replace(
        device,
        temperature_K=device.temperature_K + 10.0,
    )
    with pytest.raises(ValueError, match="base_device_hash"):
        apply_experiment_point(
            spec,
            changed_device,
            protocol,
            {"program_voltage": 6.0},
        )


def test_changed_operating_baseline_is_rejected_before_application():
    device = _device()
    protocol = _electrical()
    spec = ExperimentSpec.from_device(
        name="operating-baseline",
        device=device,
        variables=(_program_voltage_variable(),),
        operating_protocol=protocol,
    )
    changed = replace(protocol, program_voltage_V=6.0)
    with pytest.raises(ValueError, match="base_operating_hash"):
        apply_experiment_point(
            spec,
            device,
            changed,
            {"program_voltage": 6.0},
        )
