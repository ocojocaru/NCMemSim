import importlib.util
from pathlib import Path
import numpy as np
import pytest
from ncmemsim import make_v53_reference_device,PhysicsModel,Simulator,SimulationConfig,DeviceState
from pathlib import Path
from dataclasses import replace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEGACY_PATH = (
    PROJECT_ROOT
    / "validation"
    / "legacy"
    / "unified_nc_memory_model_v5p3_trapezoidal_wkb.py"
)
if not LEGACY_PATH.is_file():
    raise FileNotFoundError(
        f"Legacy regression reference not found: {LEGACY_PATH}"
    )

spec=importlib.util.spec_from_file_location('legacy_v53',LEGACY_PATH); legacy=importlib.util.module_from_spec(spec); spec.loader.exec_module(legacy)

def setup_model(nx=7):
    device=make_v53_reference_device(grid_points=nx)
    physics=PhysicsModel.default()
    
    # V5.3 regression parameters
    physics.occupancy.config = replace(
        physics.occupancy.config,
        nu0_Hz=5.0e12,
    )

    physics.tunneling.config = replace(
        physics.tunneling.config,
        field_coupling_factor=1.0,
        activation_beta_V_inv=2.5,
    )
    
    fg = device.floating_gates()[0]

    fg.nc_material = replace(
        fg.nc_material,
        phi_barrier_prog_eV=1.85,
        phi_barrier_erase_eV=2.15,
    )

    sim=Simulator(device,physics,SimulationConfig(dwell_time_s=2e-5,internal_dt_s=1e-5))
    return device,physics,sim

def test_equivalent_capacitance_and_flatband_match_v53():
    device,physics,_=setup_model()
    assert physics.electrostatics.equivalent_capacitance(device)==pytest.approx(legacy.equivalent_oxide_capacitance(),rel=1e-13)
    assert physics.electrostatics.flatband_zero(device)==pytest.approx(legacy.V_FB0(),rel=1e-13)

def test_charging_energy_matches_v53():
    _,physics,_=setup_model(); d=3e-9
    assert physics.occupancy.charging_energy_J(d)==pytest.approx(legacy.charging_energy(d),rel=1e-13)
    assert physics.occupancy.gamma_c(d,300.0)==pytest.approx(legacy.gamma_c(d),rel=1e-13)

def test_wkb_matches_v53():
    _,physics,_=setup_model(); L=14e-9; F=1.7e8
    got=physics.tunneling.trapezoidal_wkb(L,F,1.78)
    expected=legacy.trapezoidal_wkb_transmission(L,F,1.78)
    assert got==pytest.approx(expected,rel=1e-13)

def test_probability_step_matches_v53():
    _,physics,_=setup_model(); state=DeviceState.empty_for_device(make_v53_reference_device(grid_points=3)).floating_gates[0]
    from ncmemsim import RateArrays
    vals=np.array([1.,2.,3.]); rates=RateArrays(vals,vals*.5,vals*.2,vals*.1,np.zeros(3),np.zeros(3),np.zeros(3))
    got=physics.occupancy.step(state,rates,1e-4)
    exp=legacy.step_local_probabilities(state.P0,state.P1,state.P2,rates.r01,rates.r12,rates.r21,rates.r10,1e-4)
    assert np.allclose(got.P0,exp[0]) and np.allclose(got.P1,exp[1]) and np.allclose(got.P2,exp[2])

def test_single_voltage_relaxation_matches_v53():
    device,physics,sim=setup_model(nx=7); state=DeviceState.empty_for_device(device)      
    got=sim.relax_voltage(state,2.0)
    x,dx=legacy.fg_grid(Nx=7); p0,p1,p2=legacy.initialize_fg_state(7)
    exp=legacy.one_voltage_point_relax(p0,p1,p2,2.0,x,dx,d_nc=3e-9,eta=0.22,T=300.0,N_profile='front_loaded',dwell_time=2e-5,dt=1e-5)
    for key,newkey in [('QFG','qfg_C_m2'),('VFB','vfb_V'),('Veff','veff_V'),('C','capacitance_F_m2'),('m_mean','mean_occupation')]:
        assert got[newkey]==pytest.approx(exp[key],rel=2e-12,abs=1e-18)
    

def test_small_cv_sweep_matches_v53():
    device,physics,sim=setup_model(nx=5)
    got=sim.simulate_cv(-1.0,1.0,7)
    exp=legacy.simulate_cv_hysteresis_distributed(Vmin=-1.0,Vmax=1.0,npts=7,Nx=5,d_nc=3e-9,eta=0.22,T=300.0,N_profile='front_loaded',dwell_time=2e-5)   
    assert np.allclose(got.forward.capacitance_F_m2,exp['forward']['C'],rtol=2e-12,atol=1e-18)
    assert np.allclose(got.backward.qfg_C_m2,exp['backward']['QFG'],rtol=2e-12,atol=1e-18)
    assert got.memory_window_V==pytest.approx(exp['memory_window'],rel=2e-12,abs=1e-15)
    
