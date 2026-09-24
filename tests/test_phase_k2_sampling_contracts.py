from dataclasses import FrozenInstanceError, replace

import pytest

from ncmemsim.dtco import BindingScope, ParameterBinding
from ncmemsim.ensemble import (
    EnsembleSample,
    EnsembleSpec,
    IndependentDependence,
    NormalDistribution,
    PhysicalDomain,
    RNGSpec,
    SamplingSpec,
    StochasticVariable,
)
from ncmemsim.hashing import canonical_hash
from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)


def provenance():
    return ParameterProvenance(
        source="Phase K sampling contract test",
        status=ParameterStatus.ASSUMED,
    )


def variable():
    return StochasticVariable(
        name="diameter",
        binding=ParameterBinding(
            BindingScope.DEVICE,
            ("layers", "FG1", "nc_diameter_nm"),
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
        applicability="Reference NC diameter",
        nominal_value=5.0,
    )


def ensemble():
    return EnsembleSpec(
        name="sampling-contract-test",
        base_device_hash="0" * 64,
        base_device_name="reference-device",
        variables=(variable(),),
    )


def sampling_spec(
    *,
    seed=12345,
    sample_count=4,
):
    return SamplingSpec(
        ensemble_spec=ensemble(),
        rng=RNGSpec(seed=seed),
        sample_count=sample_count,
    )


def test_independence_is_explicit():
    dependence = IndependentDependence()

    assert dependence.kind == "independent"
    assert dependence.to_dict() == {
        "schema_version": "ensemble-dependence-v1",
        "kind": "independent",
    }
    assert dependence.definition_hash == canonical_hash(
        dependence.to_dict()
    )


def test_independence_round_trip():
    original = IndependentDependence()

    restored = IndependentDependence.from_dict(
        original.to_dict()
    )

    assert restored == original
    assert restored.definition_hash == original.definition_hash


def test_sampling_spec_defaults_are_explicit():
    item = sampling_spec()

    assert item.sample_count == 4
    assert item.dependence.kind == "independent"
    assert item.max_draws_per_value == 10000
    assert item.scalar_sampling_algorithm == (
        "phase-k-pcg64-raw53-box-muller-v1"
    )
    assert item.order == (
        "sample-major,declared-variable-order"
    )
    assert item.precision == (
        "float64-derived-python-float"
    )
    assert item.schema_version == (
        "ensemble-sampling-spec-v1"
    )


def test_sampling_spec_hash_is_canonical():
    item = sampling_spec()

    assert item.definition_hash == canonical_hash(
        item.to_dict()
    )


def test_sampling_spec_round_trip():
    original = sampling_spec()

    restored = SamplingSpec.from_dict(
        original.to_dict()
    )

    assert restored == original
    assert restored.to_dict() == original.to_dict()
    assert restored.definition_hash == original.definition_hash


def test_sampling_spec_ensemble_hash_integrity():
    data = sampling_spec().to_dict()
    data["ensemble_spec_hash"] = "1" * 64

    with pytest.raises(ValueError):
        SamplingSpec.from_dict(data)


@pytest.mark.parametrize(
    "sample_count",
    [0, -1],
)
def test_sample_count_must_be_positive(sample_count):
    with pytest.raises(ValueError):
        sampling_spec(
            sample_count=sample_count
        )


@pytest.mark.parametrize(
    "sample_count",
    [True, 1.0, "1", None],
)
def test_sample_count_requires_integer(sample_count):
    with pytest.raises(TypeError):
        sampling_spec(
            sample_count=sample_count
        )


@pytest.mark.parametrize(
    "field, value",
    [
        (
            "scalar_sampling_algorithm",
            "different",
        ),
        ("order", "variable-major"),
        ("precision", "float32"),
        ("schema_version", "ensemble-sampling-spec-v2"),
    ],
)
def test_sampling_contract_identity_is_fixed(field, value):
    with pytest.raises(ValueError):
        replace(
            sampling_spec(),
            **{field: value},
        )


def test_sampling_spec_changes_with_seed():
    first = sampling_spec(seed=12345)
    second = sampling_spec(seed=12346)

    assert first.definition_hash != second.definition_hash


def test_sampling_spec_changes_with_sample_count():
    first = sampling_spec(sample_count=4)
    second = sampling_spec(sample_count=5)

    assert first.definition_hash != second.definition_hash


def test_sample_from_values_has_stable_identity():
    spec = sampling_spec()

    first = EnsembleSample.from_values(
        spec,
        sample_index=0,
        values=(5.1,),
    )

    second = EnsembleSample.from_values(
        spec,
        sample_index=0,
        values=(5.1,),
    )

    assert first.sample_id == second.sample_id
    assert first.sample_hash == second.sample_hash


def test_sample_index_changes_sample_id():
    spec = sampling_spec()

    first = EnsembleSample.from_values(
        spec,
        sample_index=0,
        values=(5.1,),
    )

    second = EnsembleSample.from_values(
        spec,
        sample_index=1,
        values=(5.1,),
    )

    assert first.sample_id != second.sample_id


def test_values_change_content_hash_not_identity():
    spec = sampling_spec()

    first = EnsembleSample.from_values(
        spec,
        sample_index=0,
        values=(5.1,),
    )

    second = EnsembleSample.from_values(
        spec,
        sample_index=0,
        values=(5.2,),
    )

    assert first.sample_id == second.sample_id
    assert first.sample_hash != second.sample_hash


def test_sample_outside_physical_domain_is_preserved():
    sample = EnsembleSample.from_values(
        sampling_spec(),
        sample_index=0,
        values=(-1.0,),
    )

    assert sample.values == (-1.0,)


def test_sample_round_trip():
    original = EnsembleSample.from_values(
        sampling_spec(),
        sample_index=2,
        values=(5.25,),
    )

    restored = EnsembleSample.from_dict(
        original.to_dict()
    )

    assert restored == original
    assert restored.sample_id == original.sample_id
    assert restored.sample_hash == original.sample_hash


def test_sample_id_tampering_is_detected():
    data = EnsembleSample.from_values(
        sampling_spec(),
        0,
        (5.0,),
    ).to_dict()

    data["sample_id"] = "0" * 64

    with pytest.raises(ValueError):
        EnsembleSample.from_dict(data)


def test_sample_content_tampering_is_detected():
    data = EnsembleSample.from_values(
        sampling_spec(),
        0,
        (5.0,),
    ).to_dict()

    data["values"][0] = 6.0

    with pytest.raises(ValueError):
        EnsembleSample.from_dict(data)


def test_sample_requires_finite_float_values():
    spec = sampling_spec()

    for value in (
        5,
        float("nan"),
        float("inf"),
        -float("inf"),
    ):
        with pytest.raises(ValueError):
            EnsembleSample.from_values(
                spec,
                0,
                (value,),
            )


def test_sample_width_must_match_variable_order():
    with pytest.raises(ValueError):
        EnsembleSample.from_values(
            sampling_spec(),
            0,
            (),
        )


def test_sample_index_must_be_inside_spec():
    with pytest.raises(ValueError):
        EnsembleSample.from_values(
            sampling_spec(sample_count=2),
            2,
            (5.0,),
        )


def test_sample_matches_sampling_spec():
    spec = sampling_spec()

    sample = EnsembleSample.from_values(
        spec,
        0,
        (5.0,),
    )

    sample.require_matches_spec(spec)


def test_sample_rejects_different_sampling_spec():
    first = sampling_spec(seed=12345)
    second = sampling_spec(seed=12346)

    sample = EnsembleSample.from_values(
        first,
        0,
        (5.0,),
    )

    with pytest.raises(ValueError):
        sample.require_matches_spec(second)


def test_sampling_spec_is_frozen():
    item = sampling_spec()

    with pytest.raises(FrozenInstanceError):
        item.sample_count = 100


def test_sample_is_frozen():
    item = EnsembleSample.from_values(
        sampling_spec(),
        0,
        (5.0,),
    )

    with pytest.raises(FrozenInstanceError):
        item.sample_index = 1
