from dataclasses import dataclass,field
from typing import Any
@dataclass(frozen=True)
class LightSource:
    name:str; source_type:str; power_density_W_m2:float; enabled:bool=True; spectrum_mode:str="compact"
    temperature_K:float|None=None; wavelength_nm:float|None=None; wavelength_min_nm:float|None=None; wavelength_max_nm:float|None=None; metadata:dict[str,Any]=field(default_factory=dict)
    def __post_init__(self):
        if self.power_density_W_m2<0: raise ValueError("negative optical power")
        if self.source_type not in {"incandescent","led","laser","custom"}: raise ValueError("unsupported source")
        if self.source_type=="incandescent" and (self.temperature_K is None or self.temperature_K<=0): raise ValueError("temperature required")
        if self.source_type in {"led","laser"} and (self.wavelength_nm is None or self.wavelength_nm<=0): raise ValueError("wavelength required")
    @classmethod
    def incandescent(cls,power_density_W_m2,temperature_K=2800.0,wavelength_min_nm=350.0,wavelength_max_nm=2500.0,name="Incandescent lamp",spectrum_mode="compact"):
        return cls(name,"incandescent",power_density_W_m2,True,spectrum_mode,temperature_K,None,wavelength_min_nm,wavelength_max_nm)
    @classmethod
    def led(cls,wavelength_nm,power_density_W_m2,name=None): return cls(name or f"LED {wavelength_nm:g} nm","led",power_density_W_m2,wavelength_nm=wavelength_nm)
    @classmethod
    def laser(cls,wavelength_nm,power_density_W_m2,name=None): return cls(name or f"Laser {wavelength_nm:g} nm","laser",power_density_W_m2,wavelength_nm=wavelength_nm)
    def to_dict(self): return self.__dict__.copy()
