import copy
import json

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
    SampleManifest,
    SamplingSpec,
    StochasticVariable,
    UniformDistribution,
    generate_sample_manifest,
)
from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)


def provenance():
    return ParameterProvenance(
        source="Phase K manifest serialization test",
        status=ParameterStatus.ASSUMED,
    )


def manifest():
    variables = (
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

    ensemble = EnsembleSpec(
        name="manifest-serialization-test",
        base_device_hash="0" * 64,
        variables=variables,
    )

    spec = SamplingSpec(
        ensemble_spec=ensemble,
        rng=RNGSpec(seed=12345),
        sample_count=4,
    )

    return generate_sample_manifest(spec)


def test_manifest_dict_round_trip():
    original = manifest()

    restored = SampleManifest.from_dict(
        original.to_dict()
    )

    assert restored == original
    assert restored.to_dict() == original.to_dict()
    assert (
        restored.sample_table_hash
        == original.sample_table_hash
    )
    assert restored.manifest_hash == original.manifest_hash


def test_manifest_json_round_trip():
    original = manifest()

    restored = SampleManifest.from_json(
        original.to_json()
    )

    assert restored.to_dict() == original.to_dict()
    assert restored.manifest_hash == original.manifest_hash


def test_manifest_json_is_deterministic():
    original = manifest()

    assert original.to_json() == original.to_json()

    assert original.to_json() == json.dumps(
        original.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def test_pretty_json_with_different_key_order_is_accepted():
    original = manifest()

    text = json.dumps(
        original.to_dict(),
        indent=2,
        sort_keys=False,
    )

    restored = SampleManifest.from_json(text)

    assert restored.to_dict() == original.to_dict()


def test_manifest_from_dict_does_not_mutate_input():
    data = manifest().to_dict()
    before = copy.deepcopy(data)

    SampleManifest.from_dict(data)

    assert data == before


def test_unknown_manifest_field_is_rejected():
    data = manifest().to_dict()
    data["extra"] = "not allowed"

    with pytest.raises(ValueError):
        SampleManifest.from_dict(data)


def test_missing_manifest_field_is_rejected():
    data = manifest().to_dict()
    del data["sample_table_hash"]

    with pytest.raises(ValueError):
        SampleManifest.from_dict(data)


def test_sampling_spec_hash_tampering_is_detected():
    data = manifest().to_dict()
    data["sampling_spec_hash"] = "1" * 64

    with pytest.raises(ValueError):
        SampleManifest.from_dict(data)


def test_sample_value_tampering_is_detected():
    data = manifest().to_dict()
    data["samples"][0]["values"][0] += 1.0

    with pytest.raises(ValueError):
        SampleManifest.from_dict(data)


def test_sample_table_hash_tampering_is_detected():
    data = manifest().to_dict()
    data["sample_table_hash"] = "2" * 64

    with pytest.raises(ValueError):
        SampleManifest.from_dict(data)


def test_manifest_hash_tampering_is_detected():
    data = manifest().to_dict()
    data["manifest_hash"] = "3" * 64

    with pytest.raises(ValueError):
        SampleManifest.from_dict(data)


def test_runtime_unknown_field_is_rejected():
    data = manifest().to_dict()
    data["runtime"]["extra"] = "not allowed"

    with pytest.raises(ValueError):
        SampleManifest.from_dict(data)


def test_runtime_missing_field_is_rejected():
    data = manifest().to_dict()
    del data["runtime"]["numpy"]

    with pytest.raises(ValueError):
        SampleManifest.from_dict(data)


def test_samples_must_be_json_list():
    data = manifest().to_dict()
    data["samples"] = tuple(data["samples"])

    with pytest.raises(TypeError):
        SampleManifest.from_dict(data)


def test_json_duplicate_key_is_rejected():
    text = manifest().to_json()

    duplicate = (
        text[:-1]
        + ',"manifest_hash":"'
        + ("0" * 64)
        + '"}'
    )

    with pytest.raises(ValueError):
        SampleManifest.from_json(duplicate)


@pytest.mark.parametrize(
    "constant",
    [
        "NaN",
        "Infinity",
        "-Infinity",
    ],
)
def test_nonfinite_json_constant_is_rejected(constant):
    text = manifest().to_json()

    altered = text.replace(
        '"sample_count":4',
        f'"sample_count":{constant}',
        1,
    )

    with pytest.raises(ValueError):
        SampleManifest.from_json(altered)


@pytest.mark.parametrize(
    "text",
    [
        "[]",
        '"manifest"',
        "42",
        "null",
    ],
)
def test_json_root_must_be_object(text):
    with pytest.raises(TypeError):
        SampleManifest.from_json(text)


@pytest.mark.parametrize(
    "text",
    [
        None,
        1,
        [],
        {},
    ],
)
def test_from_json_requires_text(text):
    with pytest.raises(TypeError):
        SampleManifest.from_json(text)
