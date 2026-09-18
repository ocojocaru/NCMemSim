"""Scientific default/unit/provenance contracts, without new physics."""
from dataclasses import asdict,replace
import math
import numpy as np
import pytest
from ncmemsim.builder import DeviceBuilder
from ncmemsim.constants import EPSILON_0_F_M,ELEMENTARY_CHARGE_C,PLANCK_J_S,LIGHT_SPEED_M_S
from ncmemsim.kinetics import KineticsConfig,OccupancyEngine
from ncmemsim.tunneling import TunnelingConfig,TunnelingEngine
from ncmemsim.simulator import SimulationConfig
from ncmemsim.electrostatics import SemiconductorConfig,ElectrostaticsEngine
from ncmemsim.retention import RetentionConfig
from ncmemsim.transport import TransportConfig
from ncmemsim.photo import PhotoTransitionConfig,PhotoTransitionWeights,nanocrystal_number_density_m3,absorbed_photon_rate_per_nc_s,photo_transition_rate_s
from ncmemsim.optics import LightSource
from ncmemsim.physics import PhysicsModel
from ncmemsim.materials import make_ge,make_gesn
from ncmemsim.materials.database import BASE_PROPERTIES
from ncmemsim.materials.provenance import ParameterProvenance,ParameterStatus,MaterialProperty
from ncmemsim.materials.optics.models import ABSORPTION_MODEL_PROVENANCE,ABSORPTION_COEFFICIENT_PROVENANCE
from ncmemsim.reference import make_v53_reference_device
DEFAULTS=[
 (KineticsConfig,dict(nu0_Hz=1e12,nu1_Hz=1e10,nu2_Hz=3e9,capacitance_eps_r=8.,density_profile='front_loaded')),
 (TunnelingConfig,dict(injection_energy_eV=.10,oxide_effective_mass_m0=.15,integration_points=160,field_coupling_factor=.80,activation_beta_V_inv=.8)),
 (SimulationConfig,dict(dwell_time_s=.005,internal_dt_s=1e-5,qfix_C_m2=0.,qit_C_m2=0.)),
 (TransportConfig,dict(enabled=True,attempt_frequency_Hz=1e9,default_barrier_eV=1.78,effective_mass_m0=.15,direction_beta_V_inv=8.,max_transfer_fraction_per_step=.10,include_substrate_diagnostics=True)),
 (SemiconductorConfig,dict(silicon_eps_r=11.7,intrinsic_density_m3=1e16,electron_affinity_eV=4.05,bandgap_eV=1.12,psi_max_V=.9,transition_voltage_V=.65,transition_width_V=.22,accumulation_factor=40.)),
 (RetentionConfig,dict(gate_voltage_V=0.,total_time_s=1e4,initial_dt_s=1e-9,maximum_dt_s=1e3,growth_factor=2.,output_points=121,quasi_equilibrium_tolerance_C_m2_s=1e-18,quasi_equilibrium_steps=4,stop_at_quasi_equilibrium=False,occupancy_integrator='backward_euler')),
 (PhotoTransitionConfig,dict(photo_capture_efficiency=1e-3)),
 (PhotoTransitionWeights,dict(r01=1.,r12=1.,r10=0.,r21=0.))]

@pytest.mark.parametrize('cls,expected',DEFAULTS)
def test_reviewed_configuration_defaults(cls,expected):
 assert asdict(cls())==expected
 assert 'provenance' not in asdict(cls())

@pytest.mark.parametrize('architecture',['v1','v2'])
@pytest.mark.parametrize('count',[1,2,3])
def test_builder_geometry_and_profile_override(architecture,count):
 d=getattr(DeviceBuilder,architecture)(count)
 assert (d.temperature_K,d.gate_work_function_eV,d.substrate_doping_m3)==(300.,4.8,1e21)
 fgs=d.floating_gates();assert len(fgs)==count
 expected=[35,3]+sum(([15,4,4] for _ in range(count-1)),[])+[15,10,2] if architecture=='v1' else [20]+sum(([12,4] for _ in range(count-1)),[])+[12,8]
 assert [l.thickness_nm for l in d.layers]==expected
 occupancy=PhysicsModel.default().occupancy
 for fg in fgs:
  assert (fg.nc_diameter_nm,fg.nc_volume_fraction,fg.electrically_active_fraction,fg.grid_points,fg.spatial_profile)==(5.,.60,.22,31,'uniform')
  x,dx=occupancy.grid(fg);density=occupancy.density_profile(fg,x)
  assert np.all(density==density[0]) # Explicit layer uniform overrides engine front_loaded.
  assert dx*fg.grid_points==pytest.approx(fg.thickness_nm*1e-9)

@pytest.mark.parametrize('material',BASE_PROPERTIES)
def test_base_database_is_assumed_not_literature_or_calibrated(material):
 for record in BASE_PROPERTIES[material].values():
  assert record.provenance.status is ParameterStatus.ASSUMED
  assert record.provenance.doi is None
  assert 'reported_uncertainty' not in record.provenance.to_dict()

@pytest.mark.parametrize('status',list(ParameterStatus))
def test_provenance_serialization_preserves_declared_status(status):
 p=ParameterProvenance(source='Audit declared source',status=status)
 assert MaterialProperty(1.,'1',p).to_dict()['provenance']['status']==status.value
 assert 'reported_uncertainty' not in p.to_dict()

def test_zero_uncertainty_is_distinct_from_missing():
 p=ParameterProvenance('Audit',ParameterStatus.ASSUMED,reported_uncertainty=0.,uncertainty_unit='eV')
 assert p.to_dict()['reported_uncertainty']==0.
 assert 'reported_uncertainty' not in replace(p,reported_uncertainty=None,uncertainty_unit=None).to_dict()

def test_model_citation_does_not_promote_absorption_coefficients():
 assert ABSORPTION_MODEL_PROVENANCE.status is ParameterStatus.LITERATURE
 assert ABSORPTION_MODEL_PROVENANCE.doi is not None
 assert ABSORPTION_COEFFICIENT_PROVENANCE.status is ParameterStatus.ASSUMED
 assert ABSORPTION_COEFFICIENT_PROVENANCE.doi is None

def test_custom_material_values_and_name_do_not_promote_provenance():
 ge=make_ge(phi_barrier_prog_eV=1.9,parameter_set='custom-review-v1')
 alloy=make_gesn(.08,name='custom-alloy',phi_ge_prog_eV=1.9)
 assert ge.model_version=='custom-review-v1'
 assert ge.properties['phi_barrier_prog_eV'].value==1.9
 # Legacy property provenance retains default-v1; custom model name is not a fitted record.
 assert ge.properties['phi_barrier_prog_eV'].provenance.parameter_set=='default-v1'
 assert all(p.provenance.status is ParameterStatus.ASSUMED for m in (ge,alloy) for p in m.properties.values())

def test_regression_reference_is_distinct_from_builder_default():
 ref=make_v53_reference_device();fg=ref.floating_gates()[0]
 assert (ref.substrate_doping_m3,fg.nc_diameter_nm,fg.spatial_profile,fg.eps_r)==(1.2e21,3.,'front_loaded',18.)
 assert (fg.nc_material.phi_barrier_prog_eV,fg.nc_material.phi_barrier_erase_eV)==(1.78,2.10)
 assert fg.nc_material.properties=={} # Historical metadata is not typed provenance.

def test_nm_si_density_and_photo_efficiency_units():
 d=DeviceBuilder.v2(1);fg=d.floating_gates()[0];o=PhysicsModel.default().occupancy
 n=nanocrystal_number_density_m3(5.,.6)
 assert n==pytest.approx(.6/(math.pi/6*(5e-9)**3))
 assert o.effective_density(5e-9,.6,.22)==pytest.approx(.22*n)
 photons=absorbed_photon_rate_per_nc_s(2*n,5.,.6)
 assert photons==pytest.approx(2.) # Per physical NC, not per electrically active NC.
 assert photo_transition_rate_s(photons)==pytest.approx(.002)
 assert d.equivalent_dielectric_capacitance_F_m2()==pytest.approx(EPSILON_0_F_M/sum(l.thickness_nm*1e-9/l.eps_r for l in d.layers))

def test_monochromatic_energy_power_flux_and_disabled_zero():
 light=LightSource('Audit','laser',10.,wavelength_nm=1550.)
 assert light.photon_energy_J==pytest.approx(PLANCK_J_S*LIGHT_SPEED_M_S/1550e-9,abs=0)
 assert light.photon_energy_eV*ELEMENTARY_CHARGE_C==pytest.approx(light.photon_energy_J,abs=0)
 assert light.photon_flux_m2_s*light.photon_energy_J==pytest.approx(10.)
 assert replace(light,enabled=False).photon_flux_m2_s==0.

def test_signed_charge_and_fixed_interface_sum():
 e=ElectrostaticsEngine();d=DeviceBuilder.v2(1);q=-1e-4
 neutral=e.evaluate(d,0.,[0.]);charged=e.evaluate(d,0.,[q])
 assert charged.vfb_V>neutral.vfb_V
 assert charged.veff_V<neutral.veff_V
 assert e.flatband_zero(d,qfix_C_m2=q)==pytest.approx(e.flatband_zero(d,qit_C_m2=q))
 assert e.dynamic_flatband(0.,q,1e-3)==pytest.approx(.1)

def test_wkb_transmission_and_activation_are_dimensionless():
 t=TunnelingEngine();a=t.trapezoidal_wkb(5e-9,1e8,2.8)
 assert 0.<a<=1.
 assert t.positive_activation(.7)+t.negative_activation(.7)==pytest.approx(1.)
 assert t.field_from_effective_voltage(-1.,5e-9)==pytest.approx(.8/5e-9)
