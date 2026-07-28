# Electrostatics and local fields

## Compact coupling model

For a charged multi-FG stack, NCMemSim evaluates the contribution of every FG to the flat-band shift. The implementation exposes the result through `CouplingResult`, including:

- per-FG sensitivity factors;
- coupling coefficients in m²/F;
- a coupling matrix;
- per-FG and total flat-band shifts.

For one FG, the validated compact relation is preserved:

\[
\Delta V_{\mathrm{FB}}=-\frac{Q_{\mathrm{FG}}}{C_{\mathrm{ox}}}.
\]

For multiple FGs, centroid-dependent sensitivity factors weight the charge according to its location in the dielectric stack.

## Electrostatic evaluation

`ElectrostaticsEngine.evaluate()` combines:

- applied gate voltage;
- FG sheet charge;
- fixed charge `qfix_C_m2`;
- interface charge `qit_C_m2`;
- semiconductor configuration;
- dielectric stack capacitance.

The returned `ElectrostaticsResult` contains the effective voltage, flat-band voltage, capacitance, coupling information, local FG fields and potentials, and the full field profile.

## One-dimensional field profile

`FieldSolver1D` reconstructs a piecewise layer-resolved potential and electric field along the stack coordinate. The resulting `FieldProfile` is stored in simulation output under both `field_profile` and the backward-compatible `potential_profile` key.

The sign convention follows

\[
E(z)=-\frac{\mathrm{d}V}{\mathrm{d}z}.
\]

Local quantities are interpolated at every FG center and written back to the corresponding `FloatingGateState`.

## Output quantities

A voltage-relaxation result includes:

- `delta_vfb_V`;
- `delta_vfb_by_fg_V`;
- `coupling_sensitivity_factors`;
- `coupling_coefficients_m2_F`;
- `coupling_matrix_m2_F`;
- `electrostatic_local_field_by_fg_V_m`;
- `electrostatic_local_potential_by_fg_V`;
- `field_profile`.

These outputs support both aggregate C–V analysis and diagnosis of the physical conditions experienced by individual FGs.

## Scope of the solver

The field solver is a compact one-dimensional reconstruction. It does not resolve lateral nanocrystal geometry, field crowding around individual particles, or multidimensional gate-edge effects. These limitations should be considered when comparing local fields to finite-element or TCAD calculations.
