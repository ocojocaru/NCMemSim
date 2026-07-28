from __future__ import annotations
from .materials import Material, NanocrystalMaterial
from .layers import Layer,FloatingGateLayer
from .device import Device

FG_EFFECTIVE=Material('FG effective Ge:HfO2',18.0,metadata={'source':'v5.3 effective permittivity'})
GE_V53=NanocrystalMaterial('Ge v5.3',0.0,16.0,0.12,1.78,2.10,0.66,metadata={'source':'v5.3'})
HFO2_V53=Material('HfO2',25.0)
SIO2_V53=Material('SiO2',3.9)

def make_v53_reference_device(grid_points=31,nc_diameter_nm=3.0,active_fraction=0.22):
    device=Device('v5.3 regression device','CUSTOM',[
        Layer('control_hfo2',HFO2_V53,35.0,'control_dielectric'),
        FloatingGateLayer('FG1',FG_EFFECTIVE,15.0,GE_V53,nc_diameter_nm,0.60,active_fraction,'front_loaded',grid_points),
        Layer('tunnel_hfo2',HFO2_V53,10.0,'tunnel_dielectric'),
        Layer('native_sio2',SIO2_V53,2.0,'native_oxide'),
    ],gate_work_function_eV=4.8,substrate_doping_m3=1.2e21,temperature_K=300.0)
    device.validate(); return device
