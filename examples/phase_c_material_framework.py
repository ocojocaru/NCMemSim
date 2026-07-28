import json
from ncmemsim import DeviceBuilder, make_ge, make_gesn
from ncmemsim.materials import BarrierModel, CompactOpticalMaterialModel, HFO2, registry
from ncmemsim.reproducibility import build_reproducibility_manifest

ge=make_ge()
gesn2=make_gesn(0.02)
gesn10=registry.create("gesn",sn_fraction=0.10)
device=DeviceBuilder.v1(n_fgs=3,nc_material=[ge,gesn2,gesn10])

alignment=BarrierModel.affinity_rule(gesn10,HFO2)
optical=CompactOpticalMaterialModel().evaluate(gesn10,1064.0)
manifest=build_reproducibility_manifest(device,extra={
    "alignment":alignment.__dict__,
    "optical_point":optical.__dict__,
})
print(json.dumps(manifest,indent=2))
