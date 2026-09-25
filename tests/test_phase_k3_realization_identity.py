import copy

import pytest

from ncmemsim.dtco import (
    BindingScope,
    ParameterBinding,
)
from ncmemsim.ensemble import (
    EnsembleSample,
    EnsembleSpec,
    NormalDistribution,
    PhysicalDomain,
    RNGSpec,
    RealizationIdentity,
    SamplingSpec,
    SampleDomainValidationError,
    StochasticVariable,
    validate_sample_domain,
)
from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)


def provenance():
    return ParameterProvenance(
        source="Phase K3 realization test",
        status=ParameterStatus.ASSUMED,
        notes="Synthetic realization identity test",
    )


def make_sampling_spec(
    *,
    seed=12345,
):
    variable = StochasticVariable(
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
            upper=10.0,
            lower_inclusive=False,
        ),
        provenance=provenance(),
        applicability=(
            "Phase K3 realization identity test"
        ),
    )

    ensemble = EnsembleSpec(
        name="phase-k3-realization-test",
        base_device_hash="1" * 64,
        variables=(variable,),
    )

    return SamplingSpec(
        ensemble_spec=ensemble,
        rng=RNGSpec(seed=seed),
        sample_count=2,
    )


def test_sample_domain_validation_accepts_valid_value():
    spec = make_sampling_spec()

    sample = EnsembleSample.from_values(
        spec,
        0,
        (5.0,),
    )

    validate_sample_domain(
        sample,
        spec,
    )


def test_sample_domain_validation_rejects_out_of_domain_value():
    spec = make_sampling_spec()

    sample = EnsembleSample.from_values(
        spec,
        0,
        (0.0,),
    )

    with pytest.raises(
        SampleDomainValidationError
    ) as exc_info:
        validate_sample_domain(
            sample,
            spec,
        )

    error = exc_info.value

    assert (
        error.sampling_spec_hash
        == spec.definition_hash
    )
    assert error.sample_id == sample.sample_id
    assert error.sample_index == 0
    assert error.variable_name == "diameter"
    assert error.value == 0.0


def test_sample_domain_validation_checks_sample_identity_first():
    first_spec = make_sampling_spec(
        seed=12345,
    )
    second_spec = make_sampling_spec(
        seed=54321,
    )

    sample = EnsembleSample.from_values(
        first_spec,
        0,
        (5.0,),
    )

    with pytest.raises(
        ValueError,
        match=(
            "sample does not match "
            "sampling specification"
        ),
    ):
        validate_sample_domain(
            sample,
            second_spec,
        )


def test_realization_identity_is_deterministic():
    spec = make_sampling_spec()

    sample = EnsembleSample.from_values(
        spec,
        0,
        (5.0,),
    )

    first = RealizationIdentity.from_sample(
        spec,
        sample,
    )

    second = RealizationIdentity.from_sample(
        spec,
        sample,
    )

    assert first == second
    assert (
        first.realization_id
        == second.realization_id
    )


def test_realization_identity_changes_with_sample_index():
    spec = make_sampling_spec()

    first_sample = EnsembleSample.from_values(
        spec,
        0,
        (5.0,),
    )

    second_sample = EnsembleSample.from_values(
        spec,
        1,
        (5.0,),
    )

    first = RealizationIdentity.from_sample(
        spec,
        first_sample,
    )

    second = RealizationIdentity.from_sample(
        spec,
        second_sample,
    )

    assert (
        first.realization_id
        != second.realization_id
    )


def test_realization_identity_commits_to_sample_content():
    spec = make_sampling_spec()

    first_sample = EnsembleSample.from_values(
        spec,
        0,
        (5.0,),
    )

    altered_sample = EnsembleSample(
        sampling_spec_hash=(
            first_sample.sampling_spec_hash
        ),
        sample_index=(
            first_sample.sample_index
        ),
        variable_names=(
            first_sample.variable_names
        ),
        values=(6.0,),
    )

    assert (
        first_sample.sample_id
        == altered_sample.sample_id
    )

    assert (
        first_sample.sample_hash
        != altered_sample.sample_hash
    )

    first = RealizationIdentity.from_sample(
        spec,
        first_sample,
    )

    altered = RealizationIdentity.from_sample(
        spec,
        altered_sample,
    )

    assert (
        first.realization_id
        != altered.realization_id
    )


def test_realization_identity_round_trip():
    spec = make_sampling_spec()

    sample = EnsembleSample.from_values(
        spec,
        0,
        (5.0,),
    )

    identity = RealizationIdentity.from_sample(
        spec,
        sample,
    )

    restored = RealizationIdentity.from_dict(
        identity.to_dict()
    )

    assert restored == identity
    assert (
        restored.realization_id
        == identity.realization_id
    )


def test_realization_identity_rejects_tampered_hash():
    spec = make_sampling_spec()

    sample = EnsembleSample.from_values(
        spec,
        0,
        (5.0,),
    )

    identity = RealizationIdentity.from_sample(
        spec,
        sample,
    )

    payload = copy.deepcopy(
        identity.to_dict()
    )

    payload["realization_id"] = "0" * 64

    with pytest.raises(
        ValueError,
        match="realization_id integrity mismatch",
    ):
        RealizationIdentity.from_dict(
            payload
        )


def test_realization_identity_exists_before_domain_validation():
    spec = make_sampling_spec()

    sample = EnsembleSample.from_values(
        spec,
        0,
        (0.0,),
    )

    identity = RealizationIdentity.from_sample(
        spec,
        sample,
    )

    assert identity.sample_id == sample.sample_id
    assert identity.sample_hash == sample.sample_hash
    assert identity.sample_index == 0

    with pytest.raises(
        SampleDomainValidationError
    ):
        validate_sample_domain(
            sample,
            spec,
        )
