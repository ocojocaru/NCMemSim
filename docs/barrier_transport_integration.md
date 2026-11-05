# Opt-in explicit barrier transport - Phase S4

## Accepted first scope

S4 implements six module-qualified exports in `ncmemsim.barrier_transport`:
`BarrierTransportContext`, `BarrierLinkAttachment`, `BarrierTransportSpec`,
`ProfiledLinkTransportResult`, `ProfiledTransportStepResult` and
`BarrierTransportEngine`. Existing package-root/transport exports, source modules,
defaults, citation identity and old archives are unchanged. The baseline is S3
commit `47887342540c4b140ab8f991b9f5cfbde59a82be`, with successful CI/Documentation.
Current package identity remains 1.9.0; the next version is still provisional.

The wrapper accepts a plain published `TransportEngine`/`TunnelingEngine` and,
optionally, a provider callable with a nonempty declared identifier. No provider
means exact delegation to the baseline, including its result types and update.
A provider can return an explicitly disabled `BarrierTransportSpec` with no
attachments; the state update then delegates to the published baseline as well.
No default physics factory is changed.

## Current context, not a cached bias profile

For each evaluation/step the provider receives an owned `BarrierTransportContext`.
Its JSON snapshot contains the public and full dataclass device/material
declarations, complete state arrays/metadata, current field profile, network,
direct/tunnelling/occupancy configurations and computed sheet-site densities.
Native arrays and enums are converted explicitly; arbitrary objects are rejected,
not coerced with repr. Access returns independent copies, not live arrays.

The provider returns a `BarrierTransportSpec` with that exact context hash and
ordered unique link attachments. A plan for a different state, time, bias, material,
temperature or configuration is rejected before transport advancement. Material
names alone are insufficient: full material declarations are included. The provider
is invoked again for subsequent runtime calls; no profile cache is silently reused.

Providers are ordinary trusted, side-effect-free Python callables, not sandboxed
or serialized executable physics. The engine detects changed live inputs during
the callback and rejects the evaluation, but does not promise rollback of arbitrary
external side effects. Provider identifiers are provenance declarations, not code
authentication. A profile's association with current inputs does not prove that
its physical law or coefficients are correct.

## Explicit physical mapping

Each attachment supplies one S1 evaluation request and one physical dielectric
layer name per profile segment. All of the following are required:

- Link ID must exist and have kind `inter_fg`; substrate attachments are rejected.
- Profile source/destination contacts must equal the network left/right node IDs.
  The origin declaration is the left node ID, positive direction is
  `network_left_to_right`, and traversal is `along_positive_axis`.
- Ordered contiguous layer groups must equal the network's dielectric-layer order.
  Multiple linear segments within one physical layer are allowed; interleaved or
  reordered layers are rejected. Each layer's summed segment length and the total
  link length must agree with the physical network within relative tolerance
  1e-12, with zero absolute length tolerance.
- Potential energies U and incident energy E retain the S1 common-reference rule.
  Profiles supply complete current barrier energies; no voltage tilt, optical-gap
  shift, electron-affinity rule or image-force correction is automatically applied.

The network path length is its dielectric spacer length, as in the published
model; the node-origin label does not reconstruct centroid distances. There is
no automatic conversion from the field solver's signed arrays into an electron
barrier law. Any provider making that conversion must declare its potential/energy
reference, sign convention, band offsets and applicability. Synthetic providers
may prescribe fixed profiles as controls, but cannot claim calibrated bias response.

## Replacement, directional rates and failure accounting

The plain direct evaluator is still run to retain an unmodified reference. On an
attached inter-FG link, S2 transmission replaces that direct transmission; it is
not added to the old direct rate. The same incident-energy action is used for
both directions, retaining the old compact factors based on signed link potential
difference, attempt frequency and available/empty site densities. This is an
explicitly retained heuristic supply/rate model, not a new microscopic device
current, contact-statistics, detailed-balance or reverse-bias scattering model.

Unattached links retain the direct result. Substrate links stay diagnostic, with
zero redistribution flux: injection/emission remains in the existing occupancy
kinetics, whose tunnelling evaluator is not replaced. Nested advanced-TAT,
image-force or custom transport wrappers are rejected in this initial scope.
No mechanism is silently counted twice or applied as an extra correction.

Mapping/stale-context errors reject the call before the engine advances a state.
If an attached S2 profile fails numerically, only that selected link receives zero
transmission/rates/flux, with explicit failure and complete S2 evidence. No hidden
fallback to the legacy transmission occurs. A nonfinite selected directional flux
is treated similarly. Neighbouring links remain evaluable. A completed transmission
underflow is distinct: it yields zero selected flux with a completed S2 result.
Nonfinite context/direct-reference/aggregate values reject the call rather than
exporting an invalid state. Initial active contexts require positive finite sheet
densities and nonnegative finite controls with transfer fraction at most one.

## State update and simulator use

Selected link fluxes form equal-and-opposite per-FG contributions. The wrapper
reuses `TransportEngine.step` through a private adapter returning those selected
fluxes, so the published normalization, capacity bounds and conservative clipping
algorithm are not copied or modified. Input probability arrays are not advanced
in place; enabled updates use an independent state copy.

A caller can explicitly assign
`physics.transport = BarrierTransportEngine(physics.transport, provider, provider_id="study-provider-v1")`
before constructing `Simulator`. Current simulator calls already provide state,
field and occupancy inputs, so no simulator source modification is needed.
The provider receives a new context on each call, including post-occupancy inputs.

Step results retain the owned context/specification, provider ID, baseline and
selected links, action evidence, failures and copied read-only flux vectors.
Each link also retains its context, provider ID and specification hash, so source
evidence survives the existing simulator's link-diagnostic extraction. These are
the inputs for that transport evaluation, not a claim that the pre-transport
snapshot equals the final post-update simulator state. Full portable S6 reporting
is a later stage; provider code is not embedded in these diagnostic objects.

## Controlled reference and evidence

Run `python examples/phase_s4_barrier_transport_reference.py` (optional new-file
`--output`) for disabled, active, partial numerical failure and transmission-underflow
controls. Profiles are fixed synthetic energy assumptions rebound to each current
context. The standalone study prescribes a field for conservation tests; it is not
an independently calibrated or self-consistent device prediction. Tests separately
exercise actual simulator field recomputation and a single-FG injection baseline.

The [source-pinned S4 review](barrier_transport_integration_review.json) retains
original context declarations, plans, baseline/selected diagnostics and local
conservation observations. Repeated contexts are deduplicated by context hash.
Total electron sheet density is compared at relative tolerance 1e-12, including
different FG site capacities and clipping-dominated steps. Tiny floating-point
conservation residuals are retained rather than rewritten to zero.

This completes only the scoped direct inter-FG integration. S5 can study explicit
profile sensitivities within this contract. Wider physical laws, TAT composition,
contact supply models and experimental qualification require separate evidence.
See the [Phase S plan](barrier_transport.md) and [S3 limitations](barrier_multilayer_reference.md).
