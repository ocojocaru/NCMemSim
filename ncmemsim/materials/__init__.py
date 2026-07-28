from .base import Material, NanocrystalMaterial
from .presets import HFO2, SIO2, SILICON
from .models import make_ge, make_gesn, GeSnModel, GeSnParameterSet
from .provenance import MaterialProperty, ParameterProvenance, ParameterStatus
from .registry import registry, MaterialRegistry
from .band_alignment import BarrierModel, BandAlignmentResult
from .optics import CompactOpticalMaterialModel, OpticalPoint

registry.register("ge", lambda **kw: make_ge(**kw))
registry.register("gesn", lambda **kw: make_gesn(**kw))
registry.register("hfo2", lambda **kw: HFO2)
registry.register("sio2", lambda **kw: SIO2)
registry.register("si", lambda **kw: SILICON)

__all__=["Material","NanocrystalMaterial","HFO2","SIO2","SILICON","make_ge","make_gesn","GeSnModel","GeSnParameterSet","MaterialProperty","ParameterProvenance","ParameterStatus","registry","MaterialRegistry","BarrierModel","BandAlignmentResult","CompactOpticalMaterialModel","OpticalPoint"]
