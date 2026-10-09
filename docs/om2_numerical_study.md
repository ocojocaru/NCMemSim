# P5A OM-2 numerical diagnostics

P5A implements an assumed numerical reference and sensitivity study. P5B remains
the measured applied reference, identifiability and uncertainty-validation gate,
conditional on admitted experimental data. P4B experimental qualification is also
open. The user approved this split with PDFs as the only available source.
Package/citation remain published v1.6.0; no scientific preset is promoted.

## Reproducible scope

`examples/phase_p5a_om2_numerical_study.py` freezes a numerical specification
before running thirteen cases through the existing OM-2 adapter. Each case retains
the complete owned prediction, states, source identity, failures and crossings.
JSON restoration rebuilds static projections and the study summary; it does not
rerun occupancy integration, optics or a random generator. Missing cases,
relabelled capture/power inputs, changed specifications and tampered summaries
are rejected. This fixed example archive is not a general P6 study bundle.

```bash
python examples/phase_p5a_om2_numerical_study.py --output om2-study.json
python examples/phase_p5a_om2_numerical_study.py --input om2-study.json --output restored-study.json
```

Inputs remain P4B's short synthetic example: assumed 1550 nm illumination,
sample power 0.01 W, capture efficiency 0.1, endpoint voltages -2/+2 V,
explicit initial state, 1e-7 s writing holds and 1e-8 s dark point dwells.
There is no minute-scale tungsten-lamp reconstruction or comparison to measured
device data. Constant-capacitance crossings are not a physical Cfb or an LCR
measurement adapter. Existing NC equations are unchanged; substrate
photogeneration remains unmodeled.

## Temporal refinement at fixed sequence

Timestep is dt, dt/2 and dt/4 with exactly the same voltage grids, holds, dwell
durations, source and state. Compare all per-step capacitances and signed
light-minus-dark crossing-window contrast. The example predeclares bounds
1e-8 F/m2 and 1e-6 V on successive changes. These are numerical diagnostic
thresholds, not experimental accuracy requirements or derived measurement errors.

The inspected local run gives maximum capacitance changes about 4.04e-14 and
2.01e-14 F/m2 and window changes about 1.98e-11 and 9.86e-12 V. The latter
change ratio is approximately 0.498. Both comparisons fall within the example's
thresholds. This is observed timestep stability on a fixed spatial/voltage grid,
not a rigorous error bound, extrapolated exact solution, global convergence proof
or convergence certification of Palade's measured device. A failed solver case
keeps its observations and makes the comparison not assessable, never passed.

## Local sensitivity and parameter confounding

Capture is varied to 0.09/0.11 at fixed power, and delivered power to
0.009/0.011 W at fixed capture. Central secants use signed output contrast.
These +/-10% variations are assumed numerical probes, not reported uncertainty
intervals, standard deviations or a probability distribution.

The inspected secants are approximately -0.001618 V per unit capture and
-0.01618 V/W. They are local responses of this model/context; a different source,
device, regime or observable need not have the same sensitivities.

An explicit paired case changes capture to 0.05 and power to 0.02 W. Its
capacitance trajectories and contrast match the nominal 0.1/0.01 W case in this
run. With fixed line spectrum and constant capture, the NC photo-transition
model responds to their product. This numerical check illustrates parameter
confounding: the response alone cannot independently identify both unknowns.
It is not a statistical confidence interval or proof of identifiability for a
measured device. Calibrated illumination or other independent constraints would
be required before inferring capture efficiency from such a fit.

## Controls and observable-selection sensitivity

Zero power and zero capture recover their matched-dark trajectories. Common
reference capacitance is varied to 0.7/0.8/0.9 times the geometric equivalent
capacitance. The example contrasts are approximately -0.000160754,
-0.000161231 and -0.000161707 V. This dependence is an observable-definition
sensitivity, not a material-parameter change or source-reported voltage error.

A reference of 1e6 F/m2 lies outside the curves. Execution completes but its
crossing contrast is null and `not_assessable`; no extrapolation is substituted.
All thirteen case outcomes are retained, including non-assessable observables.

## Remaining scientific gates

P5A supplies software/numerical evidence only. No dataset admission, fitting,
CALIBRATED result, covariance/error budget or independent experimental validation
is created. A measured P5B reference still needs adequate source/protocol/error
inputs, genealogy, model/measurement applicability and predeclared criteria.
P6 reporting and P7 release scope must preserve these limits; implementing P5A
does not close the independent-calibration milestone.

P6A [numerical reports/bundles](om2_reporting.md) now owns this study through
OM2NumericalStudy and preserves the unchanged P5A archive format. P6B measured
reports remain conditional on eligible evidence.
