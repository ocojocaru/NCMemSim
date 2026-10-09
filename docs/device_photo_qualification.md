# P4B device/photo qualification protocol review

Status: protocol specification for source review, not an implemented measurement
adapter or completed experimental qualification. P4A exact-commit CI and
Documentation passed on `723bdd14dde7af7cb26fdc0d66d693967cd89154`.
Package/citation remain published v1.6.0.

## Selected first comparison: OM-2

The first candidate is Palade et al., Applied Physics Letters 113, 213106 (2018),
[DOI 10.1063/1.5039554](https://doi.org/10.1063/1.5039554), Figure 2(b):
illumination during endpoint writing, followed by C-V measurement in the dark.
OM-2 is selected for protocol development because the dark measurement avoids
the simultaneous light-related capacitance change in OM-1. It does not remove
substrate photogeneration during writing or establish model adequacy.

The supplied full text has been inspected. Its identity and unresolved gates are
recorded in [the source review](device_photo_protocol_review.json).
The PDF and figure images are not redistributed by this repository.
Sparse digitization artifacts remain review candidates, not admitted datasets.

## Observables and signs

Preserve two separate branches of C(Vg), their sweep directions and endpoint
preparations. The published memory window uses two extracted flat-band voltages:

`w = Vfb_after_positive_writing - Vfb_after_negative_writing`

`delta_w = w_illuminated_writing - w_dark_writing`

These are signed definitions; do not silently apply an absolute value or reverse
the subtraction to agree with a model. Signed q in the paper's electrostatic
relation is distinct from a positive count of added electrons. The simulator's
occupancy/charge convention needs an explicit documented conversion.

Digitized normalized capacitance intersections are C-V shape observations, not
automatically flat-band voltages. In particular, the 80% capacitance condition
used for the paper's OM-3 retention method must not be imported as an OM-2
flat-band extraction rule without justification. Record whether a voltage is
obtained by a physical Cfb criterion, a constant-capacitance convention or a
curve shift. The adapter must predict that same measurement definition.

A P4A single-pulse delta_vfb is relative to its own initial state; it is not this
two-branch memory window. A plotted current, apparent voltage jump under light,
or derived mean electron count is not an interchangeable observable.

## Electrical sequence

The article specifies sweeps between -2 V and +5 V with 0.1 V steps and 0.5 s
per point, plus writing holds at sweep endpoints, and a 1 MHz capacitance
measurement. The plotted writing times include 30 s, 1, 2, 5 and 10 min.
Hold illumination is enabled only during writing for OM-2; sweeps are dark.

Before implementation, recover the initial sweep direction, sequence of endpoint
holds and measurements, cycle count, reset between conditions, AC amplitude,
measurement temperature, settling and voltage-extraction algorithm. Follow state
continuation through the actual sequence. Do not initialize every condition to
empty occupancy, independently reset the two branches, or assume frozen charge
through the sweep. A sweep leg lasts roughly 35 s before endpoint conventions;
its evolution cannot automatically be neglected relative to a 30 s writing hold.
Numerical integration timestep is a convergence setting, distinct from the
instrument's 0.5 s sampling interval.

## Optical and device inputs

The source is a tungsten lamp with reported integrated irradiance 20 mW/cm2
(200 W/m2). The spectrum, reference plane and coverage must be recovered before
binding an optical prediction. Do not replace it with a 1550 nm line or derive
per-filter power from total irradiance times filter peak transmission.
Include the Au electrode's spectral attenuation once, with an explicit reference
plane and any measured normalization/calibration response.

For this article, the top electrode area is 3 x 3 mm2, not the related project
demonstrator's 1 mm2. The reported post-anneal HfO2/FG/HfO2 thicknesses are
7 +/- 1, 4 +/- 1 and 23 +/- 2 nm, with about 2 nm interfacial SiO2.
The 4 nm FG-region thickness is not a nanocrystal diameter. Reported thickness
ranges are not automatically standard uncertainties. Retain p-Si resistivity,
NC diameter/density/active-fraction assumptions, dielectric/transport inputs and
their sources. Resolve the printed NC density inconsistency instead of silently
repairing it; reference 48 supplies simulation-derived permittivities.

The paper explicitly describes photo-generated carriers in both Ge NCs and Si,
with negative-charge transfer from substrate to NCs. P4A only binds its existing
NC photo-transition pathway. Substrate carrier generation, transport and
electrostatic response must be reviewed as a separate physics scope, including
their validity and source-backed coefficients. Fitting capture efficiency cannot
stand in for this unresolved mechanism or missing illumination metadata.

## Source, split and uncertainty gates

Keep original numerical data or an audited digitization with axis references,
pixel bounds, preprocessing, exclusions and hashes. Extraction bounds are not
experimental standard deviations. Review normalized-capacitance errors, voltage
and timing errors, repetitions, drift, shared calibration and correlated branch
uncertainty. A light/dark contrast is not independent of its two component curves.

Do not split rows from a single curve as specimen-independent evidence. Specimen,
batch and acquisition genealogy must determine training and holdout groups under
the P1 policy. Different writing times are condition changes, not proof of
independent specimens. Condition holdouts, if later permitted, need a separately
named policy; do not silently weaken IndependentStudySplit. The 2017 CAS paper,
2018 APL article and project summary may share samples or observations.
Fig. 3(b) derived electron counts share ancestry with Fig. 3(a) voltages and
cannot serve as independent validation of them.

After admission and applicability review, freeze the free parameter list,
bounds, initialization, objective, error treatment, domain and numerical
convergence checks before optimization. Freeze holdout criteria before further
holdout inspection or fitting; the already inspected published curves cannot be
claimed as blind unseen validation. Criteria must be justified for this dataset,
not chosen retrospectively to make a fit pass. No numerical acceptance thresholds
or free parameters are specified while the error/model inputs remain unknown.

## Separate OM-3 extension

Figure 3(a) uses sequential 60 s light/60 s dark intervals after different dark
preparations and tracks voltage at 80% of accumulation capacitance. It requires
retention state continuation and a constant-capacitance measurement model.
Separate the instantaneous light capacitance response from stored-charge changes;
dark controls and elapsed read time belong to that interpretation. It is not a
zero-dwell read, and wall-clock time is not cumulative illumination time.
No OM-3 adapter or substrate photo-transport equation is implemented by this
protocol document.

## Current outcome and next dependency

P4B remains `not_assessable`: full text acquired, selected digitization reviewed,
but device acquisition provenance, source/error inputs and model/measurement
mapping remain unresolved. This is an acquisition/applicability outcome, not
model failure. Zero measured device packages admitted and zero parameters fitted
or experimentally qualified by this review. P5-P7 are not advanced by it.

Next: recover original OM-2 data/protocol and lamp calibration if available;
inspect reference 48; resolve source uncertainties and specimen genealogy; then
review the substrate photo-response and C-V measurement scope before runtime
implementation. If those inputs cannot be recovered, retain this gap or select
another eligible experiment. Do not manufacture a calibration from the P4A
synthetic example.
