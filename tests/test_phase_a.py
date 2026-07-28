import pytest
from ncmemsim import DeviceBuilder,LightSource,make_ge,make_gesn

def test_materials():
    assert make_ge().sn_fraction==0
    assert make_gesn(0.02).sn_fraction==pytest.approx(0.02)
    with pytest.raises(ValueError): make_gesn(1.1)

@pytest.mark.parametrize("arch",["v1","v2"])
@pytest.mark.parametrize("n",[1,2,3])
def test_builders(arch,n):
    d=getattr(DeviceBuilder,arch)(n_fgs=n)
    assert d.number_of_fgs()==n and d.total_thickness_nm()>0 and d.equivalent_dielectric_capacitance_F_m2()>0

def test_independent_fgs_and_thickness():
    d=DeviceBuilder.v1(n_fgs=3,nc_material=[make_ge(),make_gesn(0.02),make_gesn(0.10)],fg_thickness_nm=[10,11,12],nc_diameter_nm=[4,5,6])
    assert [x.thickness_nm for x in d.floating_gates()]==[10,11,12]
    old=d.total_thickness_nm(); d.get_layer("control_hfo2").thickness_nm+=5; d.validate(); assert d.total_thickness_nm()==pytest.approx(old+5)

def test_positions_and_light():
    d=DeviceBuilder.v2(n_fgs=2); p=list(d.layer_positions_nm().values())
    for a,b in zip(p,p[1:]): assert a[1]==pytest.approx(b[0])
    lamp=LightSource.incandescent(power_density_W_m2=100,temperature_K=2800)
    assert lamp.source_type=="incandescent"
