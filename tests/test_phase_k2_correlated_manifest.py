# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

import pytest

from ncmemsim.dtco import (
    BindingScope,
    ParameterBinding,
)
from ncmemsim.ensemble import (
    EnsembleSpec,
    MatrixCorrelation,
    NormalDistribution,
    PhysicalDomain,
    RNGSpec,
    SamplingSpec,
    StochasticVariable,
    UniformDistribution,
    generate_sample_manifest,
)
from ncmemsim.ensemble.sampling import (
    _sequential_psd_cholesky,
    _standard_normal,
    _unit_interval,
)
from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)


def provenance():
    return ParameterProvenance(
        source="Phase K correlated manifest test",
        status=ParameterStatus.ASSUMED,
        notes="Synthetic dependence test",
    )


def variable(
    name,
    field,
    distribution,
    unit,
    domain,
):
    return StochasticVariable(
        name=name,
        binding=ParameterBinding(
            BindingScope.DEVICE,
            (
                "layers",
                "FG1",
                field,
            ),
        ),
        distribution=distribution,
        unit=unit,
        physical_domain=domain,
        provenance=provenance(),
        applicability=(
            f"Correlated manifest test for {name}"
        ),
    )


def make_spec(
    *,
    sample_count=3,
    seed=12345,
):
    diameter = variable(
        "diameter",
        "nc_diameter_nm",
        NormalDistribution(
            mean=5.0,
            standard_deviation=0.5,
        ),
        "nm",
        PhysicalDomain(
            lower=0.0,
            lower_inclusive=False,
        ),
    )

    volume_fraction = variable(
        "volume_fraction",
        "nc_volume_fraction",
        UniformDistribution(
            lower=0.3,
            upper=0.5,
        ),
        "1",
        PhysicalDomain(
            lower=0.0,
            upper=1.0,
        ),
    )

    active_fraction = variable(
        "active_fraction",
        "electrically_active_fraction",
        NormalDistribution(
            mean=0.8,
            standard_deviation=0.05,
        ),
        "1",
        PhysicalDomain(
            lower=0.0,
            upper=1.0,
        ),
    )

    ensemble = EnsembleSpec(
        name="correlated-manifest-test",
        base_device_hash="0" * 64,
        variables=(
            diameter,
            volume_fraction,
            active_fraction,
        ),
    )

    dependence = MatrixCorrelation(
        variable_names=(
            "diameter",
            "active_fraction",
        ),
        matrix=(
            (1.0, 0.6),
            (0.6, 1.0),
        ),
        provenance=provenance(),
        applicability=(
            "Synthetic latent Gaussian correlation"
        ),
    )

    return SamplingSpec(
        ensemble_spec=ensemble,
        rng=RNGSpec(seed=seed),
        sample_count=sample_count,
        dependence=dependence,
    )


def test_correlated_manifest_is_deterministic():
    spec = make_spec()

    first = generate_sample_manifest(
        spec
    )

    second = generate_sample_manifest(
        spec
    )

    assert (
        first.sample_table_hash
        == second.sample_table_hash
    )

    assert first.samples == second.samples


def test_correlated_manifest_preserves_declared_variable_order():
    spec = make_spec()

    manifest = generate_sample_manifest(
        spec
    )

    for sample in manifest.samples:
        assert sample.variable_names == (
            "diameter",
            "volume_fraction",
            "active_fraction",
        )


def test_rng_consumption_follows_declared_variable_order():
    spec = make_spec(
        sample_count=1,
        seed=12345,
    )

    manifest = generate_sample_manifest(
        spec
    )

    rng = spec.rng.create_generator()

    dependence = spec.dependence

    assert isinstance(
        dependence,
        MatrixCorrelation,
    )

    factor = _sequential_psd_cholesky(
        dependence
    )

    first_latent = _standard_normal(
        rng
    )

    expected_diameter = (
        5.0
        + 0.5 * first_latent
    )

    uniform_draw = _unit_interval(
        rng
    )

    expected_volume_fraction = (
        (1.0 - uniform_draw) * 0.3
        + uniform_draw * 0.5
    )

    second_independent_latent = (
        _standard_normal(
            rng
        )
    )

    second_correlated_latent = (
        factor[1][0]
        * first_latent
        + factor[1][1]
        * second_independent_latent
    )

    expected_active_fraction = (
        0.8
        + 0.05
        * second_correlated_latent
    )

    sample = manifest.samples[0]

    assert sample.values == pytest.approx(
        (
            expected_diameter,
            expected_volume_fraction,
            expected_active_fraction,
        ),
        abs=1.0e-15,
    )


def test_correlation_does_not_change_uncorrelated_variable_transform():
    spec = make_spec(
        sample_count=1,
    )

    manifest = generate_sample_manifest(
        spec
    )

    volume_fraction = (
        manifest.samples[0].values[1]
    )

    assert 0.3 <= volume_fraction <= 0.5


def test_correlated_manifest_round_trip_is_archival_without_resampling():
    spec = make_spec()

    manifest = generate_sample_manifest(
        spec
    )

    restored = type(manifest).from_json(
        manifest.to_json()
    )

    assert restored.to_dict() == manifest.to_dict()

    assert (
        restored.manifest_hash
        == manifest.manifest_hash
    )


def test_sample_identity_remains_index_based():
    spec = make_spec()

    manifest = generate_sample_manifest(
        spec
    )

    assert (
        manifest.samples[0].sample_id
        != manifest.samples[1].sample_id
    )

    assert (
        manifest.samples[0].sampling_spec_hash
        == spec.definition_hash
    )


def test_different_seed_changes_correlated_sample_table():
    first = generate_sample_manifest(
        make_spec(seed=12345)
    )

    second = generate_sample_manifest(
        make_spec(seed=54321)
    )

    assert (
        first.sample_table_hash
        != second.sample_table_hash
    )
