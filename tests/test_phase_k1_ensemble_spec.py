from dataclasses import FrozenInstanceError, replace
import math

import pytest

from ncmemsim.dtco import BindingScope, ParameterBinding
from ncmemsim.ensemble import (
    ConstantDistribution,
    NormalDistribution,
    PhysicalDomain,
    StochasticVariable,
)
from ncmemsim.hashing import canonical_hash
from ncmemsim.materials.provenance import (
    ParameterProvenance,
    ParameterStatus,
)


def provenance():
    return ParameterProvenance(
        source="Assumed Phase K test distribution",
        status=ParameterStatus.ASSUMED,
    )


def diameter_variable(
    distribution=None,
    domain=None,
    unit="nm",
    nominal_value=5.0,
):
    return StochasticVariable(
        name="nc_diameter",
        binding=ParameterBinding(
            BindingScope.DEVICE,
            ("layers", "FG1", "nc_diameter_nm"),
        ),
        distribution=distribution or NormalDistribution(5.0, 0.5),
        unit=unit,
        physical_domain=domain
        or PhysicalDomain(lower=0.0, lower_inclusive=False),
        provenance=provenance(),
        applicability="Reference floating-gate nanocrystal diameter",
        nominal_value=nominal_value,
        nominal_value_source="reference device",
    )


def test_physical_domain_contains_contract():
    closed = PhysicalDomain(lower=0.0, upper=1.0)

    assert closed.contains(0.0)
    assert closed.contains(0.5)
    assert closed.contains(1.0)
    assert not closed.contains(-0.1)
    assert not closed.contains(1.1)

    open_domain = PhysicalDomain(
        lower=0.0,
        upper=1.0,
        lower_inclusive=False,
        upper_inclusive=False,
    )

    assert not open_domain.contains(0.0)
    assert open_domain.contains(0.5)
    assert not open_domain.contains(1.0)


@pytest.mark.parametrize(
    "lower, upper",
    [
        (1.0, 1.0),
        (2.0, 1.0),
        (math.nan, 1.0),
        (0.0, math.inf),
    ],
)
def test_invalid_physical_domains(lower, upper):
    with pytest.raises(ValueError):
        PhysicalDomain(lower=lower, upper=upper)


@pytest.mark.parametrize("value", ["yes", 1, 0, None])
def test_domain_inclusivity_flags_must_be_bool(value):
    with pytest.raises(TypeError):
        PhysicalDomain(
            lower=0.0,
            upper=1.0,
            lower_inclusive=value,
        )


def test_variable_uses_existing_binding_unit():
    item = diameter_variable()

    assert item.unit == "nm"

    with pytest.raises(ValueError):
        diameter_variable(unit="m")


@pytest.mark.parametrize(
    "scope, path, unit, domain",
    [
        (
            BindingScope.DEVICE,
            ("temperature_K",),
            "K",
            PhysicalDomain(lower=0.0, lower_inclusive=False),
        ),
        (
            BindingScope.DEVICE,
            ("substrate_doping_m3",),
            "m^-3",
            PhysicalDomain(lower=0.0, lower_inclusive=False),
        ),
        (
            BindingScope.DEVICE,
            ("layers", "FG1", "nc_volume_fraction"),
            "1",
            PhysicalDomain(lower=0.0, upper=1.0),
        ),
        (
            BindingScope.DEVICE,
            ("layers", "FG1", "electrically_active_fraction"),
            "1",
            PhysicalDomain(lower=0.0, upper=1.0),
        ),
        (
            BindingScope.DEVICE,
            ("layers", "FG1", "nc_material", "sn_fraction"),
            "1",
            PhysicalDomain(lower=0.0, upper=1.0),
        ),
        (
            BindingScope.OPERATING,
            ("program", "voltage_V"),
            "V",
            PhysicalDomain(),
        ),
        (
            BindingScope.OPERATING,
            ("program", "time_s"),
            "s",
            PhysicalDomain(lower=0.0, lower_inclusive=False),
        ),
        (
            BindingScope.OPERATING,
            ("optical", "wavelength_nm"),
            "nm",
            PhysicalDomain(lower=0.0, lower_inclusive=False),
        ),
    ],
)
def test_supported_binding_contracts(scope, path, unit, domain):
    item = StochasticVariable(
        name="variable",
        binding=ParameterBinding(scope, path),
        distribution=ConstantDistribution(1.0),
        unit=unit,
        physical_domain=domain,
        provenance=provenance(),
        applicability="Phase K contract test",
        nominal_value=None,
    )

    assert item.unit == unit


@pytest.mark.parametrize(
    "domain",
    [
        PhysicalDomain(),
        PhysicalDomain(lower=-1.0, upper=1.0),
        PhysicalDomain(lower=0.0),
    ],
)
def test_positive_bindings_require_positive_physical_domain(domain):
    with pytest.raises(ValueError):
        diameter_variable(
            domain=domain,
            nominal_value=None,
        )


@pytest.mark.parametrize(
    "domain",
    [
        PhysicalDomain(lower=-0.1, upper=1.0),
        PhysicalDomain(lower=0.0, upper=1.1),
        PhysicalDomain(lower=0.0),
        PhysicalDomain(upper=1.0),
    ],
)
def test_fraction_domain_must_be_bounded_inside_unit_interval(domain):
    with pytest.raises(ValueError):
        StochasticVariable(
            name="fraction",
            binding=ParameterBinding(
                BindingScope.DEVICE,
                ("layers", "FG1", "nc_volume_fraction"),
            ),
            distribution=NormalDistribution(0.5, 0.1),
            unit="1",
            physical_domain=domain,
            provenance=provenance(),
            applicability="Phase K fraction test",
            nominal_value=0.5,
        )


def test_distribution_support_is_separate_from_physical_domain():
    item = diameter_variable(
        distribution=NormalDistribution(
            mean=1.0,
            standard_deviation=100.0,
        )
    )

    assert not item.physical_domain.contains(-1.0)


def test_even_constant_outside_domain_is_not_silently_rejected_or_repaired():
    item = diameter_variable(
        distribution=ConstantDistribution(-1.0)
    )

    assert item.distribution.value == -1.0
    assert not item.physical_domain.contains(item.distribution.value)


def test_nominal_value_must_be_inside_physical_domain():
    with pytest.raises(ValueError):
        diameter_variable(nominal_value=0.0)


def test_context_nominal_value_may_be_deferred():
    item = diameter_variable(nominal_value=None)

    assert item.nominal_value is None
    assert item.nominal_value_source == "reference device"


@pytest.mark.parametrize(
    "scope, path",
    [
        (BindingScope.MODEL, ("trap_density_m3",)),
        (BindingScope.DEVICE, ("unknown",)),
        (BindingScope.OPERATING, ("unknown",)),
        (
            BindingScope.DEVICE,
            ("layers", "FG1", "grid_points"),
        ),
    ],
)
def test_unsupported_bindings_are_rejected(scope, path):
    with pytest.raises(ValueError):
        StochasticVariable(
            name="variable",
            binding=ParameterBinding(scope, path),
            distribution=ConstantDistribution(1.0),
            unit="1",
            physical_domain=PhysicalDomain(),
            provenance=provenance(),
            applicability="Phase K contract test",
        )


@pytest.mark.parametrize(
    "field, value",
    [
        ("name", ""),
        ("name", " variable"),
        ("applicability", ""),
        ("applicability", "scope "),
        ("nominal_value_source", ""),
    ],
)
def test_text_contracts(field, value):
    item = diameter_variable()
    with pytest.raises(ValueError):
        replace(item, **{field: value})


def test_provenance_contract():
    with pytest.raises(TypeError):
        replace(diameter_variable(), provenance=None)

    invalid = ParameterProvenance(
        source="test",
        status="assumed",
    )

    with pytest.raises(TypeError):
        replace(diameter_variable(), provenance=invalid)


def test_serialization_hash_and_immutability():
    item = diameter_variable()

    assert item.definition_hash == canonical_hash(item.to_dict())

    equivalent = diameter_variable(
        distribution=NormalDistribution(5, 0.5),
        nominal_value=5,
    )
    assert equivalent.definition_hash == item.definition_hash

    changed = replace(
        item,
        applicability="Different applicability",
    )
    assert changed.definition_hash != item.definition_hash

    with pytest.raises(FrozenInstanceError):
        item.unit = "m"


def test_physical_domain_serialization_is_stable():
    domain = PhysicalDomain(
        lower=0,
        upper=1,
        lower_inclusive=True,
        upper_inclusive=False,
    )

    assert domain.to_dict() == {
        "lower": 0.0,
        "upper": 1.0,
        "lower_inclusive": True,
        "upper_inclusive": False,
    }
    assert domain.definition_hash == canonical_hash(domain.to_dict())
