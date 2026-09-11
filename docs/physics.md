# Physics model

## Overview

NCMemSim v0.10.0 implements a compact multiphysics model for distributed
floating-gate nanocrystal memories.

The current verified framework combines:

- electrostatic coupling between floating gates and external electrodes;
- local one-dimensional electric-field reconstruction;
- WKB-type tunnelling;
- nanocrystal charge-state kinetics;
- conservative inter-floating-gate charge redistribution;
- retention simulation;
- wavelength-dependent Ge/GeSn optical absorption;
- absorbed-photon generation;
- photo-assisted charge-state transitions;
- combined electrical and optical programming.

The model is intended for mechanism studies, controlled parameter sweeps,
retention analysis, electro-optical programming studies, and
design-technology co-optimization (DTCO).

It is a compact physical model rather than a self-consistent multidimensional
TCAD solver.

## Charge-state model

Each nanocrystal population is represented by three charge states:

\[
P_0,\qquad P_1,\qquad P_2,
\]

corresponding to zero, one, or two stored electrons.

At every floating-gate grid point,

\[
P_0 + P_1 + P_2 = 1.
\]

The occupancy engine evolves these probabilities using transition rates between
the charge states.

The compact electrical transition network includes:

\[
0 \rightleftarrows 1 \rightleftarrows 2.
\]

The simulator validates probability normalization and bounds throughout the
numerical workflow.

## Nanocrystal charging energy

The compact charging model uses the nanocrystal self-capacitance approximation

\[
C_{\mathrm{NC}}
\approx
4\pi\varepsilon_0\varepsilon_{\mathrm{cap}}R_{\mathrm{NC}},
\]

with charging energy

\[
E_c
=
\frac{q^2}{2C_{\mathrm{NC}}}.
\]

The effective capacitance permittivity is a model parameter and should not be
silently identified with either the bulk nanocrystal permittivity or the
surrounding dielectric permittivity.

Charging energy modifies the effective energetics of the second stored
electron and therefore contributes to Coulomb-blockade-like suppression of
higher occupancy.

## Floating-gate charge

For a local nanocrystal population, the mean electron occupation is

\[
\langle n \rangle
=
P_1 + 2P_2.
\]

Together with nanocrystal number density, electrically active fraction, and
elementary charge, this defines the local stored-charge density.

The simulator integrates the distributed charge to obtain the sheet charge of
each floating gate,

\[
Q_{\mathrm{FG},i},
\]

and the total floating-gate charge,

\[
Q_{\mathrm{FG}}
=
\sum_i Q_{\mathrm{FG},i}.
\]

The nanocrystal volume fraction used by the optical absorption model is
distinct from the electrically active fraction used by the charge-state model.

## Electrostatic coupling

The electrostatic model treats the device as an ordered one-dimensional
multilayer stack.

For a series dielectric stack, the equivalent capacitance per unit area follows

\[
\left(\frac{C_{\mathrm{eq}}}{A}\right)^{-1}
=
\sum_i
\frac{t_i}{\varepsilon_0\varepsilon_{r,i}}.
\]

Stored charge in each floating gate contributes to the electrostatic state and
to the compact flat-band shift.

For multiple floating gates, coupling is evaluated using the physical
positions and dielectric environment of the individual FG layers rather than
assuming a single lumped floating gate.

The resulting compact electrostatic solution supplies the state used by the
field and transport models.

## One-dimensional electric field

The field solver reconstructs a piecewise one-dimensional potential through the
ordered device stack.

The potential is constrained by the applied gate voltage and substrate
reference potential.

Local electric fields are obtained from the potential gradient and evaluated
at relevant interfaces and floating-gate positions.

The current implementation is one-dimensional and does not explicitly resolve
three-dimensional field enhancement around individual nanocrystals.

## Electrical tunnelling

Electrical charge injection and escape use a compact WKB-type tunnelling model.

For a barrier \(U(z)\), the transmission probability has the generic form

\[
T
\sim
\exp
\left[
-2
\int
\frac{\sqrt{2m^*[U(z)-E]}}{\hbar}
\,dz
\right].
\]

The implementation uses an effective one-dimensional barrier representation
appropriate to the compact model.

Transition rates depend on quantities including:

- barrier height;
- effective carrier mass;
- barrier thickness;
- local electric field;
- attempt frequency;
- field-coupling parameters;
- charge-state energetics.

The program and erase barriers are effective compact-model parameters. They
should not automatically be interpreted as independently measured interface
band offsets.

## Electrical occupancy kinetics

Electrical tunnelling produces local transition rates

\[
r_{01}^{\mathrm{elec}},
\qquad
r_{12}^{\mathrm{elec}},
\qquad
r_{21}^{\mathrm{elec}},
\qquad
r_{10}^{\mathrm{elec}}.
\]

These rates evolve the three-state probability distribution.

The occupancy update preserves the physical probability constraints and is
designed to remain independent of the high-level simulation workflow.

This separation allows the same kinetics engine to be used by:

- fixed-voltage relaxation;
- voltage sweeps;
- C-V simulation;
- retention;
- electro-optical programming.

## Inter-floating-gate transport

For devices containing multiple floating gates, NCMemSim represents charge
transfer through an explicit transport network.

Transport nodes represent:

- the substrate;
- individual floating gates;
- external reservoirs where applicable.

Tunnel links describe allowed transfers between nodes.

Inter-floating-gate redistribution is availability limited and conservative:
charge transferred out of one internal floating gate is transferred into
another rather than being numerically created or destroyed.

Charge-conservation checks are part of the validation framework.

## Retention

Retention simulation advances the coupled device state at fixed external bias,
normally zero gate bias.

The retention solver supports increasing timesteps so that short-time
transients and long-time evolution can be represented efficiently.

At every retention step, the simulator may update:

- electrostatic coupling;
- local fields;
- tunnelling rates;
- occupancy;
- inter-floating-gate redistribution.

Retention therefore evolves from the current physical state rather than from a
fixed analytical decay constant.

The compact retention model remains subject to the transport mechanisms
implemented in the current release; additional defect-assisted mechanisms are
not implicitly included.

## Optical source model

NCMemSim v0.10.0 adds monochromatic optical excitation through `LightSource`.

For wavelength \(\lambda\), photon energy is

\[
E_\gamma
=
\frac{hc}{\lambda}.
\]

For incident optical power density \(P_{\mathrm{opt}}\), the incident photon
flux is

\[
\Phi_\gamma
=
\frac{P_{\mathrm{opt}}}{E_\gamma}.
\]

The current verified Phase E implementation focuses on monochromatic sources
such as compact LED and laser representations.

Broadband spectral integration is not part of the v0.10.0 verified optical
model.

## Ge/GeSn optical response

The optical material model is separate from the compact electronic band-gap
representation used by the electrical model.

The Ge/GeSn absorption coefficient is decomposed as

\[
\alpha(E)
=
\alpha_{\Gamma}(E)
+
\alpha_L(E)
+
\alpha_U(E),
\]

where:

- \(\alpha_{\Gamma}\) represents direct-Gamma absorption;
- \(\alpha_L\) represents indirect phonon-assisted absorption;
- \(\alpha_U\) represents Urbach-tail absorption.

Direct and indirect optical gaps are evaluated independently as functions of
GeSn composition.

The indirect contribution includes temperature-dependent phonon occupation.

The direct-gap composition model is literature based, while the indirect model
is literature informed. Absolute absorption amplitudes remain compact-model
parameters and are not yet experimentally calibrated for a specific device.

## Floating-gate optical absorption

For a floating-gate layer containing absorbing nanocrystals in a dielectric
matrix, the effective absorption coefficient is

\[
\alpha_{\mathrm{eff}}
=
f_{\mathrm{NC}}
\alpha_{\mathrm{NC}},
\]

where:

- \(f_{\mathrm{NC}}\) is the nanocrystal volume fraction;
- \(\alpha_{\mathrm{NC}}\) is the nanocrystal absorption coefficient.

The absorbed fraction for floating-gate thickness \(t_{\mathrm{FG}}\) follows
the Beer-Lambert relation

\[
A
=
1-\exp
\left(
-\alpha_{\mathrm{eff}}t_{\mathrm{FG}}
\right).
\]

The absorbed photon flux is therefore

\[
\Phi_{\mathrm{abs}}
=
A\Phi_\gamma.
\]

The average volumetric generation rate is obtained from the absorbed photon
flux and floating-gate thickness.

The model also evaluates the absorbed photon rate per nanocrystal using the
nanocrystal number density.

## Photo-assisted charge-state transitions

Absorbed photons generate an additional compact contribution to the occupancy
transition rates.

The photo-assisted rates are represented by

\[
r_{ij}^{\mathrm{photo}}.
\]

The default v0.10.0 photo-loading model enables:

\[
0 \rightarrow 1
\]

and

\[
1 \rightarrow 2.
\]

Photo-assisted detrapping is disabled by default but the transition weighting
is configurable.

A compact photo-capture efficiency converts absorbed-photon rate per
nanocrystal into photo-assisted transition rate.

This efficiency is phenomenological in v0.10.0 and is not experimentally
calibrated by default.

## Coupled electro-optical kinetics

Electrical and optical contributions are additive:

\[
r_{ij}
=
r_{ij}^{\mathrm{elec}}
+
r_{ij}^{\mathrm{photo}}.
\]

This allows the same occupancy engine to represent three operating modes:

- electrical-only programming:
  \(V_g \neq 0\), optical source absent or disabled;
- optical-assisted programming at zero gate bias:
  \(V_g = 0\), optical source enabled;
- electro-optical programming:
  \(V_g \neq 0\), optical source enabled.

The optical rates are evaluated consistently with the selected floating-gate
material, geometry, nanocrystal size, wavelength, optical power density, and
photo-transition configuration.

## Optical diagnostics

The simulator exposes optical diagnostics for each floating gate, including:

- optical absorption fraction;
- incident and absorbed photon flux;
- absorbed photon rate per nanocrystal;
- photo-transition rate;
- nanocrystal absorption coefficient;
- effective floating-gate absorption coefficient.

Scalar convenience diagnostics are also available for workflows where a
single aggregate value is useful.

For a dark simulation:

- optical photon flux is zero;
- photo-transition rates are zero.

For a disabled source with a defined wavelength:

- photon flux is zero;
- photo-transition rates are zero;
- wavelength-dependent material absorption properties may remain defined.

## Voltage dependence of the optical model

In v0.10.0, optical material properties depend on wavelength, composition, and
the parameters of the selected optical material model.

For a fixed source and material, the absorption coefficient and corresponding
base photo-assisted rate are not explicitly modified by gate voltage.

Consequently, the current optical model does not include field-dependent
optical effects such as:

- Franz-Keldysh absorption;
- Stark shifts;
- field-dependent band-edge modification.

If such effects are introduced later, the assumption of voltage-independent
optical absorption will need to be revised explicitly.

## Multi-floating-gate optical assumption

The current multi-FG optical implementation evaluates each floating gate using
the same incident optical source.

It does not yet propagate the transmitted spectrum sequentially through the
complete multilayer stack.

Therefore, for multiple floating gates, the current implementation does not
model optical shadowing or attenuation of downstream floating gates by
upstream floating gates.

This is an explicit compact-model assumption rather than an implicit numerical
approximation.

## SWIR validation

Phase E6 validates the optical implementation in the SWIR spectral region.

The validation includes:

- wavelength-dependent photon energy;
- wavelength-dependent incident photon flux;
- non-negative absorption coefficients;
- non-negative absorbed photon flux;
- non-negative photo-assisted rates;
- composition-dependent extension of GeSn absorption toward longer
  wavelengths;
- consistency between absorbed photon rate and photo-transition rate;
- electrical-only versus electro-optical programming;
- optical-assisted programming at zero gate bias;
- preservation of probability normalization;
- programming-voltage-reduction benchmarks.

For the compact direct-gap model, representative cutoff wavelengths are
approximately:

| Material | Direct-gap cutoff |
|---|---:|
| Ge | 1553 nm |
| GeSn 4% | 1940 nm |
| GeSn 8% | 2536 nm |
| GeSn 12% | 3564 nm |

These values describe the implemented compact model. They are not independent
experimental measurements.

The 12% Sn case extends beyond the principal 0-10% Sn experimental composition
range used for guidance and should therefore be treated as extrapolative.

## Programming-voltage-reduction benchmark

The v0.10.0 SWIR benchmark demonstrates that photo-assisted loading can reduce
the electrical gate voltage required to reach a selected common occupation
target.

For the benchmark GeSn 8% device:

| Wavelength | Photo rate (s^-1) | Vdark (V) | Vlight (V) | Delta V (V) |
|---:|---:|---:|---:|---:|
| 1300 nm | 3.092040e-07 | 3.9124 | 3.8343 | 0.078071 |
| 1550 nm | 3.506618e-07 | 3.9124 | 3.8238 | 0.088539 |
| 1700 nm | 3.684289e-07 | 3.9124 | 3.8193 | 0.093025 |

The benchmark uses

```text
photo_capture_efficiency = 1e-10
```

to place the dark and illuminated curves within a common occupation range.

This value is a benchmark coupling parameter and is **not experimentally
calibrated**.

The voltage reductions therefore demonstrate internal model behaviour,
spectral consistency, and electro-optical coupling rather than absolute
experimental predictive accuracy.

## Numerical integration

Transient occupancy updates use explicit simulation timesteps controlled by
the simulation configuration.

When a requested dwell interval is divided into internal steps, the effective
step is chosen so that the integrated duration equals the requested dwell
time:

\[
\Delta t_{\mathrm{actual}}
=
\frac{t_{\mathrm{dwell}}}{N_{\mathrm{steps}}}.
\]

This convention is covered by regression testing and avoids the legacy V5.3
timestep inconsistency identified during v0.9.1 release validation.

## Model validation

The physical kernels are validated at several levels:

- unit tests for individual equations and limiting cases;
- state and geometry invariants;
- electrical regression against the retained V5.3 reference;
- deterministic multi-FG golden cases;
- charge-conservation tests;
- retention tests;
- optical-source tests;
- Ge/GeSn spectral-response tests;
- absorbed-photon and photo-rate tests;
- electro-optical programming tests;
- SWIR wavelength and voltage-reduction benchmarks.

The v0.10.0 validation suite contains **194 tests** covering Phases A through
E6.

Passing these tests establishes consistency with the implemented compact model
and approved regression baselines. It does not establish experimental accuracy
for every physical parameter or fabricated device.

## Current model limitations

The v0.10.0 model intentionally does not include all physical mechanisms that
may influence a real nanocrystal memory.

Important current limitations include:

- one-dimensional compact electrostatics rather than multidimensional
  self-consistent TCAD;
- effective WKB barriers rather than a complete quantum-transport solution;
- no explicit trap-assisted tunnelling model;
- no image-force barrier lowering unless represented through an effective
  parameter;
- no stochastic nanocrystal-size or position ensemble;
- no self-consistent many-body carrier statistics;
- no explicit nanocrystal quantum-confinement correction in the optical model;
- no explicit strain-dependent optical-gap correction;
- no Franz-Keldysh optical absorption;
- no Stark-shift model;
- no state-filling optical correction;
- no full multilayer electromagnetic propagation;
- no sequential optical attenuation through multiple floating gates;
- provisional absolute optical absorption amplitudes;
- phenomenological, uncalibrated default photo-capture efficiency;
- no device-specific experimental calibration in the current release.

These limitations define the interpretation range of v0.10.0 results and
should be reported when the simulator is used in scientific publications.

## Interpretation of results

NCMemSim results should be interpreted according to the provenance and
calibration status of the underlying parameters.

A numerical result can demonstrate:

- implementation correctness;
- internal physical consistency;
- sensitivity to a parameter;
- relative trends;
- mechanism competition;
- electrical versus electro-optical behaviour;
- reproducible DTCO comparisons.

It should not automatically be described as an experimentally predictive
result unless the relevant material and device parameters have been calibrated
against suitable measurements.

The planned experimental-fitting stage will provide the framework for making
that distinction quantitative.
