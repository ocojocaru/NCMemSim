# Scientific defaults, units and parameter provenance review

This review records version 0.14.0 behavior during v1.0 preparation. Values
below are compatibility baselines, not newly validated physical constants or
recommended parameters for a particular experimental device. No algorithms,
parameter values or scientific labels are changed by this audit.

## Device and material defaults

Device defaults are gate_work_function_eV=4.8 eV, substrate_doping_m3=1e21
m^-3 and temperature_K=300 K. V1/V2 builders accept one to three floating gates.

| Builder | Ordered thicknesses, in nm |
|---|---|
| V1 | control HfO2 35, control SiO2 3, each FG 15, inter-FG SiO2 4 then HfO2 4, tunnel HfO2 10, native SiO2 2 |
| V2 | control SiO2 20, each FG 12, inter-FG SiO2 4, tunnel SiO2 8 |

Both builders default to Ge nanocrystals, diameter 5 nm, volume fraction 0.60,
electrically active fraction 0.22 and grid_points=31. Their layer profile is
explicitly uniform. It overrides KineticsConfig.density_profile=front_loaded;
constructing PhysicsModel.default does not turn these builder layers into a
front-loaded profile. V1 FG matrix is HfO2; V2 FG matrix is SiO2.

The v5.3 regression device is a distinct CUSTOM definition: substrate doping
1.2e21 m^-3, NC diameter 3 nm, front_loaded profile, effective FG permittivity
18 and program/erase barriers 1.78/2.10 eV. It is not an alias of V1.
Its historical material metadata does not supply typed property provenance.

Default database properties for Ge, alpha-Sn, Si, SiO2 and HfO2 carry ASSUMED
provenance, no DOI and no reported uncertainty. make_ge uses default program
and erase barriers 2.8 eV. GeSn electronic properties use provisional endpoint
interpolation and bowing; the default bandgap bowing is 2.4 eV. This electronic
bandgap model is separate from the optical Gamma/L parameterization.
A user-supplied barrier or parameter-set name does not promote ASSUMED records
to FITTED or CALIBRATED. In the legacy material builders, model_version/custom
metadata can change while property provenance.parameter_set remains default-v1.
Record actual values and model identity as well as property provenance.

## Reviewed configuration baseline

| Configuration | Current defaults and units |
|---|---|
| SemiconductorConfig | silicon_eps_r 11.7; intrinsic_density_m3 1e16 m^-3; affinity 4.05 eV; bandgap 1.12 eV; psi_max 0.9 V; transition_voltage 0.65 V; transition_width 0.22 V; accumulation_factor 40 |
| TunnelingConfig | injection_energy 0.10 eV; oxide mass 0.15 m0; integration_points 160; field_coupling_factor 0.80; activation_beta 0.8 V^-1 |
| KineticsConfig | nu0 1e12 Hz; nu1 1e10 Hz; nu2 3e9 Hz; capacitance_eps_r 8; density_profile front_loaded |
| TransportConfig | enabled true; attempt_frequency 1e9 Hz; barrier 1.78 eV; mass 0.15 m0; direction_beta 8 V^-1; max_transfer_fraction_per_step 0.10; include_substrate_diagnostics true |
| SimulationConfig | dwell_time 0.005 s; internal_dt 1e-5 s; qfix and qit 0 C/m^2 |
| RetentionConfig | gate_voltage 0 V; total_time 1e4 s; initial_dt 1e-9 s; maximum_dt 1e3 s; growth_factor 2; output_points 121; quasi_equilibrium_tolerance 1e-18 C/(m^2 s); quasi_equilibrium_steps 4; stop_at_quasi_equilibrium false; occupancy_integrator backward_euler |
| PhotoTransitionConfig | photo_capture_efficiency 1e-3, dimensionless |
| PhotoTransitionWeights | loading r01/r12 1; detrapping r10/r21 0, dimensionless |

These dataclass configurations do not embed ParameterProvenance. A positive
value, a default setting or a successful run does not establish experimental
calibration. Retention output_points specifies requested output sampling;
actual returned count and early stopping are covered by
[result contracts](api_results.md). The transport substrate link is diagnostic;
existing substrate/FG kinetics remain responsible for injection and emission.

## Unit and sign boundaries

Geometric inputs named *_nm are nanometres and are explicitly converted to
metres internally. Densities are per cubic metre; charges are sheet charge
C/m^2; capacitance is F/m^2; local fields are V/m; times are seconds. Relative
permittivities, volume/active/Sn fractions and probabilities are dimensionless.
The mass label m0 means a multiple of the electron rest mass, not kilograms.

The physical NC density is volume_fraction divided by spherical NC volume.
Electrically active density multiplies it by active_fraction. Photo generation
per composite volume is divided by the physical NC density to obtain photons
per NC per second; it is not divided by active density. Multiplication by
photo_capture_efficiency gives an effective transition rate in s^-1. That
parameter is a useful-event efficiency, not optical absorptance or a measured
external quantum efficiency. It is a fitted model parameter, not illumination
protocol input. Default weights enable loading, not optical detrapping.

Monochromatic photon energy uses hc/lambda with lambda converted from nm to m.
Incident power density in W/m^2 divided by energy in J gives photons/(m^2 s).
The disabled source reports zero photon flux. A broadband source does not have
one monochromatic photon energy. Absorption coefficients are in m^-1, not
cm^-1. Specific model prefactors can have additional powers of eV; preserve
their declared unit strings instead of treating all coefficients as m^-1.

Electron sheet charge is negative. Negative FG charge raises flat-band voltage
and lowers gate-minus-flat-band effective voltage in the reviewed convention.
The scalar helper uses vfb=vfb0-qfg/cox; multi-FG results use their coupling
model and must not be replaced with an unweighted sum. qfix/qit enter baseline
flat-band voltage through their sum. Occupancy rates have units s^-1; WKB
transmissions tprog/terase are dimensionless, not programming/erase times.

## Provenance is a declaration with a scope

| ParameterStatus | Interpretation to retain |
|---|---|
| assumed | provisional model choice |
| estimated | estimated value with its declared source |
| literature | declared literature source for that specific property or model relation |
| literature_fitted | parameter fit reported in the declared literature source |
| fitted | fit to the declared dataset/model, not automatically calibrated |
| calibrated | declared calibration provenance; verify its qualification/applicability evidence |
| derived | value derived from a stated relation/source, not independently measured |

Status serialization uses lowercase values; workflow scientific summaries use
uppercase FITTED/CALIBRATED labels. Do not conflate these representations.
A literature citation for absorption decomposition does not make provisional
absorption amplitudes literature-exact. Existing absorption model provenance
is LITERATURE while its amplitude provenance is ASSUMED. This audit checks the
code's attribution and scope; it does not independently revalidate cited papers.
Temperature/strain/domain limits of optical parameterizations remain applicable
when device temperature or composition is changed. A configured 300 K optical
parameter set is not an automatic temperature-dependent experimental model.

ParameterProvenance reported_uncertainty=None omits that field, while zero is
explicitly serialized. An uncertainty unit requires a finite nonnegative
uncertainty; a fit standard error is not automatically a reported measurement
uncertainty. Legacy provenance accepts declarations without independently
verifying source identity, DOI, applicability or calibration qualification.
MaterialProperty itself does not enforce universal unit conversion or finite
value validation. Raw configuration validation is likewise class-specific;
this patch does not claim every legacy constructor rejects all nonfinite or
physically implausible values. Additional hardening needs compatibility review.

Device.to_dict/layer summaries contain material names and selected scalar
properties, not a universal lossless typed-provenance archive. For fitted
application and portable reporting retain the typed source/application
[workflow evidence](scientific_workflows.md), actual configuration, device
variants and [archive schemas](api_archives.md). Applying numeric values or
creating a DeviceCalibrationSpec alone does not assign fitted/calibrated
provenance. Synthetic references remain synthetic FITTED evidence.

## Remaining v1.0 gates

Tests retain the eight configuration defaults, six builder combinations,
profile precedence, reference-device distinction, declared status preservation,
missing-versus-zero uncertainty, model/coefficient attribution boundaries,
unit conversion, charge signs and physical-versus-active density conventions.
Existing calibration plumbing/qualification tests cover non-promotion and
explicit domain promotion. No new scientific validation claim is made.

Final review must approve the intended stable defaults and model applicability,
resolve any planned legacy validation/provenance hardening separately, and
run full supported-runtime, documentation and installed-distribution checks.
Regression compatibility alone is not experimental predictive validation.
