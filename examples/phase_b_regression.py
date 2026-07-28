from ncmemsim import make_v53_reference_device,Simulator,SimulationConfig

device=make_v53_reference_device(grid_points=31)
simulator=Simulator(device,config=SimulationConfig(dwell_time_s=0.005,internal_dt_s=1e-5))
result=simulator.simulate_cv(points=61)
print(f'Cox = {device.equivalent_dielectric_capacitance_F_m2():.6e} F/m²')
print(f'Memory window = {result.memory_window_V:.6f} V')
