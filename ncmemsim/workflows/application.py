"""Explicit fitted application and isolated, fully declared program evaluators."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, fields
import json
import platform
import numpy as np

from ..device import Device
from ..layers import Layer, FloatingGateLayer
from ..materials.base import Material, NanocrystalMaterial
from ..materials.provenance import MaterialProperty, ParameterProvenance, ParameterStatus
from ..materials.optics.models import GeSnOpticalParameterSet, GeSnAbsorptionParameterSet
from ..optics import LightSource
from ..photo import PhotoTransitionWeights
from .._version import __version__
from ..device_calibration import (DeviceCalibrationSpec, DeviceFitParameterBinding,
    DeviceFitTarget, apply_device_calibration_parameters)
from ..fitting import FitParameter, FitParameterSet
from ..electrostatics import ElectrostaticsEngine, SemiconductorConfig
from ..coupling import CompactCouplingModel
from ..fieldsolver import FieldSolver1D
from ..kinetics import OccupancyEngine, KineticsConfig
from ..tunneling import TunnelingEngine, TunnelingConfig
from ..transport import TransportEngine, TransportConfig
from ..physics import PhysicsModel
from ..photo import PhotoTransitionConfig
from ..simulator import SimulationConfig, Simulator
from ..program_protocol import ProgramPulseReadProtocol, run_program_pulse_read
from ..electro_optical_program_protocol import (
    ElectroOpticalProgramPulseReadProtocol, run_electro_optical_program_pulse_read,
)
from ..hashing import canonical_hash
from ..dtco.spec import _device_definition_payload, _operating_definition_payload
from ..dtco.sweep import _json_snapshot
from .evidence import WorkflowEvidence, _load, _label


def _exact(value, cls, attributes):
    if type(value) is not cls or set(vars(value)) != set(attributes):
        raise TypeError(f"I2 requires an unextended {cls.__name__}")


def _config(value, cls):
    _exact(value, cls, (field.name for field in fields(cls)))
    return asdict(value)


def _physics_payload(physics):
    # An arbitrary subclass/callback could change predictions without changing
    # these settings. Reject it rather than claim an incomplete identity.
    _exact(physics, PhysicsModel, ('electrostatics', 'tunneling', 'occupancy', 'transport'))
    e, t, o, r = physics.electrostatics, physics.tunneling, physics.occupancy, physics.transport
    _exact(e, ElectrostaticsEngine, ('semiconductor', 'coupling_model', 'field_solver'))
    _exact(t, TunnelingEngine, ('config',))
    _exact(o, OccupancyEngine, ('tunneling', 'config'))
    _exact(r, TransportEngine, ('tunneling', 'config'))
    _exact(e.coupling_model, CompactCouplingModel, ('legacy_single_fg',))
    _exact(e.field_solver, FieldSolver1D, ())
    if o.tunneling is not t or r.tunneling is not t:
        raise ValueError('physics must share the same tunneling engine')
    if type(e.coupling_model.legacy_single_fg) is not bool:
        raise ValueError('legacy_single_fg must be boolean')
    return {'implementation': 'ncmemsim-core-physics-v1',
        'semiconductor': _config(e.semiconductor, SemiconductorConfig),
        'coupling': {'legacy_single_fg': e.coupling_model.legacy_single_fg},
        'field_solver': 'FieldSolver1D',
        'tunneling': _config(t.config, TunnelingConfig),
        'kinetics': _config(o.config, KineticsConfig),
        'transport': _config(r.config, TransportConfig),
        'shared_tunneling': True}


def _restore_physics(raw):
    if set(raw) != {'implementation', 'semiconductor', 'coupling', 'field_solver',
                    'tunneling', 'kinetics', 'transport', 'shared_tunneling'}:
        raise ValueError('incomplete physics context')
    if raw['implementation'] != 'ncmemsim-core-physics-v1' or raw['field_solver'] != 'FieldSolver1D' or raw['shared_tunneling'] is not True:
        raise ValueError('unsupported physics context')
    t = TunnelingEngine(TunnelingConfig(**raw['tunneling']))
    result = PhysicsModel(ElectrostaticsEngine(SemiconductorConfig(**raw['semiconductor']),
        CompactCouplingModel(**raw['coupling']), FieldSolver1D()), t,
        OccupancyEngine(t, KineticsConfig(**raw['kinetics'])),
        TransportEngine(t, TransportConfig(**raw['transport'])))
    if _json_snapshot(_physics_payload(result)) != _json_snapshot(raw):
        raise ValueError('noncanonical physics context')
    return result


def _context_payload(device, physics, config, photo):
    _exact(device, Device, (field.name for field in fields(Device)))
    device.validate()
    return {'device': _device_payload(device), 'physics': _physics_payload(physics),
        'simulation_config': _config(config, SimulationConfig),
        'photo_config': None if photo is None else _config(photo, PhotoTransitionConfig),
        'optical_model': {'implementation': 'CompositeGeSnAbsorptionModel-default-v1',
            'optical_parameters': asdict(GeSnOpticalParameterSet()),
            'absorption_parameters': asdict(GeSnAbsorptionParameterSet())}}


def _device_payload(device):
    _exact(device, Device, (field.name for field in fields(Device)))
    for layer in device.layers:
        cls = FloatingGateLayer if type(layer) is FloatingGateLayer else Layer
        _exact(layer, cls, (field.name for field in fields(cls)))
        materials = (layer.matrix_material, layer.nc_material) if cls is FloatingGateLayer else (layer.material,)
        for material in materials:
            mcls = NanocrystalMaterial if type(material) is NanocrystalMaterial else Material
            _exact(material, mcls, (field.name for field in fields(mcls)))
    return {**_device_definition_payload(device), 'layer_metadata': [deepcopy(l.metadata) for l in device.layers]}


def _material(raw, cls):
    value = deepcopy(raw)
    properties = {}
    for name, prop in value['properties'].items():
        p = deepcopy(prop)
        provenance = p.pop('provenance')
        provenance['status'] = ParameterStatus(provenance['status'])
        properties[name] = MaterialProperty(**p, provenance=ParameterProvenance(**provenance))
    value['properties'] = properties
    return cls(**value)


def _restore_device(raw):
    if set(raw) != {'device', 'layer_material_definitions', 'layer_metadata'}:
        raise ValueError('complete device/material/layer metadata required')
    d = deepcopy(raw['device'])
    layers, materials, metadata = d.pop('layers'), raw['layer_material_definitions'], raw['layer_metadata']
    d.pop('total_thickness_nm'); d.pop('number_of_fgs')
    if not layers or len(layers) != len(materials) or len(layers) != len(metadata):
        raise ValueError('material/layer identity mismatch')
    restored = []
    for layer, m, notes in zip(layers, materials, metadata):
        if layer['name'] != m['layer_name']:
            raise ValueError('material/layer identity mismatch')
        if layer['type'] == 'floating_gate':
            values = {k: layer[k] for k in ('name', 'thickness_nm', 'nc_diameter_nm',
                'nc_volume_fraction', 'electrically_active_fraction', 'spatial_profile', 'grid_points')}
            restored.append(FloatingGateLayer(**values, matrix_material=_material(m['matrix_material'], Material),
                nc_material=_material(m['nc_material'], NanocrystalMaterial), metadata=notes))
        elif layer['type'] == 'layer':
            restored.append(Layer(layer['name'], _material(m['material'], Material),
                layer['thickness_nm'], layer['role'], metadata=notes))
        else:
            raise ValueError('unsupported layer type')
    result = Device(**d, layers=restored)
    result.validate()
    if _json_snapshot(_device_payload(result)) != _json_snapshot(raw):
        raise ValueError('noncanonical device context')
    return result


def _protocol_payload(protocol):
    _exact(protocol, type(protocol), (field.name for field in fields(type(protocol))))
    if type(protocol) is ElectroOpticalProgramPulseReadProtocol:
        _config(protocol.light_source, LightSource)
        _config(protocol.photo_weights, PhotoTransitionWeights)
        _config(protocol.electrical_protocol, ProgramPulseReadProtocol)
        if not protocol.light_source.is_monochromatic:
            raise ValueError('I2 requires an LED or laser optical protocol')
    return _operating_definition_payload(protocol)


def _restore_protocol(raw):
    if set(raw) != {'kind', 'protocol'}:
        raise ValueError('invalid operating context')
    def electrical(value):
        return ProgramPulseReadProtocol(**{k: value[k] for k in ('program_voltage_V',
            'programming_time_s', 'read_voltage_V', 'program_internal_dt_s')})
    if raw['kind'] == 'program_pulse_read':
        result = electrical(raw['protocol'])
    elif raw['kind'] == 'electro_optical_program_pulse_read':
        p = raw['protocol']
        result = ElectroOpticalProgramPulseReadProtocol(electrical(p['electrical_protocol']),
            LightSource(**p['light_source']), PhotoTransitionWeights(**p['photo_transition_weights']),
            p['occupancy_integrator'])
    else:
        raise ValueError('unsupported operating context')
    if _json_snapshot(_protocol_payload(result)) != _json_snapshot(raw):
        raise ValueError('noncanonical operating context')
    return result


def _check_context(raw):
    if type(raw) is not dict or set(raw) != {'device', 'physics', 'simulation_config', 'photo_config', 'optical_model'}:
        raise ValueError('incomplete simulator context')
    _restore_physics(raw['physics'])
    if _config(SimulationConfig(**raw['simulation_config']), SimulationConfig) != raw['simulation_config']:
        raise ValueError('invalid simulation configuration')
    if raw['photo_config'] is not None:
        _config(PhotoTransitionConfig(**raw['photo_config']), PhotoTransitionConfig)
    _restore_device(raw['device'])
    optical = raw['optical_model']
    if set(optical) != {'implementation', 'optical_parameters', 'absorption_parameters'} or optical['implementation'] != 'CompositeGeSnAbsorptionModel-default-v1':
        raise ValueError('invalid optical model context')
    _config(GeSnOpticalParameterSet(**optical['optical_parameters']), GeSnOpticalParameterSet)
    _config(GeSnAbsorptionParameterSet(**optical['absorption_parameters']), GeSnAbsorptionParameterSet)


def _applied_value(context, binding):
    family, field = binding['target'].split('.')
    if family == 'fg':
        device = context['device']
        indices = [i for i, layer in enumerate(device['device']['layers']) if layer['type'] == 'floating_gate']
        index = indices[binding['fg_index']]
        if field.startswith('phi_barrier_'):
            return device['layer_material_definitions'][index]['nc_material'][field]
        return device['device']['layers'][index][field]
    if family == 'simulation':
        return context['simulation_config'][field]
    if family == 'photo':
        return context['photo_config'][field]
    return context['physics'][family][field]


def _specification(raw):
    spec = DeviceCalibrationSpec(FitParameterSet(tuple(FitParameter(**p) for p in raw['parameter_set']['parameters'])),
        tuple(DeviceFitParameterBinding(b['parameter_name'], DeviceFitTarget(b['target']), b.get('fg_index')) for b in raw['bindings']),
        name=raw['name'], notes=raw.get('notes'))
    if _json_snapshot(spec.to_dict()) != _json_snapshot(raw):
        raise ValueError('noncanonical calibration specification')
    _check_units(spec)
    return spec


def _check_units(spec):
    for parameter, binding in zip(spec.parameter_set.parameters, spec.bindings):
        if parameter.unit != binding.canonical_unit:
            raise ValueError(f'{parameter.name} requires canonical unit {binding.canonical_unit!r}')


def _expected_context(baseline, bindings, values):
    """Verify the declared delta without applying parameters or running physics."""
    expected = deepcopy(baseline)
    for binding in bindings:
        family, field = binding['target'].split('.')
        value = values[binding['parameter_name']]
        if family == 'fg':
            d = expected['device']
            indices = [i for i, l in enumerate(d['device']['layers']) if l['type'] == 'floating_gate']
            index = indices[binding['fg_index']]
            if field.startswith('phi_barrier_'):
                material = d['layer_material_definitions'][index]['nc_material']
                material[field] = value
                if field in material['properties']:
                    material['properties'][field]['value'] = value
            else:
                d['device']['layers'][index][field] = value
        elif family == 'photo':
            expected['photo_config'][field] = value
        elif family == 'simulation':
            expected['simulation_config'][field] = value
        else:
            expected['physics'][family][field] = value
    return expected


def _runtime():
    return {'python': platform.python_version(), 'python_implementation': platform.python_implementation(),
            'numpy': np.__version__, 'ncmemsim': __version__}


@dataclass(frozen=True)
class AppliedWorkflowEvidence:
    """Archival full context and source links; restoration executes no physics."""
    payload_json: str

    def __post_init__(self):
        raw = _load(self.payload_json)
        try:
            if set(raw) != {'schema_version', 'workflow_evidence', 'baseline_context',
                'applied_context', 'parameter_application', 'parameter_application_hash',
                'context_hash', 'operating', 'evaluation_id', 'response_model', 'runtime'} or raw['schema_version'] != 'applied-workflow-evidence-v1':
                raise ValueError('unsupported applied workflow schema')
            workflow = WorkflowEvidence.from_json(_json_snapshot(raw['workflow_evidence']))
            _label(raw['evaluation_id'], 'evaluation_id')
            if raw['response_model'] != 'program-pulse-delta-vfb-v1':
                raise ValueError('unsupported response model')
            for key in ('baseline_context', 'applied_context'):
                _check_context(raw[key])
            if raw['context_hash'] != canonical_hash(raw['applied_context']):
                raise ValueError('full context hash mismatch')
            application = raw['parameter_application']
            source = workflow.to_dict()
            spec = _specification(source['calibration_specification']['data'])
            if application != source['fit_result']['data']['parameter_application'] or canonical_hash(application) != raw['parameter_application_hash']:
                raise ValueError('fitted application identity mismatch')
            spec.parameter_set.validate_values([application['parameter_values'][name] for name in spec.parameter_set.names])
            for binding in source['calibration_specification']['data']['bindings']:
                if _json_snapshot(_applied_value(raw['applied_context'], binding)) != _json_snapshot(application['parameter_values'][binding['parameter_name']]):
                    raise ValueError('fitted value is not applied to its target')
            expected = _expected_context(raw['baseline_context'], source['calibration_specification']['data']['bindings'], application['parameter_values'])
            if _json_snapshot(expected) != _json_snapshot(raw['applied_context']):
                raise ValueError('context contains undeclared application changes')
            _restore_protocol(raw['operating'])
            if set(raw['runtime']) != {'python', 'python_implementation', 'numpy', 'ncmemsim'}:
                raise ValueError('runtime provenance required')
            for key, value in raw['runtime'].items():
                _label(value, key)
            kind = raw['operating']['kind']
            if kind not in ('program_pulse_read', 'electro_optical_program_pulse_read') or type(raw['operating']['protocol']) is not dict:
                raise ValueError('unsupported operating context')
            if kind == 'electro_optical_program_pulse_read' and raw['applied_context']['photo_config'] is None:
                raise ValueError('electro-optical execution requires explicit photo settings')
            if any(b.target is DeviceFitTarget.PHOTO_CAPTURE_EFFICIENCY for b in spec.bindings) and kind != 'electro_optical_program_pulse_read':
                raise ValueError('photo fitted target requires electro-optical execution')
        except (KeyError, IndexError, TypeError, AttributeError) as error:
            raise ValueError('incomplete applied workflow evidence') from error
        object.__setattr__(self, 'payload_json', _json_snapshot(raw))

    @property
    def evidence_hash(self):
        return canonical_hash(json.loads(self.payload_json))

    @property
    def context_hash(self):
        return json.loads(self.payload_json)['context_hash']

    @property
    def scientific_status(self):
        return 'FITTED'

    def to_dict(self):
        return {**json.loads(self.payload_json), 'evidence_hash': self.evidence_hash}

    def to_json(self):
        return _json_snapshot(self.to_dict())

    @classmethod
    def from_json(cls, value):
        raw = _load(value)
        digest = raw.pop('evidence_hash', None)
        if digest != canonical_hash(raw):
            raise ValueError('applied workflow evidence integrity mismatch')
        return cls(_json_snapshot(raw))


class WorkflowEvaluator:
    """Fixed response adapter for Phase G/H DEVICE/OPERATING candidates.

    Construct through apply_workflow_parameters. Exposed baselines/settings are
    copies. Private template drift is rejected before any simulator call.
    """
    def __init__(self, evidence, device, protocol):
        if not isinstance(evidence, AppliedWorkflowEvidence):
            raise TypeError('evidence must be AppliedWorkflowEvidence')
        self._evidence = evidence
        self._device, self._protocol = deepcopy((device, protocol))
        self._check_templates()

    def _check_templates(self):
        raw = self._evidence.to_dict()
        if _json_snapshot(_device_payload(self._device)) != _json_snapshot(raw['applied_context']['device']) or _json_snapshot(_protocol_payload(self._protocol)) != _json_snapshot(raw['operating']):
            raise ValueError('evaluator template identity mismatch')

    @property
    def evidence(self):
        return self._evidence

    @property
    def base_device(self):
        self._check_templates()
        return deepcopy(self._device)

    @property
    def base_protocol(self):
        self._check_templates()
        return deepcopy(self._protocol)

    @property
    def evaluation_id(self):
        return self._evidence.to_dict()['evaluation_id']

    @property
    def evaluation_parameters(self):
        return {'applied_workflow_evidence': self._evidence.to_dict()}

    def fresh_simulator(self, device=None):
        """Independent core simulator; no shared mutable physics or device."""
        self._check_templates()
        if self._evidence.to_dict()['runtime'] != _runtime():
            raise ValueError('captured application runtime differs from executable runtime')
        candidate = self.base_device if device is None else deepcopy(device)
        raw = self._evidence.to_dict()['applied_context']
        defaults = _context_payload(candidate, PhysicsModel.default(), SimulationConfig(), None)['optical_model']
        if _json_snapshot(raw['optical_model']) != _json_snapshot(defaults):
            raise ValueError('captured optical defaults differ from executable runtime')
        physics = _restore_physics(raw['physics'])
        config = SimulationConfig(**raw['simulation_config'])
        _context_payload(candidate, physics, config, None)
        return Simulator(candidate, physics, config)

    def evaluate(self, device, protocol, point=None):
        """Two-argument nominal/G2 and three-argument H3 callback.

        Point is accepted for H3 compatibility; it does not select a hidden
        response model or inject synthetic failures.
        """
        self._check_templates()
        if type(protocol) is not type(self._protocol):
            raise ValueError('operating protocol family mismatch')
        _restore_protocol(_protocol_payload(protocol))
        # H DEVICE/OPERATING variations can change electrical conditions and
        # wavelength/power, but not the integrator, weights or source family.
        if type(protocol) is ElectroOpticalProgramPulseReadProtocol:
            if protocol.photo_weights != self._protocol.photo_weights or protocol.occupancy_integrator != self._protocol.occupancy_integrator:
                raise ValueError('optical evaluator settings mismatch')
            a, b = asdict(protocol.light_source), asdict(self._protocol.light_source)
            for key in ('wavelength_nm', 'power_density_W_m2'):
                a.pop(key); b.pop(key)
            if _json_snapshot(a) != _json_snapshot(b):
                raise ValueError('optical source family mismatch')
        simulator = self.fresh_simulator(device)
        if type(protocol) is ProgramPulseReadProtocol:
            result = run_program_pulse_read(simulator, deepcopy(protocol))
        else:
            photo = PhotoTransitionConfig(**self._evidence.to_dict()['applied_context']['photo_config'])
            result = run_electro_optical_program_pulse_read(simulator, deepcopy(protocol), photo_config=photo)
        return {'delta_vfb_V': float(result.delta_vfb_V), 'mean_occupation': float(result.mean_occupation)}


def apply_workflow_parameters(workflow_evidence, *, calibration_spec,
        base_device, base_physics, base_simulation_config, base_protocol,
        evaluation_id, base_photo_config=None):
    """Apply exactly the ordered evidence values using existing Phase F APIs.

    Baselines are explicit: I1 cannot attest an unrecorded historical simulator
    baseline. This records the declared application, not a reconstruction claim.
    """
    if not isinstance(workflow_evidence, WorkflowEvidence):
        raise TypeError('workflow_evidence must be WorkflowEvidence')
    if not isinstance(calibration_spec, DeviceCalibrationSpec):
        raise TypeError('calibration_spec must be DeviceCalibrationSpec')
    _check_units(calibration_spec)
    source = workflow_evidence.to_dict()
    if _json_snapshot(calibration_spec.to_dict()) != _json_snapshot(source['calibration_specification']['data']):
        raise ValueError('calibration specification identity mismatch')
    _label(evaluation_id, 'evaluation_id')
    if type(base_protocol) not in (ProgramPulseReadProtocol, ElectroOpticalProgramPulseReadProtocol):
        raise TypeError('unsupported operating protocol')
    baseline = _context_payload(base_device, base_physics, base_simulation_config, base_photo_config)
    values = source['fit_result']['data']['numerical_result']['fitted_parameters']
    context = apply_device_calibration_parameters(base_device, base_physics, base_simulation_config,
        calibration_spec, [values[name] for name in calibration_spec.parameter_set.names],
        base_photo_config=base_photo_config)
    applied = _context_payload(context.device, context.physics, context.simulation_config, context.photo_config)
    raw = {'schema_version': 'applied-workflow-evidence-v1', 'workflow_evidence': source,
        'baseline_context': baseline, 'applied_context': applied,
        'parameter_application': context.parameter_application_manifest(),
        'parameter_application_hash': context.parameter_application_hash(),
        'context_hash': canonical_hash(applied), 'operating': _protocol_payload(base_protocol),
        'evaluation_id': evaluation_id, 'response_model': 'program-pulse-delta-vfb-v1',
        'runtime': _runtime()}
    evidence = AppliedWorkflowEvidence(_json_snapshot(raw))
    return WorkflowEvaluator(evidence, context.device, base_protocol)
