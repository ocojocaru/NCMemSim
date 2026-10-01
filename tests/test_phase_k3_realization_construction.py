# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

import pytest

from ncmemsim import DeviceBuilder
from ncmemsim.dtco import (
    BindingScope,
    ParameterBinding,
)
from ncmemsim.ensemble import (
    AppliedRealization,
    EnsembleSample,
    EnsembleSpec,
    NormalDistribution,
    PhysicalDomain,
    RNGSpec,
    RealizationAssignment,
    SamplingSpec,
    SampleDomainValidationError,
    StochasticVariable,
    apply_sample_to_context,
)
from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)
from ncmemsim.program_protocol import (
    ProgramPulseReadProtocol,
)


def provenance():
    return ParameterProvenance(
        source="Phase K3 realization construction test",
        status=ParameterStatus.ASSUMED,
    )


def device():
    return DeviceBuilder.v2(
        n_fgs=1,
        control_sio2_nm=20.0,
        fg_thickness_nm=12.0,
        tunnel_sio2_nm=8.0,
        nc_diameter_nm=5.0,
        nc_volume_fraction=0.60,
        active_fraction=0.22,
        name="k3-realization-base",
    )


def protocol():
    return ProgramPulseReadProtocol(
        program_voltage_V=5.0,
        programming_time_s=1.0e-6,
    )


def diameter_variable():
    return StochasticVariable(
        name="diameter",
        binding=ParameterBinding(
            BindingScope.DEVICE,
            (
                "layers",
                "FG1",
                "nc_diameter_nm",
            ),
        ),
        distribution=NormalDistribution(
            mean=5.0,
            standard_deviation=0.5,
        ),
        unit="nm",
        physical_domain=PhysicalDomain(
            lower=0.0,
            lower_inclusive=False,
        ),
        provenance=provenance(),
        applicability="K3 diameter construction test",
        nominal_value=5.0,
    )


def program_time_variable():
    return StochasticVariable(
        name="program_time",
        binding=ParameterBinding(
            BindingScope.OPERATING,
            (
                "program",
                "time_s",
            ),
        ),
        distribution=NormalDistribution(
            mean=1.0e-6,
            standard_deviation=1.0e-7,
        ),
        unit="s",
        physical_domain=PhysicalDomain(
            lower=0.0,
            lower_inclusive=False,
        ),
        provenance=provenance(),
        applicability="K3 operating construction test",
        nominal_value=1.0e-6,
    )


def sampling_spec(
    base_device,
    *,
    include_operating=False,
    base_protocol=None,
):
    variables = [diameter_variable()]

    if include_operating:
        variables.append(
            program_time_variable()
        )

    ensemble = EnsembleSpec.from_device(
        name="phase-k3-construction-test",
        device=base_device,
        variables=tuple(variables),
        operating_protocol=base_protocol,
    )

    return SamplingSpec(
        ensemble_spec=ensemble,
        rng=RNGSpec(seed=12345),
        sample_count=2,
    )


def test_device_realization_applies_sample_and_preserves_base():
    base = device()
    spec = sampling_spec(base)

    sample = EnsembleSample.from_values(
        spec,
        0,
        (6.0,),
    )

    result = apply_sample_to_context(
        spec,
        sample,
        base,
    )

    assert isinstance(
        result,
        AppliedRealization,
    )

    assert (
        result.device.floating_gates()[0].nc_diameter_nm
        == 6.0
    )

    assert (
        base.floating_gates()[0].nc_diameter_nm
        == 5.0
    )

    assert (
        result.realized_device_hash
        != spec.ensemble_spec.base_device_hash
    )

    result.require_integrity()


def test_realization_records_ordered_binding_assignments():
    base = device()
    spec = sampling_spec(base)

    sample = EnsembleSample.from_values(
        spec,
        0,
        (6.0,),
    )

    result = apply_sample_to_context(
        spec,
        sample,
        base,
    )

    assert len(result.assignments) == 1

    assignment = result.assignments[0]

    assert isinstance(
        assignment,
        RealizationAssignment,
    )
    assert assignment.variable_name == "diameter"
    assert assignment.value == 6.0
    assert assignment.unit == "nm"
    assert (
        assignment.binding
        == spec.ensemble_spec.variables[0].binding
    )


def test_mixed_device_operating_realization():
    base = device()
    base_protocol = protocol()

    spec = sampling_spec(
        base,
        include_operating=True,
        base_protocol=base_protocol,
    )

    sample = EnsembleSample.from_values(
        spec,
        0,
        (
            6.0,
            2.0e-6,
        ),
    )

    result = apply_sample_to_context(
        spec,
        sample,
        base,
        base_protocol,
    )

    assert (
        result.device.floating_gates()[0].nc_diameter_nm
        == 6.0
    )

    assert (
        result.operating_protocol.programming_time_s
        == pytest.approx(2.0e-6)
    )

    assert (
        base.floating_gates()[0].nc_diameter_nm
        == 5.0
    )

    assert (
        base_protocol.programming_time_s
        == pytest.approx(1.0e-6)
    )

    assert result.realized_operating_hash is not None

    result.require_integrity()


def test_zero_variation_construction_preserves_nominal_hashes():
    base = device()
    base_protocol = protocol()

    spec = sampling_spec(
        base,
        include_operating=True,
        base_protocol=base_protocol,
    )

    sample = EnsembleSample.from_values(
        spec,
        0,
        (
            5.0,
            1.0e-6,
        ),
    )

    result = apply_sample_to_context(
        spec,
        sample,
        base,
        base_protocol,
    )

    assert (
        result.realized_device_hash
        == spec.ensemble_spec.base_device_hash
    )

    assert (
        result.realized_operating_hash
        == spec.ensemble_spec.base_operating_hash
    )


def test_changed_base_device_is_rejected():
    base = device()
    spec = sampling_spec(base)

    sample = EnsembleSample.from_values(
        spec,
        0,
        (6.0,),
    )

    base.floating_gates()[0].nc_diameter_nm = 5.5

    with pytest.raises(
        ValueError,
        match="base_device_hash",
    ):
        apply_sample_to_context(
            spec,
            sample,
            base,
        )


def test_missing_required_operating_context_is_rejected():
    base = device()
    base_protocol = protocol()

    spec = sampling_spec(
        base,
        include_operating=True,
        base_protocol=base_protocol,
    )

    sample = EnsembleSample.from_values(
        spec,
        0,
        (
            6.0,
            2.0e-6,
        ),
    )

    with pytest.raises(
        ValueError,
        match="base_operating_protocol is required",
    ):
        apply_sample_to_context(
            spec,
            sample,
            base,
        )


def test_undeclared_operating_context_is_rejected():
    base = device()
    spec = sampling_spec(base)

    sample = EnsembleSample.from_values(
        spec,
        0,
        (6.0,),
    )

    with pytest.raises(
        ValueError,
        match="no operating baseline identity",
    ):
        apply_sample_to_context(
            spec,
            sample,
            base,
            protocol(),
        )


def test_changed_operating_context_is_rejected():
    base = device()
    base_protocol = protocol()

    spec = sampling_spec(
        base,
        include_operating=True,
        base_protocol=base_protocol,
    )

    sample = EnsembleSample.from_values(
        spec,
        0,
        (
            6.0,
            2.0e-6,
        ),
    )

    changed = ProgramPulseReadProtocol(
        program_voltage_V=6.0,
        programming_time_s=1.0e-6,
    )

    with pytest.raises(
        ValueError,
        match="base_operating_hash",
    ):
        apply_sample_to_context(
            spec,
            sample,
            base,
            changed,
        )


def test_domain_failure_occurs_before_binding_application():
    base = device()
    spec = sampling_spec(base)

    sample = EnsembleSample.from_values(
        spec,
        0,
        (0.0,),
    )

    with pytest.raises(
        SampleDomainValidationError
    ):
        apply_sample_to_context(
            spec,
            sample,
            base,
        )

    assert (
        base.floating_gates()[0].nc_diameter_nm
        == 5.0
    )


def test_realized_device_integrity_detects_later_mutation():
    base = device()
    spec = sampling_spec(base)

    sample = EnsembleSample.from_values(
        spec,
        0,
        (6.0,),
    )

    result = apply_sample_to_context(
        spec,
        sample,
        base,
    )

    result.device.floating_gates()[0].nc_diameter_nm = 7.0

    with pytest.raises(
        ValueError,
        match="realized device hash integrity mismatch",
    ):
        result.require_integrity()


def test_operating_only_realization_preserves_nominal_device():
    base = device()
    base_protocol = protocol()

    ensemble = EnsembleSpec.from_device(
        name="phase-k3-operating-only-test",
        device=base,
        variables=(program_time_variable(),),
        operating_protocol=base_protocol,
    )

    spec = SamplingSpec(
        ensemble_spec=ensemble,
        rng=RNGSpec(seed=12345),
        sample_count=1,
    )

    sample = EnsembleSample.from_values(
        spec,
        0,
        (2.0e-6,),
    )

    result = apply_sample_to_context(
        spec,
        sample,
        base,
        base_protocol,
    )

    assert (
        result.realized_device_hash
        == spec.ensemble_spec.base_device_hash
    )

    assert (
        result.device.floating_gates()[0].nc_diameter_nm
        == 5.0
    )

    assert (
        result.operating_protocol.programming_time_s
        == pytest.approx(2.0e-6)
    )

    assert (
        base_protocol.programming_time_s
        == pytest.approx(1.0e-6)
    )


def test_device_only_variables_preserve_declared_operating_baseline():
    base = device()
    base_protocol = protocol()

    spec = sampling_spec(
        base,
        include_operating=False,
        base_protocol=base_protocol,
    )

    sample = EnsembleSample.from_values(
        spec,
        0,
        (6.0,),
    )

    result = apply_sample_to_context(
        spec,
        sample,
        base,
        base_protocol,
    )

    assert (
        result.device.floating_gates()[0].nc_diameter_nm
        == 6.0
    )

    assert (
        result.realized_operating_hash
        == spec.ensemble_spec.base_operating_hash
    )

    assert (
        result.operating_protocol.programming_time_s
        == pytest.approx(1.0e-6)
    )

    assert (
        base_protocol.programming_time_s
        == pytest.approx(1.0e-6)
    )
