# Platform status - NCMemSim v1.10.0

Documentation consolidated on 2026-11-05 against published v1.10.0 and metadata
closure commit `46ec695aba82978e1bb115bb5647f7fed69f0898`.
Latest stable: **1.10.0**, published 2026-11-05. Phase S7 is complete.
[GitHub release](https://github.com/ocojocaru/NCMemSim/releases/tag/v1.10.0)
contains wheel and sdist. Version DOI:
[10.5281/zenodo.23973765](https://doi.org/10.5281/zenodo.23973765).
[Concept DOI](https://doi.org/10.5281/zenodo.23078330) remains separate.
Main CI 42000134152 and Documentation 42000134173 passed on the closure commit.
The immutable release tag points to `ba1b9ea9563f3786fb4af96215606b103a2925a2`;
later metadata/documentation commits do not move that tag or replace its assets.

## Implemented capabilities and boundaries

| Area | Available in v1.10.0 | Interpretation and limits |
|---|---|---|
| Device/state/electrostatics | Explicit multilayer geometry, one to three FG reference families, independent state, compact electrostatics and local fields | Compact one-dimensional modelling; no full TCAD or self-consistent quantum transport |
| Programming/retention | Electrical, optical and electro-optical kinetics, pulse/read protocols and coupled retention | Parameter-sensitive simulated response; no universal lifetime or endurance prediction |
| TAT and image-force corrections (v1.1) | Explicit opt-in attachment, mechanism diagnostics, sensitivity and reports | Conditional compact frequencies/fluxes; no independent experimental qualification |
| Variability (v1.2-v1.3) | Stochastic ensembles, population accounting and explicit MODEL/TAT variability | Supported bindings only; no manufacturing-yield interpretation |
| Temperature (v1.4) | Reference-anchored Si/Ge properties and owned thermal contexts/DTCO/reports | Opt-in profiles and declared domains; no implicit universal material law |
| Broadband optics (v1.5) | Discrete/broadband sources, single-layer accounting, ordered sequential stack propagation and spectral contexts/reports | Explicit passive losses; no coherent interference, scattering or full-wave propagation |
| Structural optical diagnostics (v1.6) | Hydrostatic strain-induced transition shifts, spherical kinetic confinement, owned optical/spectral contexts and reports | No general strain band structure, interacting finite-barrier confinement or automatic transport barrier inference |
| Independent calibration (v1.7) | Data admission, optical training/holdout, device/photo infrastructure, synthetic OM-2 studies and reports | Independent experimental P4B/P5B/P6B qualification remains deferred |
| Multilevel/neuromorphic (v1.8) | State-continuing electrical/matched optical sequences, level separation, update and retention/ensemble diagnostics/reports | Weight proxies are not physical conductance, circuit MAC or a trained neural network |
| Performance/interoperability (v1.9) | Serial measurements, scoped report-restoration optimization, vendor-neutral exchange, controlled comparisons and reports | Historical same-host performance evidence; no universal speedup or real TCAD agreement |
| Explicit barriers (v1.10) | Owned piecewise-linear electron profiles, stable action/exponent/log-T evaluation, controlled sensitivity and opt-in direct inter-FG replacement | Explicit snapshot/geometry mapping; no substrate replacement, TAT composition, automatic voltage law or microscopic supply model |
| Reproducibility | Source-linked JSON, projections, manifests, failure accounting and portable archives | Consistency checks are not authentication; undefined, failed and unavailable values remain distinct |

## Choose the correct path

The retained default `LightSource` path evaluates each FG independently. For
sequential attenuation choose the explicit [spectral workflow](broadband_optics.md).
Temperature and structural profiles also require their explicit contexts. Published
extensions do not silently change the default simulator or compose every mechanism.

For barriers, the [S2 isolated evaluator](barrier_transport.md) produces actions and
transmissions; [S4 attachment](barrier_transport_integration.md) is a separate opt-in
transport decision. [S6 reports](barrier_reporting.md) archive isolated actions,
not simulator/provider histories. None of these paths establishes a device current
or measured accuracy merely by being numerically reproducible.

## Start a study

- [Installation](installation.md), [quick start](quickstart.md) and [API](api.md).
- [Scientific scope](scientific_scope.md), [materials](materials.md) and [physics](physics.md).
- [DTCO](dtco.md), [Robust DTCO](robust_dtco.md) and [source-linked workflows](scientific_workflows.md).
- [Optical/thermal/structural studies](architecture.md), [multilevel operation](multilevel_operation.md).
- [Independent data and qualification](independent_calibration.md).
- [Reproducibility](reproducibility.md), [validation](validation.md) and [release checklist](v1_10_release_checklist.md).

## Historical evidence and remaining work

Version-specific test counts, archived measurements, release checklists, approved
contracts, source hashes and original fixtures retain their original scope. They
are not current total test counts or claims that a previously completed stage is
still pending. See the [documentation inventory](documentation_status.md).
The [roadmap](roadmap.md) separates delivered work from remaining research.
Post-v1.10 development includes the [Phase T1–T6 finite-confinement solver, optical context, studies and reports](finite_confinement.md)
for isolated finite-barrier ground states. The v1.11.0 candidate includes these extensions.
See the [release checklist](v1_11_release_checklist.md).
