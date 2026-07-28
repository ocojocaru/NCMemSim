import json
from ncmemsim import DeviceBuilder,LightSource,make_ge,make_gesn
v1=DeviceBuilder.v1(n_fgs=3,nc_material=[make_ge(),make_gesn(0.02),make_gesn(0.10)],fg_thickness_nm=[12,15,18],inter_fg_sio2_nm=[3,4],inter_fg_hfo2_nm=[4,5],nc_diameter_nm=[4,5,6])
v2=DeviceBuilder.v2(n_fgs=2,nc_material=make_gesn(0.10),control_sio2_nm=25,fg_thickness_nm=[10,14],inter_fg_sio2_nm=5,tunnel_sio2_nm=7)
lamp=LightSource.incandescent(power_density_W_m2=100,temperature_K=2800)
print(json.dumps(v1.to_dict(),indent=2)); print(json.dumps(v2.to_dict(),indent=2)); print(json.dumps(lamp.to_dict(),indent=2))
