# Controlled multilayer barrier references - Phase S3

## Scope and evidence

S3 implements controlled synthetic studies of the isolated S2 action evaluator.
The baseline is S2 commit `78313d539ead19bd06f1cfc774f0d683b19cb7a8`, whose
CI and Documentation passed before this study. Package identity remains 1.9.0;
the next release version remains provisional. S3 introduces no transport kernel,
material coefficient, simulator attachment or experimental qualification.

Run `python examples/phase_s3_multilayer_reference.py` to print the study, or add
`--output path.json` to create a new JSON file without replacing an existing one.
The [source-pinned study review](barrier_multilayer_review.json) stores original
source requests, results, constants, comparison criteria and historical local
observations. Observed floats may differ slightly across math libraries;
comparisons use the predeclared tolerances, not bytewise equality to one host.

## Seven source profiles

| Profile | Controlled distinction |
|---|---|
| Homogeneous linear | One constant mass and one linear barrier |
| Mass step | Continuous potential endpoints with different per-segment masses |
| Energy step | Discontinuous one-sided energies with the same mass |
| Allowed interval | Two forbidden portions separated by a classically allowed interval; no resonances |
| Zero action | Nonpositive U-E throughout |
| Underflow | Finite large action/exponent with transmission rounded to zero |
| Partial numerical failure | One unrepresentable exponent and a separate completed segment; aggregate unavailable |

The six completed profiles are compared with an independent 100-digit Decimal
linear-barrier primitive. The deliberately failed profile is retained; its full
reference exponent is outside finite output range, so its comparison is unavailable.
These synthetic heights, masses and lengths are numerical controls, not admitted
properties of a Ge/GeSn device. The underflow control also exercises a large exponent
outside the original S1 [0, 10000] control range; it does not extend that range into
a universal accuracy guarantee.

## Invariance checks

Each completed profile is tested with 2, 3, 7 and 16 subdivisions per original
segment. Only interior points of that segment are interpolated; an existing
interface jump is never replaced by a ramp. Segment mass and original endpoint
values are retained. Uniform positive lengths use original length/part count;
their total is checked with floating-point length tolerance.

Additional checks reverse the same energy landscape at the same incident energy,
scale all masses by 0.25 or 4 (action scales by the square root), and shift both
potential and incident energy by a common 1e-19 J reference offset. Reversal
does not recalculate reverse-bias electrostatics or contact supply.

The 48 comparisons meet the predeclared dimensionless exponent criterion:
absolute error <= 1e-12 + 5e-13 * abs(reference). One failed source profile
produces one explicit unavailable assessment rather than eight invented successes.

## Comparing the published kernels

Six single-segment cases cover a rectangle, descending trapezoid, turning point,
ascending linear barrier, near-flat barrier and a thick floor-limited barrier.
The direct evaluator is called with explicit length, signed field, barrier,
incident energy and mass. S3 compares isolated calls; it does not change the
transport engine's use of field magnitude or directional-rate convention.
The sampled grids are 80, 160 (published default), 320, 640, 1280 and 2560 points.

Two historical distinctions are recorded explicitly:

- The direct/S2 electron-mass constant is 9.1093837015e-31 kg, while the published
  TAT kernel uses 9.1093837139e-31 kg. Their expected exponent ratio for otherwise
  identical input is approximately 1.0000000006806167. Each TAT result is assessed
  against a reference using its own constants. A raw difference from S2 is also
  retained; no published coefficient is silently normalized or replaced.
- TAT's difference-of-powers expression loses accuracy in the selected near-flat
  control. That mismatch remains in the results. The stable S2 form passes its
  own independent reference. The old direct evaluator retains its -700 exponential
  floor, while S2 and TAT may report zero transmission with finite exponent.

The direct-grid error decreases under refinement for the selected trapezoid,
turning-point and ascending cases. This does not imply that every grid reaches
the tight S1 analytic tolerance; unresolved mismatches remain visible. A
floor-limited result is labelled as such, not assessed as a recovered full action.
No claim that all published kernels are equivalent is made.

## Profile approximation versus integration error

The final study samples a smooth quadratic forbidden-energy law with 1, 2, 4,
8, 16, 32 and 64 linear segments. Its smooth reference is an independent
high-precision closed-form quadratic integral, cross-checked with adaptive
quadrature in the tests. Every sampled piecewise-linear profile matches its own
Decimal segment reference. Its difference from the smooth profile decreases
with refinement, but 64 segments still do not reach the tight S1 tolerance.

This residual is profile-discretization error, not failure to integrate a linear
segment. Subdividing an existing straight segment leaves its mathematical profile
unchanged; sampling a curved profile more finely changes the approximating profile.
Neither operation removes the physical limits of action-only WKB at abrupt
interfaces or establishes coherent scattering, current or calibration.

## Acceptance boundary and next step

S3 accepts controlled numerical evidence, including negative results. The tests
protect source ownership, source hashes, interval/mass ordering, unchanged legacy
behavior and the distinction between integration, constants and profile-grid error.
Wheel and sdist checks execute the standalone study against the installed package.

S4 now implements a limited [snapshot-bound direct inter-FG contract](barrier_transport_integration.md). Attaching profiles requires an explicit link-length,
orientation, energy-reference, parameter-provenance and no-double-counting contract.
The published near-flat TAT issue must not be silently fixed under this study.
The [Phase S plan](barrier_transport.md) and [roadmap](roadmap.md) retain the
scientific and compatibility boundaries; experimental P4B/P5B/P6B remain deferred.
