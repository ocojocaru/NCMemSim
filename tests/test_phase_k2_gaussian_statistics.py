import math

import numpy as np
import pytest

from ncmemsim.dtco import (
    BindingScope,
    ParameterBinding,
)
from ncmemsim.ensemble import (
    EnsembleSpec,
    LogNormalDistribution,
    MatrixCorrelation,
    NormalDistribution,
    PhysicalDomain,
    RNGSpec,
    SamplingSpec,
    StochasticVariable,
    UniformDistribution,
    generate_sample_manifest,
)
from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)


SAMPLE_COUNT = 8000
LATENT_CORRELATION = 0.65
SEED = 24680
STATISTICAL_TOLERANCE = 0.025


def provenance():
    return ParameterProvenance(
        source="Phase K Gaussian copula statistical validation",
        status=ParameterStatus.ASSUMED,
        notes="Deterministic synthetic validation population",
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
            f"Gaussian copula statistical validation for {name}"
        ),
    )


def sampling_spec(
    first_variable,
    second_variable,
):
    ensemble = EnsembleSpec(
        name="gaussian-copula-statistical-validation",
        base_device_hash="0" * 64,
        variables=(
            first_variable,
            second_variable,
        ),
    )

    dependence = MatrixCorrelation(
        variable_names=(
            first_variable.name,
            second_variable.name,
        ),
        matrix=(
            (
                1.0,
                LATENT_CORRELATION,
            ),
            (
                LATENT_CORRELATION,
                1.0,
            ),
        ),
        provenance=provenance(),
        applicability=(
            "Synthetic latent Gaussian Pearson correlation"
        ),
    )

    return SamplingSpec(
        ensemble_spec=ensemble,
        rng=RNGSpec(seed=SEED),
        sample_count=SAMPLE_COUNT,
        dependence=dependence,
    )


def values_from_manifest(
    specification,
):
    manifest = generate_sample_manifest(
        specification
    )

    return np.asarray(
        [
            sample.values
            for sample in manifest.samples
        ],
        dtype=np.float64,
    )


def ordinal_ranks(
    values,
):
    order = np.argsort(
        values,
        kind="mergesort",
    )

    ranks = np.empty(
        values.size,
        dtype=np.float64,
    )

    ranks[order] = np.arange(
        values.size,
        dtype=np.float64,
    )

    return ranks


def test_normal_normal_physical_pearson_matches_latent_correlation():
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

    thickness = variable(
        "thickness",
        "thickness_nm",
        NormalDistribution(
            mean=15.0,
            standard_deviation=1.0,
        ),
        "nm",
        PhysicalDomain(
            lower=0.0,
            lower_inclusive=False,
        ),
    )

    values = values_from_manifest(
        sampling_spec(
            diameter,
            thickness,
        )
    )

    pearson = float(
        np.corrcoef(
            values[:, 0],
            values[:, 1],
        )[0, 1]
    )

    assert pearson == pytest.approx(
        LATENT_CORRELATION,
        abs=STATISTICAL_TOLERANCE,
    )


def test_nonlinear_marginals_match_gaussian_copula_spearman_relation():
    volume_fraction = variable(
        "volume_fraction",
        "nc_volume_fraction",
        UniformDistribution(
            lower=0.2,
            upper=0.6,
        ),
        "1",
        PhysicalDomain(
            lower=0.0,
            upper=1.0,
        ),
    )

    thickness = variable(
        "thickness",
        "thickness_nm",
        LogNormalDistribution(
            median=15.0,
            geometric_standard_deviation=2.0,
        ),
        "nm",
        PhysicalDomain(
            lower=0.0,
            lower_inclusive=False,
        ),
    )

    values = values_from_manifest(
        sampling_spec(
            volume_fraction,
            thickness,
        )
    )

    first = values[:, 0]
    second = values[:, 1]

    assert (
        np.unique(first).size
        == SAMPLE_COUNT
    )

    assert (
        np.unique(second).size
        == SAMPLE_COUNT
    )

    first_ranks = ordinal_ranks(
        first
    )

    second_ranks = ordinal_ranks(
        second
    )

    spearman = float(
        np.corrcoef(
            first_ranks,
            second_ranks,
        )[0, 1]
    )

    expected_spearman = (
        6.0
        / math.pi
        * math.asin(
            LATENT_CORRELATION
            / 2.0
        )
    )

    assert spearman == pytest.approx(
        expected_spearman,
        abs=STATISTICAL_TOLERANCE,
    )


def test_nonlinear_physical_pearson_is_not_the_latent_contract():
    volume_fraction = variable(
        "volume_fraction",
        "nc_volume_fraction",
        UniformDistribution(
            lower=0.2,
            upper=0.6,
        ),
        "1",
        PhysicalDomain(
            lower=0.0,
            upper=1.0,
        ),
    )

    thickness = variable(
        "thickness",
        "thickness_nm",
        LogNormalDistribution(
            median=15.0,
            geometric_standard_deviation=2.0,
        ),
        "nm",
        PhysicalDomain(
            lower=0.0,
            lower_inclusive=False,
        ),
    )

    values = values_from_manifest(
        sampling_spec(
            volume_fraction,
            thickness,
        )
    )

    physical_pearson = float(
        np.corrcoef(
            values[:, 0],
            values[:, 1],
        )[0, 1]
    )

    assert abs(
        physical_pearson
        - LATENT_CORRELATION
    ) > 0.05
