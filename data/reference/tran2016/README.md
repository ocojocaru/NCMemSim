# Tran 2016 Sample A - Figure 6(a) digitization

This directory contains the F4f0 reference-data package for NCMemSim.

## Source

H. Tran et al., *J. Appl. Phys.* **119**, 103106 (2016), DOI 10.1063/1.4943652.

The selected dataset is Sample A (pure Ge, xSn = 0, zero reported in-plane strain)
from Figure 6(a). The plotted symbols are absorption coefficients obtained by the
authors from spectroscopic-ellipsometry data through the Johs-Herzinger optical
model. They are therefore **model-derived experimental optical data**, not raw
ellipsometry observables.

## Files

- `tran2016_sampleA_fig6a_near_edge_all.csv` - all 8 selected near-edge points.
- `tran2016_sampleA_fig6a_fit.csv` - 4-point fitting subset.
- `tran2016_sampleA_fig6a_validation.csv` - 4-point holdout subset.
- `tran2016_sampleA_fig6a_digitization_audit.csv` - pixel coordinates, converted
  photon energies, alpha values, selected/excluded markers, and split labels.
- `tran2016_sampleA_fig6a_metadata.json` - complete provenance and digitization metadata.
- `tran2016_sampleA_fig6a_overlay.png` - visual verification of marker centers.

The three loader-ready CSV files use exactly:

`wavelength_nm,absorption_coefficient_m_inv,absorption_uncertainty_m_inv`

## Important qualification

The validation subset is a disjoint **holdout from the same published curve**.
It is not an independent experiment. Any future `CALIBRATED` claim must preserve
that qualification explicitly.

The 5% alpha uncertainty is an NCMemSim digitization estimate and must not be
described as an experimental uncertainty reported by Tran et al.
