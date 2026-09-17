from __future__ import annotations

import pytest

from ncmemsim.dtco import (
    BindingScope,
    OperatingBindingError,
    ParameterBinding,
    apply_operating_binding,
    apply_operating_bindings,
)
from ncmemsim.electro_optical_program_protocol import (
    ElectroOpticalProgramPulseReadProtocol,
)
from ncmemsim.optics import LightSource
from ncmemsim.photo import PhotoTransitionWeights
from ncmemsim.program_protocol import ProgramPulseReadProtocol


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


def _op(*path: str) -> ParameterBinding:
    return ParameterBinding(BindingScope.OPERATING, path)


def test_program_voltage_binding_rebuilds_and_preserves_base():
    base = _electrical()
    candidate = apply_operating_binding(
        base,
        _op("program", "voltage_V"),
        6.0,
    )
    assert candidate is not base
    assert candidate.program_voltage_V == 6.0
    assert base.program_voltage_V == 5.0


def test_program_time_binding_uses_existing_protocol_validation():
    with pytest.raises(OperatingBindingError, match="validation failed"):
        apply_operating_binding(
            _electrical(),
            _op("program", "time_s"),
            -1.0,
        )


def test_read_voltage_binding():
    candidate = apply_operating_binding(
        _electrical(),
        _op("read", "voltage_V"),
        0.5,
    )
    assert candidate.read_voltage_V == 0.5


def test_internal_dt_binding_can_replace_none():
    candidate = apply_operating_binding(
        _electrical(),
        _op("program", "internal_dt_s"),
        1.0e-5,
    )
    assert candidate.program_internal_dt_s == pytest.approx(1.0e-5)


def test_nested_electrical_binding_in_electro_optical_protocol():
    base = _electro_optical()
    candidate = apply_operating_binding(
        base,
        _op("program", "voltage_V"),
        6.5,
    )
    assert candidate.electrical_protocol.program_voltage_V == 6.5
    assert base.electrical_protocol.program_voltage_V == 5.0


def test_optical_wavelength_binding_rebuilds_light_source():
    base = _electro_optical()
    candidate = apply_operating_binding(
        base,
        _op("optical", "wavelength_nm"),
        1550.0,
    )
    assert candidate.light_source.wavelength_nm == 1550.0
    assert base.light_source.wavelength_nm == 1300.0


def test_optical_power_binding_rebuilds_light_source():
    base = _electro_optical()
    candidate = apply_operating_binding(
        base,
        _op("optical", "power_density_W_m2"),
        250.0,
    )
    assert candidate.light_source.power_density_W_m2 == 250.0
    assert base.light_source.power_density_W_m2 == 100.0


def test_optical_binding_rejected_for_electrical_protocol():
    with pytest.raises(OperatingBindingError, match="require"):
        apply_operating_binding(
            _electrical(),
            _op("optical", "wavelength_nm"),
            1550.0,
        )


def test_wavelength_binding_rejects_non_monochromatic_source():
    protocol = ElectroOpticalProgramPulseReadProtocol(
        electrical_protocol=_electrical(),
        light_source=LightSource.incandescent(
            power_density_W_m2=100.0,
        ),
        photo_weights=PhotoTransitionWeights(),
    )
    with pytest.raises(OperatingBindingError, match="LED or laser"):
        apply_operating_binding(
            protocol,
            _op("optical", "wavelength_nm"),
            1550.0,
        )


@pytest.mark.parametrize("value", [0.0, -1.0])
def test_optical_power_must_be_strictly_positive(value):
    with pytest.raises(OperatingBindingError, match="strictly positive"):
        apply_operating_binding(
            _electro_optical(),
            _op("optical", "power_density_W_m2"),
            value,
        )


def test_non_operating_scope_is_rejected():
    binding = ParameterBinding(BindingScope.DEVICE, ("temperature_K",))
    with pytest.raises(OperatingBindingError, match="BindingScope.OPERATING"):
        apply_operating_binding(_electrical(), binding, 310.0)


def test_unsupported_operating_path_is_rejected():
    with pytest.raises(OperatingBindingError, match="unsupported operating"):
        apply_operating_binding(
            _electrical(),
            _op("photo", "capture_efficiency"),
            1.0e-3,
        )


def test_duplicate_operating_binding_is_rejected():
    binding = _op("program", "voltage_V")
    with pytest.raises(OperatingBindingError, match="duplicate"):
        apply_operating_bindings(
            _electrical(),
            ((binding, 5.5), (binding, 6.0)),
        )


def test_multiple_operating_bindings_are_applied_atomically():
    base = _electro_optical()
    candidate = apply_operating_bindings(
        base,
        (
            (_op("program", "voltage_V"), 6.0),
            (_op("optical", "wavelength_nm"), 1550.0),
            (_op("optical", "power_density_W_m2"), 200.0),
        ),
    )
    assert candidate.electrical_protocol.program_voltage_V == 6.0
    assert candidate.light_source.wavelength_nm == 1550.0
    assert candidate.light_source.power_density_W_m2 == 200.0
    assert base.electrical_protocol.program_voltage_V == 5.0
    assert base.light_source.wavelength_nm == 1300.0
