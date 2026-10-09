# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""P4A fixed-input light/dark device diagnostic; not measured qualification."""
from pathlib import Path
import argparse,json,sys
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from examples.phase_n5_broadband_reference import build_resolution,SCOPE
from ncmemsim import DeviceState
from ncmemsim.spectral_sources import SpectralEvidence
from ncmemsim.spectral_absorption import SpectralAbsorptionProfile
from ncmemsim.spectral_stack import SpectralStackLayer
from ncmemsim.spectral_context import SpectralPulseProtocol
from ncmemsim.program_protocol import ProgramPulseReadProtocol
from ncmemsim.photo import PhotoTransitionWeights
from ncmemsim.device_photo_experiment import SamplePlaneIllumination,DevicePhotoPrediction,build_device_photo_experiment,predict_device_photo_experiment


def build_experiment(n=1,*,power_W=.01,capture_efficiency=.1):
    resolution=build_resolution(n)
    evidence=SpectralEvidence('P4A assumed sample-plane diagnostic','example code','ASSUMED','W, m2, nm, s',(),'single line/flat top','not measured',SCOPE)
    illumination=SamplePlaneIllumination(1550.,power_W,1e-8,1e-7,evidence,'Assumed uniform sample-plane input; no nominal laser or upstream optical correction inferred.')
    device=resolution.device;source=illumination.source
    passive=tuple(SpectralStackLayer(SpectralAbsorptionProfile(x.name,source.wavelength_nm,(0.,),x.thickness_nm*1e-9,1500,2000,evidence),'passive','assumed_transparent') for x in device.layers if x.role!='floating_gate')
    protocol=SpectralPulseProtocol(ProgramPulseReadProtocol(2.,1e-7,0.,1e-7/16),PhotoTransitionWeights())
    return build_device_photo_experiment('P4A '+str(n)+' FG light/dark diagnostic',resolution,illumination,protocol,
        capture_efficiency=capture_efficiency,initial_state=DeviceState.empty_for_device(device),device_area_m2=1e-10,
        initial_preparation_evidence='Explicit assumed empty state; not an observed experimental preparation.',
        assumptions='Uniform full-device spot, transparent passive/matrix optics, constant assumed capture, fixed pulse/read; no experimental device qualification or storage-yield claim.',
        direction='gate_to_substrate',passive_layers=passive,wavelength_min_nm=1500.,wavelength_max_nm=2000.,evidence=evidence)


def run_reference():return predict_device_photo_experiment(build_experiment())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--input',type=Path);args=parser.parse_args()
    result=DevicePhotoPrediction.from_json(args.input.read_text(encoding='utf-8')) if args.input else run_reference()
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result.to_dict(),indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'prediction_hash':result.contract_hash,'status':result.summary['status'],'scientific_status':result.summary['scientific_status'],'contrast':result.summary['contrast']}))
