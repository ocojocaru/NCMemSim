from collections.abc import Sequence
from .device import Device
from .layers import Layer,FloatingGateLayer
from .materials import HFO2,SIO2,NanocrystalMaterial,make_ge

def seq(v,n,label):
    if isinstance(v,(int,float)): return [float(v)]*n
    a=[float(x) for x in v]
    if len(a)!=n: raise ValueError(f"{label} needs {n} values")
    return a

def mats(v,n):
    if isinstance(v,NanocrystalMaterial): return [v]*n
    a=list(v)
    if len(a)!=n: raise ValueError("wrong nc_material count")
    return a

class DeviceBuilder:
    @staticmethod
    def v1(n_fgs,nc_material=None,control_hfo2_nm=35.0,control_sio2_nm=3.0,fg_thickness_nm=15.0,inter_fg_sio2_nm=4.0,inter_fg_hfo2_nm=4.0,tunnel_hfo2_nm=10.0,tunnel_sio2_nm=2.0,nc_diameter_nm=5.0,nc_volume_fraction=0.60,active_fraction=0.22,name=None):
        if n_fgs not in {1,2,3}: raise ValueError("n_fgs must be 1,2,3")
        ms=mats(nc_material or make_ge(),n_fgs); ft=seq(fg_thickness_nm,n_fgs,"fg_thickness_nm"); dn=seq(nc_diameter_nm,n_fgs,"nc_diameter_nm"); vf=seq(nc_volume_fraction,n_fgs,"nc_volume_fraction"); et=seq(active_fraction,n_fgs,"active_fraction"); ni=n_fgs-1; si=seq(inter_fg_sio2_nm,ni,"inter_fg_sio2_nm") if ni else []; hf=seq(inter_fg_hfo2_nm,ni,"inter_fg_hfo2_nm") if ni else []
        layers=[Layer("control_hfo2",HFO2,control_hfo2_nm,"control_dielectric"),Layer("control_sio2",SIO2,control_sio2_nm,"control_dielectric")]
        for i in range(n_fgs):
            layers.append(FloatingGateLayer(f"FG{i+1}",HFO2,ft[i],ms[i],dn[i],vf[i],et[i]))
            if i<ni: layers += [Layer(f"inter_fg{i+1}_sio2",SIO2,si[i],"interlayer_dielectric"),Layer(f"inter_fg{i+1}_hfo2",HFO2,hf[i],"interlayer_dielectric")]
        layers += [Layer("tunnel_hfo2",HFO2,tunnel_hfo2_nm,"tunnel_dielectric"),Layer("tunnel_sio2",SIO2,tunnel_sio2_nm,"native_oxide")]
        d=Device(name or f"V1_{ms[0].name}_{n_fgs}FG","V1",layers); d.validate(); return d
    @staticmethod
    def v2(n_fgs,nc_material=None,control_sio2_nm=20.0,fg_thickness_nm=12.0,inter_fg_sio2_nm=4.0,tunnel_sio2_nm=8.0,nc_diameter_nm=5.0,nc_volume_fraction=0.60,active_fraction=0.22,name=None):
        if n_fgs not in {1,2,3}: raise ValueError("n_fgs must be 1,2,3")
        ms=mats(nc_material or make_ge(),n_fgs); ft=seq(fg_thickness_nm,n_fgs,"fg_thickness_nm"); dn=seq(nc_diameter_nm,n_fgs,"nc_diameter_nm"); vf=seq(nc_volume_fraction,n_fgs,"nc_volume_fraction"); et=seq(active_fraction,n_fgs,"active_fraction"); ni=n_fgs-1; si=seq(inter_fg_sio2_nm,ni,"inter_fg_sio2_nm") if ni else []
        layers=[Layer("control_sio2",SIO2,control_sio2_nm,"control_dielectric")]
        for i in range(n_fgs):
            layers.append(FloatingGateLayer(f"FG{i+1}",SIO2,ft[i],ms[i],dn[i],vf[i],et[i]))
            if i<ni: layers.append(Layer(f"inter_fg{i+1}_sio2",SIO2,si[i],"interlayer_dielectric"))
        layers.append(Layer("tunnel_sio2",SIO2,tunnel_sio2_nm,"tunnel_dielectric"))
        d=Device(name or f"V2_{ms[0].name}_{n_fgs}FG","V2",layers); d.validate(); return d
