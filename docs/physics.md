# Physics model

This chapter documents the physical interpretation of the current Phase D implementation. The code remains the executable specification; this page states the intended equations, assumptions, and limitations.

## 1. Device geometry

The device is represented by an ordered one-dimensional stack. A layer has a thickness, dielectric permittivity, material identity, and geometric position. A floating-gate layer additionally carries nanocrystal material, diameter, volume fraction, electrically active fraction, and state-grid information.

The electrostatic coordinate is normal to the gate stack. Lateral inhomogeneity and explicit random nanocrystal positions are not resolved in v0.9.1.

## 2. Floating-gate charge states

For each floating gate and each internal grid point, the model stores three probabilities:

\[
P_0,\quad P_1,\quad P_2,
\]

subject to

\[
P_0 + P_1 + P_2 = 1,
\qquad
0 \le P_j \le 1.
\]

The model's normalized mean occupation is

\[
m = \frac{P_1}{2} + P_2.
\]

This definition maps the empty, singly occupied, and doubly occupied states to 0, 1/2, and 1. The physical sheet charge is calculated from occupation, nanocrystal density, active fraction, and electron charge according to the implementation's compact population model.

Each FG evolves independently, although its local field and transport rates depend on the complete device state.

## 3. Compact electrostatic coupling

The total flat-band shift is decomposed into contributions from all floating gates:

\[
\Delta V_{\mathrm{FB}} = \sum_i \Delta V_{\mathrm{FB},i}.
\]

In compact form, a charge sheet closer to the gate and one closer to the substrate do not necessarily have the same sensitivity. The coupling model therefore computes geometry-dependent weighting factors and a coupling matrix rather than treating the total charge as a single sheet.

The result contains:

- total and per-FG sheet charge;
- per-FG flat-band-shift contribution;
- total flat-band shift;
- electrostatic sensitivity factors;
- local field estimates.

This is not a self-consistent multidimensional Poisson solver. It is a one-dimensional compact model designed for fast parametric exploration.

## 4. Potential and electric-field reconstruction

`FieldSolver1D` constructs a piecewise potential profile \(V(z)\) across layer boundaries and derives the segment field using the sign convention

\[
E(z) = -\frac{\mathrm{d}V}{\mathrm{d}z}.
\]

Local potential and field values are interpolated or evaluated at each floating-gate center. These local values drive tunnelling and rate calculations.

Interface charge is represented through the compact FG coupling treatment. Explicit interface traps, mobile ionic charge, and lateral fringing fields are not included.

## 5. WKB tunnelling

The tunnelling engine evaluates a semiclassical transmission of the form

\[
T \approx \exp\left[-2\int_{z_1}^{z_2}
\sqrt{\frac{2m^*}{\hbar^2}\left(U(z)-E\right)}\,\mathrm{d}z\right],
\]

for the classically forbidden portion of the barrier. The implementation supports compact direct-tunnelling calculations and field-dependent barrier shapes through its configuration.

Transmission is highly sensitive to barrier height, effective mass, thickness, and local field. These values must therefore be reported with provenance in scientific use.

The current implementation does not claim a complete treatment of trap-assisted tunnelling, image-force lowering, non-parabolic bands, coherent resonances, or full quantum transport.

## 6. Transport network

The device is mapped to nodes and directed tunnel links. Floating gates are linked to nearest neighbours; substrate-related links may also be represented for diagnostics or boundary exchange depending on the workflow.

A link result contains transmission and flux information. Net flux for each floating gate is obtained by summing signed incident-link contributions.

The finite transfer step is availability-limited so that a source cannot transfer more charge than it contains. The rebalanced implementation preserves internal charge conservation for pure FG↔FG redistribution within numerical tolerance.

## 7. Occupancy kinetics

The occupancy engine updates the three-state system using configured transition rates. Conceptually, the local transitions are

\[
P_0 \rightleftarrows P_1 \rightleftarrows P_2.
\]

Rates can depend on local fields, tunnelling transmissions, energy parameters, and the selected compact kinetics configuration. Probability normalization and admissible bounds are checked by the validation layer.

## 8. Voltage relaxation and sweeps

`Simulator.relax_voltage` advances a supplied state for a selected gate voltage and dwell time. A sweep applies that operation sequentially over a voltage array, so the output state of one point becomes the input state of the next point. Forward and backward sweeps can therefore exhibit history dependence and a memory window.

The C–V workflow is a compact LCR-style approximation built on the simulator's charge and electrostatic response; it should not be interpreted as a transient small-signal TCAD calculation unless the selected configuration and comparison justify that interpretation.

## 9. Retention

Retention advances an initially programmed state at a specified bias, usually zero gate bias. The solver uses a small initial step and grows the timestep geometrically up to a configured maximum, while returning values at approximately logarithmic output times.

Typical outputs include:

- total and per-FG charge versus time;
- mean occupation by FG versus time;
- final state;
- total-charge retention fraction;
- charge-loss fraction;
- quasi-equilibrium status.

A long extrapolation is only as reliable as the underlying barrier, rate, and material assumptions. Agreement at short simulated times does not by itself validate a ten-year prediction.

## 10. Units and sign conventions

Internal calculations use SI units. Public geometry inputs commonly include `_nm` in the parameter name and are converted internally. Charge densities are reported in C m\(^{-2}\), fields in V m\(^{-1}\), fluxes in m\(^{-2}\) s\(^{-1}\), and time in seconds.

Electron charge is negative; reported FG charge and flat-band-shift signs must be interpreted together with the documented voltage and field conventions.

## 11. Current limitations

Version 0.9.1 does not yet provide:

- self-consistent multidimensional Poisson–Schrödinger simulation;
- explicit stochastic nanocrystal spatial ensembles;
- calibrated optical generation and optical programming;
- automated experimental fitting and uncertainty intervals;
- trap-assisted, defect-mediated, or phonon-assisted transport;
- endurance, breakdown, and full reliability physics;
- a guaranteed material database valid across all compositions and temperatures.

These limitations are deliberate roadmap items, not hidden capabilities.
