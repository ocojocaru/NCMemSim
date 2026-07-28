from dataclasses import dataclass,field
from typing import Any
from .materials import Material,NanocrystalMaterial

@dataclass
class Layer:
    name:str; material:Material; thickness_nm:float; role:str; metadata:dict[str,Any]=field(default_factory=dict)
    def validate(self):
        if not self.name or self.thickness_nm<=0 or not self.role: raise ValueError("invalid layer")
    @property
    def eps_r(self): return self.material.eps_r
    def to_dict(self): return {"type":"layer","name":self.name,"material":self.material.name,"thickness_nm":self.thickness_nm,"eps_r":self.eps_r,"role":self.role}

@dataclass
class FloatingGateLayer:
    name:str; matrix_material:Material; thickness_nm:float; nc_material:NanocrystalMaterial
    nc_diameter_nm:float; nc_volume_fraction:float; electrically_active_fraction:float
    spatial_profile:str="uniform"; grid_points:int=31; metadata:dict[str,Any]=field(default_factory=dict)
    def validate(self):
        if not self.name or self.thickness_nm<=0 or self.nc_diameter_nm<=0: raise ValueError("invalid FG layer")
        if not 0<=self.nc_volume_fraction<=1 or not 0<=self.electrically_active_fraction<=1 or self.grid_points<2: raise ValueError("invalid FG parameters")
    @property
    def eps_r(self): return self.matrix_material.eps_r
    @property
    def role(self): return "floating_gate"
    def to_dict(self): return {"type":"floating_gate","name":self.name,"matrix_material":self.matrix_material.name,"thickness_nm":self.thickness_nm,"nc_material":self.nc_material.name,"sn_fraction":self.nc_material.sn_fraction,"nc_diameter_nm":self.nc_diameter_nm,"nc_volume_fraction":self.nc_volume_fraction,"electrically_active_fraction":self.electrically_active_fraction,"spatial_profile":self.spatial_profile,"grid_points":self.grid_points}
