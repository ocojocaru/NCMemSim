<p align="center">
  <img src="assets/banner.svg" alt="NCMemSim — Nanocrystal Memory Simulation Platform" width="100%">
</p>

# NCMemSim

**Nanocrystal Memory Simulation Platform**

NCMemSim is a modular Python framework for the simulation and design–technology co-optimization (DTCO) of Ge/GeSn nanocrystal non-volatile memories. It provides an explicit multilayer device description, independent state variables for one to three floating gates, compact electrostatics, local field reconstruction, WKB-based tunnelling, inter-floating-gate charge redistribution, retention analysis, validation utilities, reproducibility manifests, and deterministic regression references.

> **Current release:** `0.9.1` — Repository Polish, Sprints R1–R6  
> **Scientific status:** research software under active development; Phase D physics and validation are implemented.

## Why NCMemSim?

Distributed floating-gate memories couple material composition, nanocrystal geometry, dielectric-stack design, local electrostatics, tunnelling barriers, charge-state kinetics, and retention. NCMemSim separates these concerns into testable modules so that a device can be explored reproducibly instead of being hard-coded into one monolithic script.

The framework is intended for:

- Ge and GeSn nanocrystal floating gates;
- one-, two-, and three-floating-gate stacks;
- HfO2/SiO2 dielectric architectures;
- compact C–V and memory-window studies;
- local electric-field and potential analysis;
- WKB tunnelling and inter-FG transport;
- retention and charge-redistribution studies;
- future optical programming, experimental fitting, and design-space exploration.

## Implemented capabilities

| Area | Available in v0.9.1 |
|---|---|
| Device construction | V1 and V2 architectures, 1–3 floating gates |
| Materials | Si, SiO2, HfO2, Ge, composition-dependent GeSn |
| State model | Independent `P0`, `P1`, `P2` arrays for each FG |
| Electrostatics | Compact coupling and flat-band shift decomposition |
| Local fields | 1D potential and electric-field profiles |
| Tunnelling | WKB-based tunnelling engine |
| Transport | Nearest-neighbour FG↔FG tunnel network |
| Retention | Adaptive time integration with logarithmic outputs |
| Validation | Probability, device, field, and charge-conservation checks |
| Reproducibility | Device/simulation hashes and runtime manifest |
| Regression | Golden reference suite and benchmark utilities |

Optical programming, parameter fitting, automated DTCO, and advanced quantum corrections are roadmap items and should not be interpreted as implemented production features.

## Installation

NCMemSim requires Python 3.11 or newer.

```bash
python -m venv .venv
```

Activate the environment, then install the project from the repository root:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

For development tools:

```bash
python -m pip install -e ".[dev]"
```

## Quick start

The following example builds a three-FG V2 device, assigns an initial programmed state, and runs a retention simulation:

```python
from ncmemsim import DeviceBuilder, DeviceState, RetentionConfig, Simulator

# Gate / SiO2 / (FG / tunnel SiO2)^3 / Si
device = DeviceBuilder.v2(
    n_fgs=3,
    control_sio2_nm=25.0,
    inter_fg_sio2_nm=1.5,
    tunnel_sio2_nm=7.0,
)

state = DeviceState.empty_for_device(device)
for fg_state, occupation in zip(state.floating_gates, (0.75, 0.45, 0.20)):
    fg_state.P0[:] = 1.0 - occupation
    fg_state.P1[:] = occupation
    fg_state.P2[:] = 0.0

result = Simulator(device).simulate_retention(
    state,
    RetentionConfig(
        total_time_s=1.0e4,
        initial_dt_s=1.0e-6,
        maximum_dt_s=100.0,
        output_points=61,
    ),
)

print(result.qfg_C_m2[-1])
print(result.mean_occupation_by_fg[-1])
print(result.total_charge_retention_fraction)
```

See [`docs/quickstart.md`](docs/quickstart.md) and the executable files in [`examples/`](examples/) for electrostatic coupling, local fields, transport, retention, validation, and material-model workflows.

## Package architecture

<p align="center">
  <img src="assets/architecture.svg" alt="NCMemSim software architecture" width="92%">
</p>


The package exposes a deliberately small public API through `ncmemsim.__init__`; internal modules remain independently testable. The supported device families are summarized below.

<p align="center">
  <img src="assets/device-stack.svg" alt="Supported V1 and V2 nanocrystal memory stacks" width="88%">
</p>

## Scientific model at a glance

Each floating gate uses three charge-state probabilities:

\[
P_0 + P_1 + P_2 = 1,
\]

with mean occupation represented by the model as

\[
m = \frac{P_1}{2} + P_2.
\]

The compact electrostatic model decomposes the flat-band shift into per-FG contributions and reconstructs local fields across the multilayer stack. Tunnelling probabilities are evaluated with WKB-type barrier integrals, while inter-FG redistribution is solved through an explicit nearest-neighbour transport network. Retention integrates the coupled state in time with adaptive step growth and logarithmically spaced outputs.

The equations, assumptions, conventions, and current limitations are documented in [`docs/physics.md`](docs/physics.md).

## Validation and reproducibility

The Phase D6 validation layer includes:

- state-normalization and physical-consistency checks;
- field-profile checks;
- internal charge-conservation checks;
- deterministic golden cases for one-, two-, and three-FG devices;
- a short retention reference trajectory;
- runtime and traced-memory benchmarks;
- reproducibility manifests with software, platform, device, and simulation hashes.

Run the test suite with:

```bash
python -m pytest -q
```

Generate validation artifacts with:

```bash
python scripts/generate_golden.py
python scripts/run_benchmarks.py
python scripts/reproduce_paper_figures.py
```

## Visual identity and diagrams

Canonical project artwork and reusable scientific schematics are stored in [`assets/`](assets/). Usage guidance is available in [`BRANDING.md`](BRANDING.md).

## Documentation

The documentation source is in `docs/` and is configured for MkDocs Material.

```bash
python -m pip install mkdocs mkdocs-material
mkdocs serve
```

Main sections:

- [Installation](docs/installation.md)
- [Quick start](docs/quickstart.md)
- [Architecture](docs/architecture.md)
- [Physics](docs/physics.md)
- [Materials](docs/materials.md)
- [Validation](docs/validation.md)
- [Public API](docs/api.md)
- [Developer guide](docs/developer.md)
- [Roadmap](docs/roadmap.md)

## Roadmap

| Release | Scope | Status |
|---|---|---|
| v0.9.0 | Phase D6 validation baseline | Complete |
| v0.9.1 | Repository polish, documentation, GitHub infrastructure, branding and release engineering | Complete |
| v0.10.0 | Optical programming engine | Planned |
| v0.11.0 | Experimental fitting | Planned |
| v0.12.0 | Design-space exploration / DTCO | Planned |
| v1.0.0 | First stable scientific release | Planned |

See [`VISION.md`](VISION.md) for the long-term scientific direction.

## Contributing

Contributions should preserve physical traceability, numerical reproducibility, and backward compatibility unless a breaking change is explicitly approved. Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before submitting changes.

## Citation

Citation metadata is provided in [`CITATION.cff`](CITATION.cff). Until a DOI-backed software release or associated article is available, cite the repository and the exact software version used.

## License

NCMemSim is licensed under the [Apache License 2.0](LICENSE).
