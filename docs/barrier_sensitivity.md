# Controlled barrier sensitivity - Phase S5

S5 implements a reproducible, synthetic study of the isolated S2 electron action.
It does not attach profiles to a simulator or change the S4 integration contract.
All parameters are prescribed assumptions; no material coefficient is admitted.
Published package/citation identity is 1.10.0, dated 2026-11-05; S7 is complete.

## Controlled inputs and outputs

Run `python examples/phase_s5_barrier_sensitivity.py` or add `--output new-file.json`.
The output path must not already exist. The JSON includes every original request,
SI profile, provenance, source hashes, per-segment diagnostics, exponent B, log T,
transmission, failures, independent reference and comparison limit.
This is a study output, not the future S6 report/bundle schema.

The baseline is a rectangular 2 nm barrier with electron potential energy U=0.4 eV,
incident energy E=0.1 eV and mass 0.2 m0. U and E share one synthetic energy zero;
U is not an electrostatic voltage or an optical band gap. Explicit conversion
produces the SI values used in the evaluator and in the independent reference.

| Axis | Prescribed values | Held fixed |
|---|---|---|
| Thickness | 1, 2, 4 nm | U, E, mass |
| Potential energy U | 0.2, 0.4, 0.8 eV | Thickness, E, mass |
| Effective mass | 0.1, 0.2, 0.4 m0 | Thickness, U, E |
| Incident energy E | 0, 0.1, 0.3, 0.4, 0.5 eV | Thickness, U, mass |

A nine-point factorial thickness/U study retains joint effects without ranking
by a device objective. Counts include repeated baseline settings in distinct
controls: 31 attempted rows, 30 completed evaluations and one retained numerical
failure; 30 reference matches and one unavailable comparison. No row is discarded
from a success denominator. Unexpected mismatches remain `mismatched` in the output.

## Numerical acceptance and interpretation

An independent 100-digit Decimal rectangular expression evaluates
B=2 L sqrt(2 m max(U-E,0))/hbar using the actual declared SI inputs and S2 constants.
The predeclared S1 limit is inclusive: absolute error <= 1e-12 + 1e-10 |B_ref|.
Tests independently check B proportional to L and sqrt(m), monotonic increase
with U and decrease with E, and opposite changes in T=exp(-B).
At E>=U the action-only approximation returns B=0, T=1; this does not prove unit
physical transmission when interface reflection or above-barrier scattering matters.

Subdivisions of 1, 2, 7, 16 and 64 pieces represent the same rectangular barrier.
They test numerical invariance, with 1e-12 absolute and 5e-13 relative B tolerance.
They do not refine a nonlinear physical potential or estimate model uncertainty.
S3 retains the separate nonlinear-profile refinement evidence and negative controls.

A high-U control retains finite B/log T when T underflows to zero. A deliberately
extreme length/mass control retains failed diagnostics and unavailable full B/T;
its reference is also outside finite output range. Neither is a physical material.
Parameter sweeps are conditional model sensitivity, not probability distributions,
confidence intervals, measured uncertainty, current, yield or lifetime predictions.

## Relationship to transport

The [S4 contract](barrier_transport_integration.md) still requires a current snapshot,
matching physical spacer lengths and explicitly supplied U/E profiles. These isolated
thickness sweeps must not be attached to an unchanged device geometry. No implicit
field-to-barrier law, substrate injection, TAT or image-force composition is added.
The [S3 references](barrier_multilayer_reference.md) and published kernels are retained.
S6 is next: strict source-linked reports and bundles with static consistency checks.
