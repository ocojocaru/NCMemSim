from __future__ import annotations

import pytest

from ncmemsim.dtco import (
    BindingScope, DesignVariable, DesignVariableRole, ParameterBinding,
)
from ncmemsim.hashing import canonical_hash


CONTRACTS = [
    (BindingScope.DEVICE, ("gate_work_function_eV",), "eV"),
    (BindingScope.DEVICE, ("substrate_doping_m3",), "m^-3"),
    (BindingScope.DEVICE, ("temperature_K",), "K"),
    *[
        (BindingScope.DEVICE, ("layers", layer, attr), unit)
        for layer in ("FG1", "another_layer")
        for attr, unit in (
            ("thickness_nm", "nm"), ("nc_diameter_nm", "nm"),
            ("nc_volume_fraction", "1"), ("electrically_active_fraction", "1"),
            ("grid_points", "1"),
        )
    ],
    (BindingScope.DEVICE, ("layers", "FG1", "nc_material", "sn_fraction"), "1"),
    (BindingScope.OPERATING, ("program", "voltage_V"), "V"),
    (BindingScope.OPERATING, ("program", "time_s"), "s"),
    (BindingScope.OPERATING, ("program", "internal_dt_s"), "s"),
    (BindingScope.OPERATING, ("read", "voltage_V"), "V"),
    (BindingScope.OPERATING, ("optical", "wavelength_nm"), "nm"),
    (BindingScope.OPERATING, ("optical", "power_density_W_m2"), "W/m^2"),
]


def variable(scope, path, unit, values=(1, 2)):
    return DesignVariable(
        name="test_variable", binding=ParameterBinding(scope, path),
        values=values, role=DesignVariableRole.MODEL, unit=unit,
    )


@pytest.mark.parametrize("scope,path,unit", CONTRACTS)
def test_known_contract_accepts_canonical_unit_and_preserves_identity(scope, path, unit):
    v = variable(scope, path, unit)
    payload = {
        "name": "test_variable",
        "binding": {"scope": scope.value, "path": list(path)},
        "values": [1, 2], "role": "model", "unit": unit,
    }
    assert v.to_dict() == payload
    assert v.definition_hash == canonical_hash(payload)
    assert v.values == (1, 2)


@pytest.mark.parametrize("scope,path,unit", CONTRACTS)
@pytest.mark.parametrize("bad_unit", [None, "", "wrong", " nm", "nm ", "NM"])
def test_known_contract_rejects_noncanonical_units(scope, path, unit, bad_unit):
    with pytest.raises(ValueError, match="canonical unit"):
        variable(scope, path, bad_unit)


@pytest.mark.parametrize("scope,path,unit", CONTRACTS)
def test_known_numeric_binding_rejects_categories_at_construction(scope, path, unit):
    with pytest.raises(TypeError, match="requires numeric"):
        variable(scope, path, None, ("low", "high"))


@pytest.mark.parametrize("value", [" low", "low ", "\tlow", "low\n", "\u00a0low"])
def test_categories_reject_outer_whitespace(value):
    with pytest.raises(ValueError, match="outer whitespace"):
        variable(BindingScope.MODEL, ("category",), None, (value,))


def test_categories_preserve_internal_whitespace():
    assert variable(
        BindingScope.MODEL, ("category",), None, ("low power", "high power")
    ).values == ("low power", "high power")


@pytest.mark.parametrize("scope,path,unit", CONTRACTS)
def test_model_scope_has_no_binding_unit_or_numeric_contract(scope, path, unit):
    assert variable(BindingScope.MODEL, path, "custom").unit == "custom"
    assert not variable(BindingScope.MODEL, path, None, ("low", "high")).is_numeric


@pytest.mark.parametrize("scope,path", [
    (BindingScope.DEVICE, ("unknown",)),
    (BindingScope.DEVICE, ("temperature_K", "nested")),
    (BindingScope.DEVICE, ("other", "FG1", "thickness_nm")),
    (BindingScope.DEVICE, ("layers", "FG1", "nc_material", "bandgap_eV")),
    (BindingScope.OPERATING, ("voltage_V",)),
    (BindingScope.OPERATING, ("program", "unknown")),
])
def test_unknown_paths_remain_declarative(scope, path):
    assert variable(scope, path, "custom").unit == "custom"
    assert not variable(scope, path, None, ("low", "high")).is_numeric
