from dataclasses import replace
import math

import numpy as np
import pytest

from ncmemsim import DeviceBuilder
from ncmemsim.dtco import (
    BindingScope,
    ParameterBinding,
    BindingApplicationError,
    OperatingBindingError,
)
import ncmemsim.ensemble.execution as execution_module
from ncmemsim.ensemble import (
    EnsembleSample,
    EnsembleSpec,
    NormalDistribution,
    PhysicalDomain,
    RNGSpec,
    SampleManifest,
    SamplingSpec,
    StochasticVariable,
    execute_sample_manifest,
    generate_sample_manifest,
)
from ncmemsim.hashing import canonical_hash
from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)
from ncmemsim.program_protocol import (
    ProgramPulseReadProtocol,
)


def provenance():
    return ParameterProvenance(
        source="Phase K3 execution test",
        status=ParameterStatus.ASSUMED,
    )


def device():
    return DeviceBuilder.v2(
        n_fgs=1,
        nc_diameter_nm=5.0,
        name="k3-execution-base",
    )


def variable(
    *,
    layer="FG1",
):
    return StochasticVariable(
        name="diameter",
        binding=ParameterBinding(
            BindingScope.DEVICE,
            (
                "layers",
                layer,
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
        applicability="Phase K3 execution test",
        nominal_value=5.0,
    )


def manifest(
    values=(5.5, 6.0, 6.5),
    *,
    layer="FG1",
):
    base = device()

    ensemble = EnsembleSpec.from_device(
        name="phase-k3-execution-test",
        device=base,
        variables=(
            variable(layer=layer),
        ),
    )

    spec = SamplingSpec(
        ensemble_spec=ensemble,
        rng=RNGSpec(seed=12345),
        sample_count=len(values),
    )

    runtime = generate_sample_manifest(
        spec
    ).runtime

    samples = tuple(
        EnsembleSample.from_values(
            spec,
            index,
            (float(value),),
        )
        for index, value
        in enumerate(values)
    )

    return (
        base,
        SampleManifest(
            sampling_spec=spec,
            samples=samples,
            runtime=runtime,
        ),
    )


def evaluator(candidate, protocol, realization):
    return {
        "index": (
            realization.identity.sample_index
        ),
        "diameter": (
            candidate
            .floating_gates()[0]
            .nc_diameter_nm
        ),
    }


def test_exact_manifest_order_and_no_resampling(
    monkeypatch,
):
    base, original = manifest()

    restored = SampleManifest.from_json(
        original.to_json()
    )

    def forbidden(*args, **kwargs):
        raise AssertionError(
            "execution attempted resampling"
        )

    monkeypatch.setattr(
        np.random,
        "PCG64",
        forbidden,
    )

    first = execute_sample_manifest(
        restored,
        base,
        evaluator,
        evaluation_id="k3-execution-test",
    )

    second = execute_sample_manifest(
        restored,
        base,
        evaluator,
        evaluation_id="k3-execution-test",
    )

    assert (
        first.to_json()
        == second.to_json()
    )

    assert first.success_count == 3
    assert first.failure_count == 0

    assert [
        point.identity.sample_index
        for point in first.points
    ] == [0, 1, 2]

    assert [
        point.output["diameter"]
        for point in first.points
    ] == [5.5, 6.0, 6.5]


def test_success_records_exact_realized_context():
    base, samples = manifest(
        values=(6.0,),
    )

    result = execute_sample_manifest(
        samples,
        base,
        evaluator,
        evaluation_id="context-test",
    )

    point = result.points[0]

    assert point.status == "success"

    assert (
        point.realized_context[
            "device"
        ]
        is not None
    )

    assert (
        canonical_hash(
            point.realized_context[
                "device"
            ]
        )
        == point.realized_device_hash
    )

    assert (
        point.assignments[0].value
        == 6.0
    )


def test_domain_failure_is_isolated_and_execution_continues():
    base, samples = manifest(
        values=(5.5, 0.0, 6.5),
    )

    result = execute_sample_manifest(
        samples,
        base,
        evaluator,
        evaluation_id="domain-failure",
    )

    assert [
        point.status
        for point in result.points
    ] == [
        "success",
        "failed",
        "success",
    ]

    failed = result.points[1]

    assert (
        failed.failure_stage
        == "sample-domain-validation"
    )

    assert (
        failed.identity.sample_id
        == samples.samples[1].sample_id
    )

    assert failed.assignments == ()
    assert failed.realized_context is None

    assert (
        failed.failure_category
        == "sample-domain-invalid"
    )

    with pytest.raises(
        ValueError,
        match="failure category",
    ):
        replace(
            failed,
            failure_category="wrong-category",
        )


def test_realization_construction_failure_is_isolated(
    monkeypatch,
):
    base, samples = manifest(
        values=(5.5, 6.5, 5.8),
    )

    original = (
        execution_module
        .apply_sample_to_context
    )

    def fail_second(
        sampling_spec,
        sample,
        base_device,
        base_operating_protocol=None,
    ):
        if sample.sample_index == 1:
            raise RuntimeError(
                "realization construction failed"
            )

        return original(
            sampling_spec,
            sample,
            base_device,
            base_operating_protocol,
        )

    monkeypatch.setattr(
        execution_module,
        "apply_sample_to_context",
        fail_second,
    )

    result = execute_sample_manifest(
        samples,
        base,
        evaluator,
        evaluation_id="construction-failure",
    )

    assert result.success_count == 2
    assert result.failure_count == 1

    failed = result.points[1]

    assert (
        failed.failure_stage
        == "realization-construction"
    )

    assert (
        failed.failure_category
        == "realization-invalid"
    )

    assert failed.assignments == ()
    assert failed.realized_context is None

    assert (
        result.points[0].status
        == "success"
    )

    assert (
        result.points[2].status
        == "success"
    )


def test_workflow_failure_is_isolated():
    base, samples = manifest()

    def fail_second(
        candidate,
        protocol,
        realization,
    ):
        if (
            realization
            .identity
            .sample_index
            == 1
        ):
            raise RuntimeError(
                "numerical workflow failure"
            )

        return evaluator(
            candidate,
            protocol,
            realization,
        )

    result = execute_sample_manifest(
        samples,
        base,
        fail_second,
        evaluation_id="workflow-failure",
    )

    failed = result.points[1]

    assert (
        failed.failure_stage
        == "workflow"
    )

    assert failed.output is None

    assert len(
        failed.assignments
    ) == 1

    assert (
        failed.realized_context
        is not None
    )

    assert (
        result.points[2].status
        == "success"
    )

    assert (
        failed.failure_category
        == "workflow-execution"
    )


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        {"bad": math.nan},
        {1: "bad"},
        {"bad": np.array([1])},
    ],
)
def test_invalid_outputs_are_serialization_failures(
    value,
):
    base, samples = manifest(
        values=(5.5,),
    )

    result = execute_sample_manifest(
        samples,
        base,
        lambda *args: value,
        evaluation_id="serialization-failure",
    )

    point = result.points[0]

    assert point.status == "failed"
    assert (
        point.failure_stage
        == "serialization"
    )
    assert point.output is None
    assert (
        point.realized_context
        is not None
    )

    assert (
        point.failure_category
        == "output-serialization"
    )


@pytest.mark.parametrize(
    "exception",
    [
        KeyboardInterrupt,
        SystemExit,
    ],
)
def test_interrupts_propagate(
    exception,
):
    base, samples = manifest(
        values=(5.5,),
    )

    def stop(*args):
        raise exception

    with pytest.raises(exception):
        execute_sample_manifest(
            samples,
            base,
            stop,
            evaluation_id="interrupt",
        )


def test_callback_mutation_is_isolated_from_other_samples():
    base, samples = manifest()

    seen = []

    def mutate(
        candidate,
        protocol,
        realization,
    ):
        assert (
            candidate.metadata.get(
                "mutated"
            )
            is None
        )

        seen.append(candidate)

        candidate.metadata[
            "mutated"
        ] = True

        return {
            "index": (
                realization
                .identity
                .sample_index
            )
        }

    result = execute_sample_manifest(
        samples,
        base,
        mutate,
        evaluation_id="mutation-isolation",
    )

    assert result.success_count == 3

    assert (
        len(
            {
                id(candidate)
                for candidate in seen
            }
        )
        == 3
    )

    assert (
        base.metadata.get(
            "mutated"
        )
        is None
    )


def test_caller_baseline_mutation_does_not_change_frozen_study():
    base, samples = manifest()

    expected_nominal_hash = (
        samples
        .sampling_spec
        .ensemble_spec
        .base_device_hash
    )

    def mutate_caller(
        candidate,
        protocol,
        realization,
    ):
        base.temperature_K = 999.0

        return {
            "index": (
                realization
                .identity
                .sample_index
            )
        }

    result = execute_sample_manifest(
        samples,
        base,
        mutate_caller,
        evaluation_id="caller-mutation",
    )

    assert result.success_count == 3

    assert base.temperature_K == 999.0

    nominal_device = (
        result
        .to_dict()
        ["execution"]
        ["nominal"]
        ["device"]
    )

    assert (
        canonical_hash(
            nominal_device
        )
        == expected_nominal_hash
    )


def test_setup_error_occurs_before_callback():
    base, samples = manifest()

    base.floating_gates()[
        0
    ].nc_diameter_nm = 8.0

    calls = []

    with pytest.raises(
        ValueError,
        match="base_device_hash",
    ):
        execute_sample_manifest(
            samples,
            base,
            lambda *args: (
                calls.append(1)
                or {"ok": True}
            ),
            evaluation_id="setup-error",
        )

    assert calls == []


def test_result_rejects_missing_or_reordered_points():
    base, samples = manifest()

    result = execute_sample_manifest(
        samples,
        base,
        evaluator,
        evaluation_id="integrity-test",
    )

    with pytest.raises(ValueError):
        replace(
            result,
            points=result.points[:-1],
        )

    with pytest.raises(ValueError):
        replace(
            result,
            points=tuple(
                reversed(
                    result.points
                )
            ),
        )


def test_operating_realization_records_exact_context():
    base = device()

    base_protocol = ProgramPulseReadProtocol(
        program_voltage_V=5.0,
        programming_time_s=1.0e-6,
    )

    operating_variable = StochasticVariable(
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
        applicability="Phase K3 operating execution test",
        nominal_value=1.0e-6,
    )

    ensemble = EnsembleSpec.from_device(
        name="phase-k3-operating-execution",
        device=base,
        variables=(operating_variable,),
        operating_protocol=base_protocol,
    )

    spec = SamplingSpec(
        ensemble_spec=ensemble,
        rng=RNGSpec(seed=12345),
        sample_count=1,
    )

    runtime = generate_sample_manifest(
        spec
    ).runtime

    samples = SampleManifest(
        sampling_spec=spec,
        samples=(
            EnsembleSample.from_values(
                spec,
                0,
                (2.0e-6,),
            ),
        ),
        runtime=runtime,
    )

    result = execute_sample_manifest(
        samples,
        base,
        lambda candidate, protocol, realization: {
            "duration": protocol.programming_time_s,
        },
        evaluation_id="operating-context",
        base_operating_protocol=base_protocol,
    )

    point = result.points[0]

    assert point.status == "success"

    assert (
        point.output["duration"]
        == pytest.approx(2.0e-6)
    )

    assert (
        point.realized_context[
            "operating"
        ]["protocol"]["programming_time_s"]
        == pytest.approx(2.0e-6)
    )

    assert (
        canonical_hash(
            point.realized_context[
                "operating"
            ]
        )
        == point.realized_operating_hash
    )

    assert (
        base_protocol.programming_time_s
        == pytest.approx(1.0e-6)
    )


def test_protocol_mutation_is_isolated_between_samples():
    base = device()

    base_protocol = ProgramPulseReadProtocol(
        program_voltage_V=5.0,
        programming_time_s=1.0e-6,
    )

    operating_variable = StochasticVariable(
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
        applicability="Phase K3 protocol isolation test",
        nominal_value=1.0e-6,
    )

    ensemble = EnsembleSpec.from_device(
        name="phase-k3-protocol-isolation",
        device=base,
        variables=(operating_variable,),
        operating_protocol=base_protocol,
    )

    spec = SamplingSpec(
        ensemble_spec=ensemble,
        rng=RNGSpec(seed=12345),
        sample_count=2,
    )

    runtime = generate_sample_manifest(
        spec
    ).runtime

    samples = SampleManifest(
        sampling_spec=spec,
        samples=(
            EnsembleSample.from_values(
                spec,
                0,
                (2.0e-6,),
            ),
            EnsembleSample.from_values(
                spec,
                1,
                (3.0e-6,),
            ),
        ),
        runtime=runtime,
    )

    seen = []

    def mutate_protocol(
        candidate,
        protocol,
        realization,
    ):
        seen.append(
            protocol.programming_time_s
        )

        object.__setattr__(
            protocol,
            "programming_time_s",
            99.0,
        )

        return {
            "index": (
                realization
                .identity
                .sample_index
            )
        }

    result = execute_sample_manifest(
        samples,
        base,
        mutate_protocol,
        evaluation_id="protocol-isolation",
        base_operating_protocol=base_protocol,
    )

    assert result.success_count == 2

    assert seen == pytest.approx(
        [
            2.0e-6,
            3.0e-6,
        ]
    )

    assert (
        base_protocol.programming_time_s
        == pytest.approx(1.0e-6)
    )

    assert (
        result.points[0]
        .realized_context["operating"]
        ["protocol"]["programming_time_s"]
        == pytest.approx(2.0e-6)
    )

    assert (
        result.points[1]
        .realized_context["operating"]
        ["protocol"]["programming_time_s"]
        == pytest.approx(3.0e-6)
    )


@pytest.mark.parametrize(
    "exception_type",
    [
        BindingApplicationError,
        OperatingBindingError,
    ],
)
def test_binding_failure_has_distinct_stage_and_category(
    monkeypatch,
    exception_type,
):
    base, samples = manifest(
        values=(5.5, 6.0),
    )

    original = (
        execution_module
        .apply_sample_to_context
    )

    calls = []

    def fail_first(
        sampling_spec,
        sample,
        base_device,
        base_operating_protocol=None,
    ):
        calls.append(
            sample.sample_index
        )

        if sample.sample_index == 0:
            raise exception_type(
                "controlled binding failure"
            )

        return original(
            sampling_spec,
            sample,
            base_device,
            base_operating_protocol,
        )

    monkeypatch.setattr(
        execution_module,
        "apply_sample_to_context",
        fail_first,
    )

    result = execute_sample_manifest(
        samples,
        base,
        evaluator,
        evaluation_id="binding-failure",
    )

    assert (
        result.success_count,
        result.failure_count,
    ) == (1, 1)

    failed = result.points[0]

    assert failed.status == "failed"

    assert (
        failed.failure_stage
        == "binding"
    )

    assert (
        failed.failure_category
        == "binding-application"
    )

    assert (
        failed.error_type
        == (
            f"{exception_type.__module__}."
            f"{exception_type.__qualname__}"
        )
    )

    assert failed.assignments == ()
    assert failed.realized_context is None

    assert (
        result.points[1].status
        == "success"
    )

    assert calls == [0, 1]
