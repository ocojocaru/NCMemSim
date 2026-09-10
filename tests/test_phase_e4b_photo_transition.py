import pytest

from ncmemsim.photo import (
    PhotoTransitionConfig,
    photo_transition_rate_s,
)


def test_default_photo_transition_efficiency():
    config = PhotoTransitionConfig()

    assert config.photo_capture_efficiency == pytest.approx(
        1.0e-3
    )


def test_photo_transition_rate_scales_with_efficiency():
    config = PhotoTransitionConfig(
        photo_capture_efficiency=0.01
    )

    rate = photo_transition_rate_s(
        absorbed_photon_rate_per_nc_s=3500.0,
        config=config,
    )

    assert rate == pytest.approx(35.0)


def test_zero_efficiency_gives_zero_transition_rate():
    config = PhotoTransitionConfig(
        photo_capture_efficiency=0.0
    )

    rate = photo_transition_rate_s(
        absorbed_photon_rate_per_nc_s=3500.0,
        config=config,
    )

    assert rate == 0.0


def test_unit_efficiency_recovers_absorbed_photon_rate():
    config = PhotoTransitionConfig(
        photo_capture_efficiency=1.0
    )

    rate = photo_transition_rate_s(
        absorbed_photon_rate_per_nc_s=3500.0,
        config=config,
    )

    assert rate == pytest.approx(3500.0)


def test_invalid_photo_capture_efficiency_rejected():
    with pytest.raises(ValueError):
        PhotoTransitionConfig(
            photo_capture_efficiency=-0.01
        )

    with pytest.raises(ValueError):
        PhotoTransitionConfig(
            photo_capture_efficiency=1.01
        )


def test_negative_absorbed_photon_rate_rejected():
    with pytest.raises(ValueError):
        photo_transition_rate_s(
            absorbed_photon_rate_per_nc_s=-1.0
        )