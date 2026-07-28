from dataclasses import dataclass,field
from typing import Any
from .constants import EPSILON_0_F_M
from .layers import FloatingGateLayer

@dataclass
class Device:
    name:str; architecture:str; layers:list
    gate_work_function_eV:float=4.8; substrate_doping_m3:float=1e21; temperature_K:float=300.0
    metadata:dict[str,Any]=field(default_factory=dict)
    def validate(self):
        if self.architecture not in {"V1","V2","CUSTOM"}: raise ValueError("invalid architecture")
        if not self.layers or self.temperature_K<=0 or self.substrate_doping_m3<=0: raise ValueError("invalid device")
        names=set()
        for layer in self.layers:
            layer.validate()
            if layer.name in names: raise ValueError("duplicate layer name")
            names.add(layer.name)
        if self.number_of_fgs() not in {1,2,3}: raise ValueError("one to three FGs required")
    def floating_gates(self): return [x for x in self.layers if isinstance(x,FloatingGateLayer)]
    def number_of_fgs(self): return len(self.floating_gates())
    def total_thickness_nm(self): return sum(x.thickness_nm for x in self.layers)
    def layer_positions_nm(self):
        out={}; x=0.0
        for layer in self.layers:
            out[layer.name]=(x,x+layer.thickness_nm); x+=layer.thickness_nm
        return out
    def get_layer(self,name):
        for layer in self.layers:
            if layer.name==name: return layer
        raise KeyError(name)
    def electrical_thickness_nm(self): return sum(x.thickness_nm/x.eps_r for x in self.layers)
    def equivalent_dielectric_capacitance_F_m2(self): return EPSILON_0_F_M/sum(x.thickness_nm*1e-9/x.eps_r for x in self.layers)
    def to_dict(self): return {"name":self.name,"architecture":self.architecture,"gate_work_function_eV":self.gate_work_function_eV,"substrate_doping_m3":self.substrate_doping_m3,"temperature_K":self.temperature_K,"total_thickness_nm":self.total_thickness_nm(),"number_of_fgs":self.number_of_fgs(),"layers":[x.to_dict() for x in self.layers],"metadata":self.metadata}
