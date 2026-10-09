# P4B device/photo qualification protocol review

Status: protocol specification plus an implemented assumed OM-2 sequence adapter.
A measured-device/LCR adapter and experimental qualification remain unresolved. P4A exact-commit CI and
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

## Related-source full-text checkpoint

The supplied CAS2017 paper (DOI 10.1109/SMICND.2017.8101163) uses -1/+5 V
endpoint programming and approximately 5 mW/cm2 integral illumination. It
reports room-temperature measurements, 1 MHz, 0.1 V steps, 0.5 s per point and
a +5 to -1 V read sweep after positive programming. Its capacitance ratio
Q=CPL/CPD-1 is dimensionless, not stored electric charge or a memory-window
contrast. These conditions cannot silently replace APL2018's -2/+5 V and
20 mW/cm2 inputs. Shared project/authors do not settle specimen genealogy.

Reference 48 (DOI 10.1016/j.apsusc.2017.09.038) has now been read in full.
Its Table 1 permittivities are fit-derived from an equivalent RC layer circuit,
including series contact/substrate resistance and an interfacial SiOx branch.
Its Al-contact 1 mm2 device and 7 nm composite FG region differ from the
Au-contact photo-memory specimen. Its effective FG relative permittivity is
retained as **16.4**, exactly as reported; it is not automatically a direct
measurement of pure-Ge NC permittivity or a universal preset.

The FG capacitance printed as 2.07 nF is inconsistent with that permittivity,
the 7 nm layer and the reported area under the planar-capacitance conversion.
Approximately 20.7 nF would reconcile those values. A decimal error is a possible
explanation, not an author-confirmed correction. Keep epsilon_r=16.4; retain the
printed capacitance and flag the possible correction separately. Do not reject
or replace the reported permittivity merely from this consistency calculation.

The user corrected the acquisition premise: only the supplied PDF articles are
available; original data and author/laboratory clarifications are unavailable. Lamp spectrum/reference plane,
full APL electrical/read sequence, repetitions/error budget and specimen identities
remain requested inputs. The Wang2006 candidate remains abstract-only. No
messages to authors are sent by this software review, and no runtime equation,
calibration status, numerical preset or package version changes at this checkpoint.

## Exploratory OM-2 sequence adapter

`ncmemsim.om2_sweep` adds `OM2SweepProtocol`, `OM2SweepExperiment`,
`OM2SweepPrediction` and `run_om2_sweep`. Inputs bind an owned P4A device/photo
experiment to explicit endpoint holds, ascending/descending voltage grids,
point dwell, integration timestep and a common absolute capacitance reference
in F/m2. No fitting, source-data admission or physical equation is added.

```python
from ncmemsim.om2_sweep import (
    OM2SweepProtocol, OM2SweepExperiment, OM2SweepPrediction, run_om2_sweep,
)
```

The assumed order is negative-endpoint hold, ascending dark sweep,
positive-endpoint hold, descending dark sweep. Each grid includes both endpoints,
with its own additional point dwell; those samples are not the hold itself.
State continues across every step, including sweep-induced charging; no state
reset occurs between branches. The matched-dark sequence starts from an identical
copy of the explicit initial state and follows identical voltages and durations.
Illumination is enabled only for the two writing holds of the illuminated run.
Source, capture weights and existing owned NC kinetics come from the P4A input.
Hold duration and upper voltage must match that bound input. Dark measurements
do not introduce an extra zero-dwell P4A read operation between steps.

The model reports existing quasi-static capacitance, not the measured 1 MHz
equivalent parallel LCR capacitance. At a caller-declared common capacitance,
piecewise-linear crossings are found along each ordered branch. Multiple
crossings/plateaus are ambiguous; no sorting of capacitance, silent selection,
per-curve normalization or extrapolation is performed. A missing/ambiguous
crossing gives `not_assessable` and null contrast, even when execution completes.
The signed crossing window is descending minus ascending; light-minus-dark
window contrast preserves that sign. It is not automatically physical Vfb or
the author's extraction criterion.

Archives retain input identities, runtime, every step's original initial/final
state, timing, light flag, C/Vfb/charge and partial failures. Readers verify the
state chain, charges, time and static electrostatic projections; they rebuild
crossings without occupancy integration, optical reevaluation or RNG replay.
Stored trajectories are retained evidence, not authenticated/replayed dynamics.
A failure in the dark sequence keeps completed illuminated observations and
produces no invented contrast. Schema, derived summary and input drift are rejected.

```bash
python examples/phase_p4b_om2_reference.py --output om2.json
python examples/phase_p4b_om2_reference.py --input om2.json --output restored-om2.json
```

The example explicitly uses the assumed P4A 1550 nm line and short numerical
durations: 1e-7 s holds, 1e-8 s point dwells, endpoint voltages -2/+2 V, nine
points per branch and backward-Euler integration. Reference is .8 times geometric
equivalent capacitance. None of these choices reconstructs the tungsten lamp,
minute-scale programming or an experimental Cfb. Tests cover state continuation,
matched dark recovery, zero optical effects, two/three FG bookkeeping, unique
and rejected crossings, archives/failures and a timestep refinement on the same
sequence. The refinement check is numerical evidence for this example, not
convergence certification of a published device experiment.

With PDFs only, the software scope can progress, and measured-curve comparisons
remain exploratory. Substrate photogeneration, RC measurement conversion and
unknown preparation/error/source metadata remain outside this adapter. P4B's
experimental qualification is not closed by this implementation.
