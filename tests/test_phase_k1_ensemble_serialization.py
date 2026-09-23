import json

import pytest

from ncmemsim.dtco import BindingScope, ParameterBinding
from ncmemsim.ensemble import (
    EnsembleSpec,
    NormalDistribution,
    PhysicalDomain,
    StochasticVariable,
)
from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)


def provenance():
    return ParameterProvenance(
        source="Phase K round-trip test",
        status=ParameterStatus.ASSUMED,
        doi="10.0000/example",
        notes="Serialization reference",
        parameter_set="phase-k-test",
        reported_uncertainty=0.1,
        uncertainty_unit="nm",
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
        applicability="Reference nanocrystal diameter",
        nominal_value=5.0,
        nominal_value_source="reference device",
    )


def ensemble():
    return EnsembleSpec(
        name="phase-k-round-trip",
        base_device_hash="0" * 64,
        base_device_name="reference-device",
        description="Strict serialization test",
        variables=(variable(),),
    )


def test_physical_domain_round_trip():
    original = PhysicalDomain(
        lower=0.0,
        upper=1.0,
        lower_inclusive=False,
        upper_inclusive=True,
    )

    restored = PhysicalDomain.from_dict(
        original.to_dict()
    )

    assert restored == original
    assert restored.to_dict() == original.to_dict()
    assert restored.definition_hash == original.definition_hash


def test_stochastic_variable_round_trip():
    original = variable()

    restored = StochasticVariable.from_dict(
        original.to_dict()
    )

    assert restored == original
    assert restored.to_dict() == original.to_dict()
    assert restored.definition_hash == original.definition_hash
    assert restored.binding.binding_id == original.binding.binding_id


def test_ensemble_round_trip():
    original = ensemble()

    restored = EnsembleSpec.from_dict(
        original.to_dict()
    )

    assert restored == original
    assert restored.to_dict() == original.to_dict()
    assert restored.definition_hash == original.definition_hash
    assert restored.variable_names == original.variable_names


def test_full_json_round_trip():
    original = ensemble()

    payload = json.loads(
        json.dumps(original.to_dict())
    )

    restored = EnsembleSpec.from_dict(payload)

    assert restored.to_dict() == original.to_dict()
    assert restored.definition_hash == original.definition_hash


def test_provenance_round_trip_preserves_uncertainty():
    restored = StochasticVariable.from_dict(
        variable().to_dict()
    )

    assert restored.provenance == provenance()
    assert restored.provenance.reported_uncertainty == 0.1
    assert restored.provenance.uncertainty_unit == "nm"


def test_provenance_without_uncertainty_round_trip():
    original = StochasticVariable(
        name="diameter",
        binding=ParameterBinding(
            BindingScope.DEVICE,
            ("layers", "FG1", "nc_diameter_nm"),
        ),
        distribution=NormalDistribution(5.0, 0.5),
        unit="nm",
        physical_domain=PhysicalDomain(
            lower=0.0,
            lower_inclusive=False,
        ),
        provenance=ParameterProvenance(
            source="No uncertainty",
            status=ParameterStatus.ASSUMED,
        ),
        applicability="Reference diameter",
        nominal_value=5.0,
    )

    data = original.to_dict()

    assert "reported_uncertainty" not in data["provenance"]
    assert "uncertainty_unit" not in data["provenance"]

    restored = StochasticVariable.from_dict(data)

    assert restored.to_dict() == data


@pytest.mark.parametrize(
    "data",
    [
        {
            "lower": 0.0,
            "upper": 1.0,
            "lower_inclusive": True,
        },
        {
            "lower": 0.0,
            "upper": 1.0,
            "lower_inclusive": True,
            "upper_inclusive": True,
            "extra": 1,
        },
    ],
)
def test_physical_domain_strict_fields(data):
    with pytest.raises(ValueError):
        PhysicalDomain.from_dict(data)


def test_binding_unknown_field_is_rejected():
    data = variable().to_dict()
    data["binding"]["extra"] = 1

    with pytest.raises(ValueError):
        StochasticVariable.from_dict(data)


def test_binding_missing_field_is_rejected():
    data = variable().to_dict()
    del data["binding"]["path"]

    with pytest.raises(ValueError):
        StochasticVariable.from_dict(data)


def test_binding_scope_must_be_known():
    data = variable().to_dict()
    data["binding"]["scope"] = "magic"

    with pytest.raises(ValueError):
        StochasticVariable.from_dict(data)


def test_binding_scope_must_be_text():
    data = variable().to_dict()
    data["binding"]["scope"] = 1

    with pytest.raises(TypeError):
        StochasticVariable.from_dict(data)


def test_binding_path_requires_json_list():
    data = variable().to_dict()
    data["binding"]["path"] = tuple(
        data["binding"]["path"]
    )

    with pytest.raises(TypeError):
        StochasticVariable.from_dict(data)


def test_provenance_unknown_field_is_rejected():
    data = variable().to_dict()
    data["provenance"]["extra"] = 1

    with pytest.raises(ValueError):
        StochasticVariable.from_dict(data)


def test_provenance_missing_base_field_is_rejected():
    data = variable().to_dict()
    del data["provenance"]["parameter_set"]

    with pytest.raises(ValueError):
        StochasticVariable.from_dict(data)


def test_provenance_status_must_be_known():
    data = variable().to_dict()
    data["provenance"]["status"] = "magic"

    with pytest.raises(ValueError):
        StochasticVariable.from_dict(data)


def test_stochastic_variable_unknown_field_is_rejected():
    data = variable().to_dict()
    data["extra"] = 1

    with pytest.raises(ValueError):
        StochasticVariable.from_dict(data)


def test_stochastic_variable_missing_field_is_rejected():
    data = variable().to_dict()
    del data["unit"]

    with pytest.raises(ValueError):
        StochasticVariable.from_dict(data)


def test_stochastic_variable_schema_is_strict():
    data = variable().to_dict()
    data["schema_version"] = "ensemble-variable-v2"

    with pytest.raises(ValueError):
        StochasticVariable.from_dict(data)


def test_ensemble_unknown_field_is_rejected():
    data = ensemble().to_dict()
    data["extra"] = 1

    with pytest.raises(ValueError):
        EnsembleSpec.from_dict(data)


def test_ensemble_missing_field_is_rejected():
    data = ensemble().to_dict()
    del data["base_device_hash"]

    with pytest.raises(ValueError):
        EnsembleSpec.from_dict(data)


def test_ensemble_variables_require_json_list():
    data = ensemble().to_dict()
    data["variables"] = tuple(data["variables"])

    with pytest.raises(TypeError):
        EnsembleSpec.from_dict(data)


def test_ensemble_schema_is_strict():
    data = ensemble().to_dict()
    data["schema_version"] = "ensemble-spec-v2"

    with pytest.raises(ValueError):
        EnsembleSpec.from_dict(data)


def test_nested_distribution_error_propagates():
    data = ensemble().to_dict()
    data["variables"][0]["distribution"]["family"] = "magic"

    with pytest.raises(ValueError):
        EnsembleSpec.from_dict(data)


def test_operating_identity_round_trip():
    original = EnsembleSpec(
        name="operating-identity",
        base_device_hash="0" * 64,
        base_device_name="reference-device",
        variables=(variable(),),
        base_operating_hash="1" * 64,
        base_operating_kind="program_pulse_read",
    )

    restored = EnsembleSpec.from_dict(
        original.to_dict()
    )

    assert restored == original
    assert restored.definition_hash == original.definition_hash


def test_partial_operating_identity_remains_invalid():
    data = ensemble().to_dict()
    data["base_operating_hash"] = "1" * 64

    with pytest.raises(ValueError):
        EnsembleSpec.from_dict(data)


def test_from_dict_does_not_mutate_input():
    data = ensemble().to_dict()

    snapshot = json.loads(json.dumps(data))

    EnsembleSpec.from_dict(data)

    assert data == snapshot
