# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Portable archive roundoff checks preserve bytes and reject material drift."""
from copy import deepcopy
from decimal import Decimal,localcontext
from pathlib import Path
import json,math
import pytest
from ncmemsim.spectral_absorption import SpectralAbsorptionResult,_projection_roundoff_equal
from ncmemsim.spectral_stack import SpectralStackResult
from ncmemsim.om2_reporting import OM2NumericalReport
ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def archived():
    return json.loads((ROOT/'tests/fixtures/archives/v1_7_preparation/om2_report.json').read_text(encoding='utf-8'))


def alternate_expm1(x):
    with localcontext() as ctx:
        ctx.prec=80
        return float(Decimal.from_float(x).exp()-1)


def test_cross_libm_stack_and_single_layer_preserve_exact_archive(archived,monkeypatch):
    stack=archived['study']['results']['dt']['experiment']['device_photo']['spectral_context']['optical_result']
    layer=stack['projection']['layers'][1]['absorption']
    monkeypatch.setattr(math,'expm1',alternate_expm1)
    restored=SpectralStackResult.from_dict(stack)
    assert restored.to_dict()==stack
    assert SpectralAbsorptionResult.from_dict(layer).to_dict()==layer
    # Returned projections cannot mutate the frozen archived observation string.
    projection=restored.projection;projection['summary']['absorbed_irradiance_W_m2']=999
    assert restored.to_dict()==stack


def test_frozen_p7_report_preserves_hash_under_alternate_libm(archived,monkeypatch):
    monkeypatch.setattr(math,'expm1',alternate_expm1)
    report=OM2NumericalReport.from_dict(archived)
    assert report.to_dict()==archived
    assert report.contract_hash=='062e453cc977cec48114bc17ac3a27f58ee3f6996370d1aa6e36ac9dcad7065f'


@pytest.mark.parametrize('fault',['derived','profile','wavelength','evidence','schema','extra','nan'])
def test_meaningful_or_input_tampering_still_rejected(archived,fault):
    stack=deepcopy(archived['study']['results']['dt']['experiment']['device_photo']['spectral_context']['optical_result'])
    if fault=='derived':stack['projection']['summary']['absorbed_irradiance_W_m2']*=1.000001
    if fault=='profile':stack['projection']['layers'][1]['absorption']['profile']['effective_alpha_m_inv'][0]=math.nextafter(stack['path']['layers'][1]['profile']['effective_alpha_m_inv'][0],math.inf)
    if fault=='wavelength':stack['projection']['layers'][1]['absorption']['source']['wavelength_nm'][0]=math.nextafter(1550.,math.inf)
    if fault=='evidence':stack['projection']['layers'][1]['absorption']['source']['evidence']['source']='forged'
    if fault=='schema':stack['schema_version']='unknown'
    if fault=='extra':stack['projection']['extra']=True
    if fault=='nan':stack['projection']['summary']['absorbed_irradiance_W_m2']=float('nan')
    with pytest.raises(ValueError):SpectralStackResult.from_dict(stack)


def test_ulp_limit_is_narrow_and_cancellation_scaled_to_incident():
    x=600.;inside=x;outside=x
    for _ in range(16):inside=math.nextafter(inside,math.inf)
    for _ in range(17):outside=math.nextafter(outside,math.inf)
    assert _projection_roundoff_equal({'a':inside},{'a':x})
    assert not _projection_roundoff_equal({'a':outside},{'a':x})
    assert _projection_roundoff_equal({'incident_irradiance_W_m2':1e6,'power_balance_residual_W_m2':math.ulp(1e6)},
        {'incident_irradiance_W_m2':1e6,'power_balance_residual_W_m2':0.})
    assert not _projection_roundoff_equal({'incident_irradiance_W_m2':1e6,'power_balance_residual_W_m2':1.},
        {'incident_irradiance_W_m2':1e6,'power_balance_residual_W_m2':0.})
