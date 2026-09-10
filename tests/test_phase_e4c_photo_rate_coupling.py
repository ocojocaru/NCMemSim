import numpy as np
import pytest

from ncmemsim.kinetics import OccupancyEngine, RateArrays
from ncmemsim.photo import (
    PhotoTransitionRates,
    PhotoTransitionWeights,
    photo_transition_rate_arrays,
)


def test_default_photo_weights_are_programming_only():
    weights = PhotoTransitionWeights()

    assert weights.r01 == pytest.approx(1.0)
    assert weights.r12 == pytest.approx(1.0)
    assert weights.r10 == pytest.approx(0.0)
    assert weights.r21 == pytest.approx(0.0)


def test_photo_rate_arrays_use_base_rate():
    photo = photo_transition_rate_arrays(
        base_photo_rate_s=3.5,
        grid_size=4,
    )

    assert np.allclose(photo.r01, 3.5)
    assert np.allclose(photo.r12, 3.5)
    assert np.allclose(photo.r10, 0.0)
    assert np.allclose(photo.r21, 0.0)


def test_custom_photo_transition_weights():
    weights = PhotoTransitionWeights(
        r01=1.0,
        r12=0.5,
        r10=0.2,
        r21=0.1,
    )

    photo = photo_transition_rate_arrays(
        base_photo_rate_s=10.0,
        grid_size=3,
        weights=weights,
    )

    assert np.allclose(photo.r01, 10.0)
    assert np.allclose(photo.r12, 5.0)
    assert np.allclose(photo.r10, 2.0)
    assert np.allclose(photo.r21, 1.0)


def test_zero_photo_rate_gives_zero_arrays():
    photo = photo_transition_rate_arrays(
        base_photo_rate_s=0.0,
        grid_size=5,
    )

    assert np.all(photo.r01 == 0.0)
    assert np.all(photo.r12 == 0.0)
    assert np.all(photo.r10 == 0.0)
    assert np.all(photo.r21 == 0.0)


def test_invalid_photo_weights_rejected():
    with pytest.raises(ValueError):
        PhotoTransitionWeights(
            r01=-1.0,
        )


def test_invalid_photo_array_inputs_rejected():
    with pytest.raises(ValueError):
        photo_transition_rate_arrays(
            base_photo_rate_s=-1.0,
            grid_size=3,
        )

    with pytest.raises(ValueError):
        photo_transition_rate_arrays(
            base_photo_rate_s=1.0,
            grid_size=0,
        )
        
        
def make_electrical_rates():
    return RateArrays(
        r01=np.array([1.0, 2.0, 3.0]),
        r12=np.array([0.5, 1.0, 1.5]),
        r21=np.array([0.4, 0.3, 0.2]),
        r10=np.array([0.2, 0.2, 0.2]),
        tprog=np.array([0.1, 0.2, 0.3]),
        terase=np.array([0.3, 0.2, 0.1]),
        field_V_m=np.array([1.0e8, 1.0e8, 1.0e8]),
    )


def test_electrical_and_photo_rates_add():
    electrical = make_electrical_rates()

    photo = photo_transition_rate_arrays(
        base_photo_rate_s=2.0,
        grid_size=3,
    )

    total = OccupancyEngine.combine_rates(
        electrical,
        photo,
    )

    assert np.allclose(
        total.r01,
        electrical.r01 + 2.0,
    )

    assert np.allclose(
        total.r12,
        electrical.r12 + 2.0,
    )

    assert np.allclose(
        total.r10,
        electrical.r10,
    )

    assert np.allclose(
        total.r21,
        electrical.r21,
    )


def test_photo_coupling_does_not_modify_transport_quantities():
    electrical = make_electrical_rates()

    photo = photo_transition_rate_arrays(
        base_photo_rate_s=10.0,
        grid_size=3,
    )

    total = OccupancyEngine.combine_rates(
        electrical,
        photo,
    )

    assert np.allclose(
        total.tprog,
        electrical.tprog,
    )
    assert np.allclose(
        total.terase,
        electrical.terase,
    )
    assert np.allclose(
        total.field_V_m,
        electrical.field_V_m,
    )