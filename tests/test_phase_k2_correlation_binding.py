import pytest

from ncmemsim.dtco import (
    BindingScope,
    ParameterBinding,
)
from ncmemsim.ensemble import (
    ConstantDistribution,
    EnsembleSpec,
    FiniteDiscreteDistribution,
    LogNormalDistribution,
    MatrixCorrelation,
    NormalDistribution,
    PhysicalDomain,
    RNGSpec,
    SamplingSpec,
    StochasticVariable,
    TruncatedNormalDistribution,
    UniformDistribution,
    generate_sample_manifest,
)
from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)


def provenance():
    return ParameterProvenance(
        source="Phase K correlation binding test",
        status=ParameterStatus.ASSUMED,
        notes="Synthetic modelling assumption",
    )


def variable(
    name,
    binding_field,
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
                binding_field,
            ),
        ),
        distribution=distribution,
        unit=unit,
        physical_domain=domain,
        provenance=provenance(),
        applicability=(
            f"Correlation binding test for {name}"
        ),
    )


def continuous_variables():
    return (
        variable(
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
        ),
        variable(
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
        ),
        variable(
            "active_fraction",
            "electrically_active_fraction",
            TruncatedNormalDistribution(
                mean=0.8,
                standard_deviation=0.05,
                lower=0.5,
                upper=1.0,
            ),
            "1",
            PhysicalDomain(
                lower=0.0,
                upper=1.0,
            ),
        ),
        variable(
            "fg_thickness",
            "thickness_nm",
            LogNormalDistribution(
                median=15.0,
                geometric_standard_deviation=1.05,
            ),
            "nm",
            PhysicalDomain(
                lower=0.0,
                lower_inclusive=False,
            ),
        ),
    )


def ensemble(
    variables=None,
):
    if variables is None:
        variables = continuous_variables()

    return EnsembleSpec(
        name="correlation-binding-test",
        base_device_hash="0" * 64,
        variables=tuple(variables),
    )


def matrix_correlation(
    variable_names,
    matrix,
):
    return MatrixCorrelation(
        variable_names=tuple(variable_names),
        matrix=tuple(
            tuple(row)
            for row in matrix
        ),
        provenance=provenance(),
        applicability=(
            "Synthetic latent Gaussian correlation "
            "for binding validation"
        ),
    )


def sampling_spec(
    dependence,
    variables=None,
):
    return SamplingSpec(
        ensemble_spec=ensemble(variables),
        rng=RNGSpec(seed=12345),
        sample_count=4,
        dependence=dependence,
    )


def test_all_initial_continuous_marginals_are_supported():
    dependence = matrix_correlation(
        (
            "diameter",
            "volume_fraction",
            "active_fraction",
            "fg_thickness",
        ),
        (
            (1.0, 0.0, 0.0, 0.0),
            (0.0, 1.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        ),
    )

    spec = sampling_spec(dependence)

    assert spec.dependence == dependence


def test_correlation_may_cover_subset_of_ensemble_variables():
    dependence = matrix_correlation(
        (
            "diameter",
            "active_fraction",
        ),
        (
            (1.0, 0.4),
            (0.4, 1.0),
        ),
    )

    spec = sampling_spec(dependence)

    assert spec.dependence.variable_names == (
        "diameter",
        "active_fraction",
    )


def test_unknown_correlation_variable_is_rejected():
    dependence = matrix_correlation(
        (
            "diameter",
            "unknown",
        ),
        (
            (1.0, 0.2),
            (0.2, 1.0),
        ),
    )

    with pytest.raises(ValueError):
        sampling_spec(dependence)


def test_correlation_variable_order_must_follow_ensemble_order():
    dependence = matrix_correlation(
        (
            "volume_fraction",
            "diameter",
        ),
        (
            (1.0, 0.2),
            (0.2, 1.0),
        ),
    )

    with pytest.raises(ValueError):
        sampling_spec(dependence)


@pytest.mark.parametrize(
    "unsupported_distribution",
    [
        ConstantDistribution(15.0),
        FiniteDiscreteDistribution(
            values=(14.0, 15.0, 16.0),
            probabilities=(0.2, 0.6, 0.2),
        ),
    ],
)
def test_unsupported_marginal_cannot_participate_in_correlation(
    unsupported_distribution,
):
    diameter = continuous_variables()[0]

    thickness = variable(
        "fg_thickness",
        "thickness_nm",
        unsupported_distribution,
        "nm",
        PhysicalDomain(
            lower=0.0,
            lower_inclusive=False,
        ),
    )

    dependence = matrix_correlation(
        (
            "diameter",
            "fg_thickness",
        ),
        (
            (1.0, 0.3),
            (0.3, 1.0),
        ),
    )

    with pytest.raises(ValueError):
        sampling_spec(
            dependence,
            variables=(
                diameter,
                thickness,
            ),
        )


def test_unsupported_marginal_may_remain_uncorrelated():
    diameter = continuous_variables()[0]
    volume_fraction = continuous_variables()[1]

    thickness = variable(
        "fg_thickness",
        "thickness_nm",
        ConstantDistribution(15.0),
        "nm",
        PhysicalDomain(
            lower=0.0,
            lower_inclusive=False,
        ),
    )

    dependence = matrix_correlation(
        (
            "diameter",
            "volume_fraction",
        ),
        (
            (1.0, 0.3),
            (0.3, 1.0),
        ),
    )

    spec = sampling_spec(
        dependence,
        variables=(
            diameter,
            volume_fraction,
            thickness,
        ),
    )

    assert spec.dependence == dependence


def test_sampling_spec_round_trip_with_matrix_correlation():
    dependence = matrix_correlation(
        (
            "diameter",
            "volume_fraction",
        ),
        (
            (1.0, 0.3),
            (0.3, 1.0),
        ),
    )

    original = sampling_spec(dependence)

    restored = SamplingSpec.from_dict(
        original.to_dict()
    )

    assert restored == original
    assert restored.to_dict() == original.to_dict()
    assert (
        restored.definition_hash
        == original.definition_hash
    )


def test_correlation_changes_sampling_spec_identity():
    independent = SamplingSpec(
        ensemble_spec=ensemble(),
        rng=RNGSpec(seed=12345),
        sample_count=4,
    )

    correlated = sampling_spec(
        matrix_correlation(
            (
                "diameter",
                "volume_fraction",
            ),
            (
                (1.0, 0.3),
                (0.3, 1.0),
            ),
        )
    )

    assert (
        independent.definition_hash
        != correlated.definition_hash
    )


def test_correlated_generation_is_not_enabled_yet():
    spec = sampling_spec(
        matrix_correlation(
            (
                "diameter",
                "volume_fraction",
            ),
            (
                (1.0, 0.3),
                (0.3, 1.0),
            ),
        )
    )

    with pytest.raises(ValueError):
        generate_sample_manifest(spec)


def test_independent_sampling_algorithm_is_recorded():
    spec = SamplingSpec(
        ensemble_spec=ensemble(),
        rng=RNGSpec(seed=12345),
        sample_count=4,
    )

    assert spec.dependence_sampling_algorithm == (
        "independent-scalar-v1"
    )

    assert (
        spec.to_dict()[
            "dependence_sampling_algorithm"
        ]
        == "independent-scalar-v1"
    )


def test_gaussian_copula_sampling_algorithm_is_recorded():
    spec = sampling_spec(
        matrix_correlation(
            (
                "diameter",
                "volume_fraction",
            ),
            (
                (1.0, 0.3),
                (0.3, 1.0),
            ),
        )
    )

    assert spec.dependence_sampling_algorithm == (
        "gaussian-copula-sequential-psd-cholesky-v1"
    )

    assert (
        spec.to_dict()[
            "dependence_sampling_algorithm"
        ]
        == "gaussian-copula-sequential-psd-cholesky-v1"
    )


def test_dependence_sampling_algorithm_tampering_is_rejected():
    spec = sampling_spec(
        matrix_correlation(
            (
                "diameter",
                "volume_fraction",
            ),
            (
                (1.0, 0.3),
                (0.3, 1.0),
            ),
        )
    )

    data = spec.to_dict()

    data["dependence_sampling_algorithm"] = (
        "different-algorithm"
    )

    with pytest.raises(ValueError):
        SamplingSpec.from_dict(data)
