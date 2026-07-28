# Scientific scope and modelling assumptions

NCMemSim is a compact multiphysics simulator for planar nanocrystal non-volatile memories. It is intended for **mechanism studies, parameter sweeps, retention analysis, and design–technology co-optimization (DTCO)**. It is not a replacement for a self-consistent multidimensional TCAD solver.

## Supported device class

The current implementation targets one-dimensional gate stacks containing one to three distributed floating-gate (FG) layers. Each FG is represented by an ensemble of nanocrystals embedded in a dielectric layer and discretized along the layer thickness.

Two device families are supported by the builder and explicit layer model:

- **V1:** gate / HfO₂ / SiO₂ / repeated FG–tunnel stack / Si;
- **V2:** gate / SiO₂ / repeated FG–tunnel stack / Si.

The internal representation is an ordered list of layers, so the physics engines operate on geometry rather than on hard-coded architecture branches.

## State variables

For every spatial point in each FG, the simulator evolves three probabilities:

\[
P_0,\qquad P_1,\qquad P_2,
\]

corresponding to zero, one, or two stored electrons in the compact occupancy model. The invariant

\[
P_0+P_1+P_2=1
\]

is checked by the state and validation layers.

The normalized local occupation used by the charge model is

\[
m=\frac{P_1+2P_2}{2}.
\]

## Coupled physics currently implemented

The v0.9.1 scientific kernel combines:

1. layer-resolved one-dimensional electrostatics;
2. centroid-weighted coupling between FG charge and flat-band shift;
3. local potential and electric-field reconstruction;
4. compact WKB transmission estimates;
5. occupancy kinetics for substrate injection and emission;
6. conservative nearest-neighbour FG-to-FG redistribution;
7. adaptive retention integration;
8. validation, golden references, benchmarking, and reproducibility manifests.

## Deliberate approximations

The current release uses compact constitutive relations and therefore makes the following approximations:

- lateral non-uniformity and fringing fields are neglected;
- nanocrystals are treated statistically rather than as an explicit 3D ensemble;
- the electrostatic solution is layer-resolved and one-dimensional;
- tunnelling barriers are compact WKB barriers rather than solutions of a full quantum transport problem;
- substrate exchange is represented through the occupancy kinetics engine;
- inter-FG transport is restricted to nearest-neighbour links;
- thermal, trap-assisted, and many-body corrections are not yet general-purpose models;
- optical programming, experimental fitting, and automated DTCO are roadmap features rather than completed production capabilities.

## Appropriate uses

NCMemSim is appropriate for:

- comparing 1–3 FG architectures;
- studying the effect of FG position, thickness, density, and material;
- estimating memory-window trends;
- examining local field redistribution;
- testing qualitative transport pathways;
- simulating charge redistribution during retention;
- producing deterministic reference cases for model development.

Results should be interpreted as model predictions under documented assumptions. Quantitative agreement with experiment requires parameter provenance, uncertainty assessment, and calibration against the measured device.
