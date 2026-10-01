# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

from dataclasses import FrozenInstanceError, replace

import numpy as np
import pytest

from ncmemsim.ensemble import RNGSpec
from ncmemsim.hashing import canonical_hash


REFERENCE_SEED = 12345

REFERENCE_RAW_UINT64 = [
    4193609425186963869,
    5843160025838961886,
    14708796524633321433,
    12474696839993944336,
    7214697784736971533,
]


def test_rng_contract_identity():
    spec = RNGSpec(seed=REFERENCE_SEED)

    assert spec.family == "numpy.random.Generator"
    assert spec.bit_generator == "PCG64"
    assert spec.algorithm == "numpy-pcg64-v1"
    assert spec.schema_version == "ensemble-rng-v1"


@pytest.mark.parametrize(
    "seed",
    [
        0,
        1,
        2**64,
        2**128 - 1,
    ],
)
def test_valid_seed_domain(seed):
    assert RNGSpec(seed=seed).seed == seed


@pytest.mark.parametrize(
    "seed",
    [
        -1,
        2**128,
        2**128 + 1,
    ],
)
def test_invalid_seed_range(seed):
    with pytest.raises(ValueError):
        RNGSpec(seed=seed)


@pytest.mark.parametrize(
    "seed",
    [
        True,
        False,
        1.0,
        "1",
        None,
        [],
    ],
)
def test_seed_requires_integer_excluding_bool(seed):
    with pytest.raises(TypeError):
        RNGSpec(seed=seed)


@pytest.mark.parametrize(
    "field, value",
    [
        ("family", "numpy.random.default_rng"),
        ("bit_generator", "PCG64DXSM"),
        ("algorithm", "numpy-pcg64-v2"),
        ("schema_version", "ensemble-rng-v2"),
    ],
)
def test_fixed_rng_identity_cannot_be_changed(field, value):
    with pytest.raises(ValueError):
        replace(
            RNGSpec(seed=REFERENCE_SEED),
            **{field: value},
        )


def test_rng_round_trip():
    original = RNGSpec(seed=REFERENCE_SEED)

    restored = RNGSpec.from_dict(
        original.to_dict()
    )

    assert restored == original
    assert restored.to_dict() == original.to_dict()
    assert restored.definition_hash == original.definition_hash


def test_rng_hash_is_canonical():
    spec = RNGSpec(seed=REFERENCE_SEED)

    assert spec.definition_hash == canonical_hash(
        spec.to_dict()
    )

    changed = RNGSpec(seed=REFERENCE_SEED + 1)

    assert changed.definition_hash != spec.definition_hash


def test_rng_from_dict_rejects_unknown_field():
    data = RNGSpec(seed=REFERENCE_SEED).to_dict()
    data["extra"] = 1

    with pytest.raises(ValueError):
        RNGSpec.from_dict(data)


def test_rng_from_dict_rejects_missing_field():
    data = RNGSpec(seed=REFERENCE_SEED).to_dict()
    del data["algorithm"]

    with pytest.raises(ValueError):
        RNGSpec.from_dict(data)


@pytest.mark.parametrize(
    "data",
    [
        None,
        [],
        (),
        "rng",
    ],
)
def test_rng_from_dict_requires_mapping(data):
    with pytest.raises(TypeError):
        RNGSpec.from_dict(data)


def test_create_generator_returns_explicit_pcg64():
    rng = RNGSpec(
        seed=REFERENCE_SEED
    ).create_generator()

    assert isinstance(rng, np.random.Generator)
    assert isinstance(rng.bit_generator, np.random.PCG64)


def test_fixed_seed_matches_pcg64_reference_integer_stream():
    rng = RNGSpec(
        seed=REFERENCE_SEED
    ).create_generator()

    values = rng.bit_generator.random_raw(
        len(REFERENCE_RAW_UINT64)
    )

    assert values.tolist() == REFERENCE_RAW_UINT64


def test_two_generators_with_same_spec_have_same_state_stream():
    spec = RNGSpec(seed=REFERENCE_SEED)

    first = spec.create_generator()
    second = spec.create_generator()

    first_values = first.bit_generator.random_raw(16)
    second_values = second.bit_generator.random_raw(16)

    assert np.array_equal(
        first_values,
        second_values,
    )


def test_different_seed_changes_raw_stream():
    first = RNGSpec(
        seed=REFERENCE_SEED
    ).create_generator()

    second = RNGSpec(
        seed=REFERENCE_SEED + 1
    ).create_generator()

    assert not np.array_equal(
        first.bit_generator.random_raw(16),
        second.bit_generator.random_raw(16),
    )


def test_rng_spec_is_frozen():
    spec = RNGSpec(seed=REFERENCE_SEED)

    with pytest.raises(FrozenInstanceError):
        spec.seed = 1
