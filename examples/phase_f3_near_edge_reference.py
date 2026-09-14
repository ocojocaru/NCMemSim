from __future__ import annotations

from ncmemsim import make_gesn
from ncmemsim.materials.optics import GeSnNearEdgeReferenceModel


def main() -> None:
    model = GeSnNearEdgeReferenceModel()

    cases = [
        (0.00, 1500.0),
        (0.00, 1600.0),
        (0.05, 2000.0),
        (0.10, 2500.0),
        (0.15, 2000.0),
    ]

    print(
        "x_Sn   lambda_nm   E_eV       Eg_eV      Ec_eV      "
        "alpha_m^-1      branch   domain"
    )

    for sn_fraction, wavelength_nm in cases:
        material = make_gesn(sn_fraction)

        point = model.evaluate(
            material,
            wavelength_nm=wavelength_nm,
        )

        print(
            f"{sn_fraction:4.2f}   "
            f"{point.wavelength_nm:9.1f}   "
            f"{point.photon_energy_eV:8.5f}   "
            f"{point.direct_gap_eV:8.5f}   "
            f"{point.connection_energy_eV:8.5f}   "
            f"{point.absorption_coefficient_m_inv:12.5e}   "
            f"{point.branch.value:7s}   "
            f"{point.domain_status.value}"
        )


if __name__ == "__main__":
    main()
