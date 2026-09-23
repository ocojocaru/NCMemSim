from dataclasses import FrozenInstanceError, replace

import pytest

from ncmemsim import DeviceBuilder
from ncmemsim.dtco import BindingScope, ParameterBinding
from ncmemsim.ensemble import (
    ConstantDistribution,
    EnsembleSpec,
    NormalDistribution,
    PhysicalDomain,
    StochasticVariable,
)
from ncmemsim.hashing import canonical_hash
from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)
from ncmemsim.program_protocol import ProgramPulseReadProtocol


def provenance():
    return ParameterProvenance(
        source="Assumed Phase K specification test",
        status=ParameterStatus.ASSUMED,
    )


def device():
    return DeviceBuilder.v2(
        n_fgs=1,
        control_sio2_nm=20,
        fg_thickness_nm=12,
        tunnel_sio2_nm=8,
        nc_diameter_nm=5,
        nc_volume_fraction=0.6,
        active_fraction=0.22,
    )


def diameter_variable(name="diameter"):
    return StochasticVariable(
        name=name,
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


def fraction_variable(name="active_fraction"):
    return StochasticVariable(
        name=name,
        binding=ParameterBinding(
            BindingScope.DEVICE,
            (
                "layers",
                "FG1",
                "electrically_active_fraction",
            ),
        ),
        distribution=NormalDistribution(
            mean=0.22,
            standard_deviation=0.02,
        ),
        unit="1",
        physical_domain=PhysicalDomain(
            lower=0.0,
            upper=1.0,
        ),
        provenance=provenance(),
        applicability="Reference electrically active NC fraction",
        nominal_value=0.22,
        nominal_value_source="reference device",
    )


def operating_variable():
    return StochasticVariable(
        name="program_time",
        binding=ParameterBinding(
            BindingScope.OPERATING,
            ("program", "time_s"),
        ),
        distribution=ConstantDistribution(1e-6),
        unit="s",
        physical_domain=PhysicalDomain(
            lower=0.0,
            lower_inclusive=False,
        ),
        provenance=provenance(),
        applicability="Program-pulse duration",
        nominal_value=1e-6,
        nominal_value_source="reference protocol",
    )


def specification(variables=None):
    return EnsembleSpec.from_device(
        name="phase-k-test",
        device=device(),
        variables=variables
        or (diameter_variable(), fraction_variable()),
        description="Phase K ensemble specification test",
    )


def test_from_device_builds_stable_identity():
    first = specification()
    second = specification()

    assert first.base_device_hash == second.base_device_hash
    assert first.definition_hash == second.definition_hash
    assert first.definition_hash == canonical_hash(first.to_dict())


def test_variable_order_is_explicit_and_identity_significant():
    diameter = diameter_variable()
    fraction = fraction_variable()

    first = specification((diameter, fraction))
    second = specification((fraction, diameter))

    assert first.variable_names == (
        "diameter",
        "active_fraction",
    )
    assert second.variable_names == (
        "active_fraction",
        "diameter",
    )

    assert first.definition_hash != second.definition_hash


def test_variables_are_normalized_to_tuple():
    item = EnsembleSpec.from_device(
        name="ensemble",
        device=device(),
        variables=[diameter_variable()],
    )

    assert isinstance(item.variables, tuple)


def test_requires_at_least_one_variable():
    with pytest.raises(ValueError):
        EnsembleSpec.from_device(
            name="ensemble",
            device=device(),
            variables=(),
        )


def test_duplicate_variable_names_are_rejected():
    with pytest.raises(ValueError):
        specification(
            (
                diameter_variable("same"),
                fraction_variable("same"),
            )
        )


def test_duplicate_bindings_are_rejected():
    first = diameter_variable("first")
    second = replace(
        first,
        name="second",
        distribution=NormalDistribution(
            mean=5.0,
            standard_deviation=1.0,
        ),
    )

    with pytest.raises(ValueError):
        specification((first, second))


def test_non_stochastic_variable_is_rejected():
    with pytest.raises(TypeError):
        EnsembleSpec(
            name="ensemble",
            base_device_hash="0" * 64,
            variables=(object(),),
        )


@pytest.mark.parametrize(
    "base_hash",
    [
        "",
        "abc",
        "0" * 63,
        "0" * 65,
        "G" * 64,
        "A" * 64,
    ],
)
def test_invalid_device_hash_is_rejected(base_hash):
    with pytest.raises(ValueError):
        EnsembleSpec(
            name="ensemble",
            base_device_hash=base_hash,
            variables=(diameter_variable(),),
        )


@pytest.mark.parametrize(
    "field, value",
    [
        ("name", ""),
        ("name", " ensemble"),
        ("base_device_name", ""),
        ("base_device_name", "device "),
        ("description", ""),
        ("description", " text"),
    ],
)
def test_text_contracts(field, value):
    item = specification()

    with pytest.raises(ValueError):
        replace(item, **{field: value})


def test_schema_version_is_fixed():
    with pytest.raises(ValueError):
        replace(
            specification(),
            schema_version="ensemble-spec-v2",
        )


def test_matches_nominal_device():
    nominal = device()
    item = EnsembleSpec.from_device(
        name="ensemble",
        device=nominal,
        variables=(diameter_variable(),),
    )

    assert item.matches_device(nominal)
    item.require_matching_device(nominal)


def test_different_device_does_not_match():
    item = specification()

    different = DeviceBuilder.v2(
        n_fgs=1,
        control_sio2_nm=20,
        fg_thickness_nm=12,
        tunnel_sio2_nm=8,
        nc_diameter_nm=6,
        nc_volume_fraction=0.6,
        active_fraction=0.22,
    )

    assert not item.matches_device(different)

    with pytest.raises(ValueError):
        item.require_matching_device(different)


def test_operating_variable_requires_operating_baseline():
    with pytest.raises(ValueError):
        EnsembleSpec.from_device(
            name="ensemble",
            device=device(),
            variables=(operating_variable(),),
        )


def test_operating_baseline_identity():
    protocol = ProgramPulseReadProtocol(
        program_voltage_V=5.0,
        programming_time_s=1e-6,
    )

    item = EnsembleSpec.from_device(
        name="ensemble",
        device=device(),
        variables=(operating_variable(),),
        operating_protocol=protocol,
    )

    assert item.base_operating_hash is not None
    assert item.base_operating_kind == "program_pulse_read"
    assert item.matches_operating(protocol)
    item.require_matching_operating(protocol)


def test_different_operating_protocol_does_not_match():
    protocol = ProgramPulseReadProtocol(
        program_voltage_V=5.0,
        programming_time_s=1e-6,
    )

    item = EnsembleSpec.from_device(
        name="ensemble",
        device=device(),
        variables=(operating_variable(),),
        operating_protocol=protocol,
    )

    different = ProgramPulseReadProtocol(
        program_voltage_V=6.0,
        programming_time_s=1e-6,
    )

    assert not item.matches_operating(different)

    with pytest.raises(ValueError):
        item.require_matching_operating(different)


def test_no_operating_identity_returns_false():
    item = specification()

    protocol = ProgramPulseReadProtocol(
        program_voltage_V=5.0,
        programming_time_s=1e-6,
    )

    assert not item.matches_operating(protocol)

    with pytest.raises(ValueError):
        item.require_matching_operating(protocol)


def test_partial_operating_identity_is_rejected():
    item = specification()

    with pytest.raises(ValueError):
        replace(
            item,
            base_operating_hash="0" * 64,
            base_operating_kind=None,
        )

    with pytest.raises(ValueError):
        replace(
            item,
            base_operating_hash=None,
            base_operating_kind="program_pulse_read",
        )


def test_invalid_operating_hash_is_rejected():
    item = specification()

    with pytest.raises(ValueError):
        replace(
            item,
            base_operating_hash="bad",
            base_operating_kind="program_pulse_read",
        )


def test_serialization_preserves_variable_order():
    item = specification()

    data = item.to_dict()

    assert [
        variable["name"]
        for variable in data["variables"]
    ] == [
        "diameter",
        "active_fraction",
    ]


def test_definition_is_frozen():
    item = specification()

    with pytest.raises(FrozenInstanceError):
        item.name = "changed"


def test_description_changes_identity():
    item = specification()

    changed = replace(
        item,
        description="Different scientific description",
    )

    assert changed.definition_hash != item.definition_hash
