# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

import pytest

from ncmemsim.dtco import (
    BindingScope,
    ParameterBinding,
)
from ncmemsim.ensemble import (
    EnsembleSpec,
    NormalDistribution,
    PhysicalDomain,
    RNGSpec,
    SampleGenerationError,
    SamplingSpec,
    StochasticVariable,
    TruncatedNormalDistribution,
    UniformDistribution,
    generate_sample_manifest,
)
from ncmemsim.hashing import canonical_hash
from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)


def provenance():
    return ParameterProvenance(
        source="Phase K manifest test",
        status=ParameterStatus.ASSUMED,
    )


def variables():
    return (
        StochasticVariable(
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
            applicability="NC diameter",
            nominal_value=5.0,
        ),
        StochasticVariable(
            name="volume_fraction",
            binding=ParameterBinding(
                BindingScope.DEVICE,
                (
                    "layers",
                    "FG1",
                    "nc_volume_fraction",
                ),
            ),
            distribution=UniformDistribution(
                lower=0.3,
                upper=0.5,
            ),
            unit="1",
            physical_domain=PhysicalDomain(
                lower=0.0,
                upper=1.0,
            ),
            provenance=provenance(),
            applicability="NC volume fraction",
            nominal_value=0.4,
        ),
    )


def sampling_spec(
    *,
    seed=12345,
    count=4,
):
    ensemble = EnsembleSpec(
        name="manifest-test",
        base_device_hash="0" * 64,
        variables=variables(),
    )

    return SamplingSpec(
        ensemble_spec=ensemble,
        rng=RNGSpec(seed=seed),
        sample_count=count,
    )


def test_manifest_generation_is_deterministic():
    spec = sampling_spec()

    first = generate_sample_manifest(spec)
    second = generate_sample_manifest(spec)

    assert first.to_dict() == second.to_dict()
    assert first.sample_table_hash == second.sample_table_hash
    assert first.manifest_hash == second.manifest_hash


def test_manifest_contains_expected_sample_order():
    manifest = generate_sample_manifest(
        sampling_spec(count=5)
    )

    assert tuple(
        sample.sample_index
        for sample in manifest.samples
    ) == (0, 1, 2, 3, 4)

    assert all(
        sample.variable_names
        == ("diameter", "volume_fraction")
        for sample in manifest.samples
    )


def test_sample_ids_are_unique_and_stable():
    manifest = generate_sample_manifest(
        sampling_spec(count=5)
    )

    sample_ids = tuple(
        sample.sample_id
        for sample in manifest.samples
    )

    assert len(set(sample_ids)) == 5


def test_manifest_sample_table_hash_is_canonical():
    manifest = generate_sample_manifest(
        sampling_spec()
    )

    assert manifest.sample_table_hash == canonical_hash(
        manifest._sample_table_payload()
    )


def test_manifest_hash_is_canonical():
    manifest = generate_sample_manifest(
        sampling_spec()
    )

    assert manifest.manifest_hash == canonical_hash(
        manifest._payload()
    )


def test_seed_changes_sample_table():
    first = generate_sample_manifest(
        sampling_spec(seed=12345)
    )

    second = generate_sample_manifest(
        sampling_spec(seed=12346)
    )

    assert (
        first.sample_table_hash
        != second.sample_table_hash
    )


def test_runtime_metadata_is_recorded():
    manifest = generate_sample_manifest(
        sampling_spec()
    )

    runtime = dict(manifest.runtime)

    assert set(runtime) == {
        "python",
        "python_implementation",
        "numpy",
        "ncmemsim",
    }

    assert all(runtime.values())


def test_generation_is_sample_major_declared_variable_order():
    spec = sampling_spec(count=2)

    manifest = generate_sample_manifest(spec)

    independent_rng = spec.rng.create_generator()

    expected = []

    for _ in range(2):
        row = []

        for variable in spec.ensemble_spec.variables:
            from ncmemsim.ensemble import sample_distribution

            row.append(
                sample_distribution(
                    variable.distribution,
                    independent_rng,
                    max_draws_per_value=(
                        spec.max_draws_per_value
                    ),
                )
            )

        expected.append(tuple(row))

    assert tuple(
        sample.values
        for sample in manifest.samples
    ) == tuple(expected)


def test_generation_does_not_apply_physical_domain_policy():
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
            mean=-5.0,
            standard_deviation=0.01,
        ),
        unit="nm",
        physical_domain=PhysicalDomain(
            lower=0.0,
            lower_inclusive=False,
        ),
        provenance=provenance(),
        applicability="Intentional invalid-domain sample test",
    )

    ensemble = EnsembleSpec(
        name="invalid-domain-generation-test",
        base_device_hash="0" * 64,
        variables=(variable,),
    )

    manifest = generate_sample_manifest(
        SamplingSpec(
            ensemble_spec=ensemble,
            rng=RNGSpec(seed=12345),
            sample_count=1,
        )
    )

    assert manifest.samples[0].values[0] < 0.0


def test_sampling_failure_retains_sample_identity_and_variable():
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
        distribution=TruncatedNormalDistribution(
            mean=100.0,
            standard_deviation=1.0,
            lower=1.0,
            upper=2.0,
        ),
        unit="nm",
        physical_domain=PhysicalDomain(
            lower=0.0,
            lower_inclusive=False,
        ),
        provenance=provenance(),
        applicability="Intentional rejection failure",
    )

    ensemble = EnsembleSpec(
        name="failure-test",
        base_device_hash="0" * 64,
        variables=(variable,),
    )

    spec = SamplingSpec(
        ensemble_spec=ensemble,
        rng=RNGSpec(seed=12345),
        sample_count=2,
        max_draws_per_value=2,
    )

    with pytest.raises(
        SampleGenerationError
    ) as caught:
        generate_sample_manifest(spec)

    error = caught.value

    assert error.sample_index == 0
    assert error.variable_name == "diameter"
    assert error.sampling_spec_hash == spec.definition_hash
    assert len(error.sample_id) == 64
