# Materials and parameter provenance

## Material objects

NCMemSim distinguishes bulk/dielectric `Material` objects from `NanocrystalMaterial` objects. Built-in public constructors and presets include:

- `SILICON`
- `SIO2`
- `HFO2`
- `make_ge()`
- `make_gesn(sn_fraction)`

The registry can construct composition-dependent materials by name, while the model modules provide interpolation, band alignment, and compact optical-property evaluation.

## GeSn composition

`make_gesn(x)` uses a Sn atomic fraction `x`, for example:

```python
from ncmemsim import make_gesn

gesn_2pct = make_gesn(0.02)
gesn_10pct = make_gesn(0.10)
```

A composition-dependent value is a model output, not a universal constant. The selected interpolation law and its source should be recorded when reporting scientific results.

## Provenance

The material framework was designed so that parameters can carry provenance metadata. A reproducible parameter should ideally record:

- value and unit;
- source or citation;
- model or interpolation rule;
- composition and temperature range;
- whether the value is measured, fitted, assumed, or inherited;
- uncertainty when available.

The reproducibility manifest includes material-model information and hashes the device definition. A scientific workflow should save the manifest together with numerical results.

## Band alignment

Compact barrier heights can be generated with band-alignment helpers such as an electron-affinity rule. These are model choices and should not be confused with experimentally measured offsets for every specific interface.

Example:

```python
from ncmemsim import make_gesn
from ncmemsim.materials import BarrierModel, HFO2

alignment = BarrierModel.affinity_rule(make_gesn(0.10), HFO2)
```

## Optical material models

The Phase C package contains compact optical-model infrastructure, but full optical programming is not implemented in v0.9.1. Optical-property evaluation should presently be treated as a foundation for Phase E rather than a validated coupled photoprogramming solver.

## Adding a material

A new material model should provide:

1. an unambiguous identifier;
2. SI-unit parameters;
3. provenance metadata;
4. composition and temperature validity ranges;
5. tests at endpoints and representative intermediate values;
6. documentation of extrapolation behaviour;
7. a registry entry only after the model is stable enough for public use.
