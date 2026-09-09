"""
unified_nc_memory_model_v5p3_trapezoidal_wkb.py
Distributed Ge-nanocrystal floating-gate memory model with trapezoidal WKB tunneling + dwell time.
"""

import os, csv, json, math
import numpy as np
import matplotlib.pyplot as plt

OUTPUT_DIR = "results_v5p3"
os.makedirs(OUTPUT_DIR, exist_ok=True)
SAVE_DPI = 300

EPS0 = 8.854187817e-12
Q = 1.602176634e-19
KB = 1.380649e-23
HBAR = 1.054571817e-34
M0 = 9.1093837015e-31

t_control = 35e-9
t_fg = 15e-9
t_tunnel = 10e-9
t_native = 2e-9

eps_hfo2 = 25.0 * EPS0
eps_sio2 = 3.9 * EPS0
eps_fg_eff = 18.0 * EPS0
eps_si = 11.7 * EPS0

Na = 1.2e21
ni = 1.0e16
f_ge = 0.60
eta_default = 0.35
d_nc_default = 3.0e-9

psi_max_default = 0.9
Vtr_default = 0.65
Vw_mos_default = 0.22
acc_factor_default = 40.0

T_default = 300.0
m_eff_ox = 0.15 * M0
eps_nc_local = 8.0 * EPS0
Phi_B_prog_eV = 1.85
Phi_B_erase_eV = 2.15
E_inj_eV = 0.10
nu0_default = 5.0e12
nu1_default = 1.0e10
nu2_default = 3.0e9
beta_g_default = 2.5
N_WKB = 160

dt_internal = 2.0e-4
dwell_time_per_step = 0.10

ret_t_start = 1e-3
ret_t_stop = 1e4
ret_npts = 200
Nx_default = 31

chi_si_eV = 4.05
Eg_si_eV = 1.12
phi_m_eV = 4.8
Qfix_default = 0.0
Qit_default = 0.0


def save_csv(filename, headers, rows):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)
    return path


def save_json(filename, obj):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
    return path


def save_figure(fig, filename):
    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, dpi=SAVE_DPI, bbox_inches="tight")
    return path


def equivalent_oxide_capacitance():
    return 1.0 / (t_control / eps_hfo2 + t_fg / eps_fg_eff + t_tunnel / eps_hfo2 + t_native / eps_sio2)


def nanocrystal_volume(d_nc):
    return (math.pi / 6.0) * d_nc**3


def nanocrystal_density(d_nc, f_ge=f_ge):
    return f_ge / nanocrystal_volume(d_nc)


def effective_nanocrystal_density(d_nc, eta=eta_default):
    return eta * nanocrystal_density(d_nc)


def nc_capacitance(d_nc, eps_eff=eps_nc_local):
    return 4.0 * math.pi * eps_eff * (0.5 * d_nc)


def charging_energy(d_nc, eps_eff=eps_nc_local):
    return Q**2 / (2.0 * nc_capacitance(d_nc, eps_eff=eps_eff))


def gamma_c(d_nc, T=T_default, eps_eff=eps_nc_local):
    return charging_energy(d_nc, eps_eff=eps_eff) / (KB * T)


def phi_f_p_si(T=T_default):
    return (KB * T / Q) * math.log(Na / ni)


def V_FB0(cox_eq=None, T=T_default, Qfix=Qfix_default, Qit=Qit_default):
    if cox_eq is None:
        cox_eq = equivalent_oxide_capacitance()
    phi_s_eV = chi_si_eV + 0.5 * Eg_si_eV + phi_f_p_si(T=T)
    phi_ms_V = phi_m_eV - phi_s_eV
    return phi_ms_V - (Qfix + Qit) / cox_eq


def fg_grid(Nx=Nx_default):
    x = np.linspace(0.5 * t_fg / Nx, t_fg - 0.5 * t_fg / Nx, Nx)
    return x, t_fg / Nx


def N_eff_profile(x, d_nc=d_nc_default, eta=eta_default, profile="front_loaded"):
    N0 = effective_nanocrystal_density(d_nc, eta=eta)
    if profile == "uniform":
        return np.full_like(x, N0, dtype=float)
    if profile == "front_loaded":
        lam = 0.30 * t_fg
        w = np.exp(-x / lam)
        w /= np.mean(w)
        return N0 * w
    raise ValueError("Unknown N_eff profile")


def field_from_effective_voltage(Veff):
    return abs(Veff) / max(t_native + t_tunnel, 1e-12)


def local_tunneling_distance(x_local):
    return t_native + t_tunnel + x_local


def trapezoidal_wkb_transmission(L, F, phi_B_eV, E_eV=E_inj_eV, m_eff=m_eff_ox, npts=N_WKB):
    if L <= 0:
        return 1.0
    s = np.linspace(0.0, L, npts)
    # qFs in joule corresponds to F*s in eV for one electron charge.
    U_minus_E_eV = phi_B_eV - F * s - E_eV
    U_minus_E_eV = np.maximum(U_minus_E_eV, 0.0)
    if np.all(U_minus_E_eV <= 0):
        return 1.0
    kappa = np.sqrt(2.0 * m_eff * (U_minus_E_eV * Q)) / HBAR
    action = np.trapezoid(kappa, s)
    return float(np.exp(max(-2.0 * action, -700.0)))


def bias_activation_positive(Veff, beta=beta_g_default):
    return 1.0 / (1.0 + math.exp(-beta * Veff))


def bias_activation_negative(Veff, beta=beta_g_default):
    return 1.0 / (1.0 + math.exp(beta * Veff))


def local_rates(x_local, Veff, d_nc=d_nc_default, T=T_default):
    F = field_from_effective_voltage(Veff)
    L = local_tunneling_distance(x_local)
    T_prog = trapezoidal_wkb_transmission(L, F, Phi_B_prog_eV)
    T_erase = trapezoidal_wkb_transmission(L, F, Phi_B_erase_eV)
    fp = bias_activation_positive(Veff)
    fm = bias_activation_negative(Veff)
    r01 = nu0_default * T_prog * fp
    r12 = r01 * math.exp(-gamma_c(d_nc, T=T))
    r21 = nu1_default * T_erase * fm
    r10 = nu2_default * T_erase * fm
    return r01, r12, r21, r10, T_prog, T_erase, F


def initialize_fg_state(Nx=Nx_default):
    return np.ones(Nx), np.zeros(Nx), np.zeros(Nx)


def occupancy(P1, P2):
    return 0.5 * (P1 + 2.0 * P2)


def step_local_probabilities(P0, P1, P2, r01, r12, r21, r10, dt):
    dP0 = -r01 * P0 + r10 * P1
    dP1 = r01 * P0 - (r10 + r12) * P1 + r21 * P2
    dP2 = r12 * P1 - r21 * P2
    P0n = np.maximum(P0 + dP0 * dt, 0.0)
    P1n = np.maximum(P1 + dP1 * dt, 0.0)
    P2n = np.maximum(P2 + dP2 * dt, 0.0)
    s = P0n + P1n + P2n
    s = np.where(s <= 0.0, 1.0, s)
    return P0n / s, P1n / s, P2n / s


def rho_FG(P1, P2, N_eff_x):
    return Q * N_eff_x * occupancy(P1, P2)


def total_QFG_per_area(rho_x, dx):
    return float(np.sum(rho_x) * dx)


def dynamic_VFB(VFB0_value, QFG, cox_eq):
    return VFB0_value - QFG / cox_eq


def psi_surface_proxy(Veff, Vtr=Vtr_default, Vw_mos=Vw_mos_default, psi_max=psi_max_default):
    return psi_max * 0.5 * (1.0 + np.tanh((Veff - Vtr) / Vw_mos))


def depletion_width_from_psi(psi):
    psi_clip = np.maximum(psi, 1e-6)
    return np.sqrt(2.0 * eps_si * psi_clip / (Q * Na))


def semiconductor_capacitance(Veff, cox_eq, acc_factor=acc_factor_default):
    psi = psi_surface_proxy(Veff)
    Wd = depletion_width_from_psi(psi)
    Cdep = eps_si / Wd
    Cacc = acc_factor * cox_eq
    w_acc = 0.5 * (1.0 - np.tanh((Veff - 0.0) / 0.18))
    return w_acc * Cacc + (1.0 - w_acc) * Cdep


def mos_total_capacitance(Veff, cox_eq):
    Cs = semiconductor_capacitance(Veff, cox_eq)
    return (cox_eq * Cs) / (cox_eq + Cs)


def compute_rates_arrays(x, Veff, d_nc=d_nc_default, T=T_default):
    r01 = np.zeros_like(x); r12 = np.zeros_like(x); r21 = np.zeros_like(x); r10 = np.zeros_like(x)
    Tprog = np.zeros_like(x); Terase = np.zeros_like(x); Fvals = np.zeros_like(x)
    for i, xi in enumerate(x):
        r01[i], r12[i], r21[i], r10[i], Tprog[i], Terase[i], Fvals[i] = local_rates(xi, Veff, d_nc=d_nc, T=T)
    return r01, r12, r21, r10, Tprog, Terase, Fvals


def one_voltage_point_relax(P0, P1, P2, Vg, x, dx, d_nc=d_nc_default, eta=eta_default, T=T_default, N_profile="front_loaded", dwell_time=dwell_time_per_step, dt=dt_internal, cox_eq=None, VFB0_value=None):
    if cox_eq is None:
        cox_eq = equivalent_oxide_capacitance()
    if VFB0_value is None:
        VFB0_value = V_FB0(cox_eq=cox_eq, T=T)
    N_eff_x = N_eff_profile(x, d_nc=d_nc, eta=eta, profile=N_profile)
    
    
    #nsteps = max(1, int(math.ceil(dwell_time / dt)))
    #P0c, P1c, P2c = P0.copy(), P1.copy(), P2.copy()
    #last_F = last_Tprog = last_Terase = 0.0
    #for _ in range(nsteps):
    #    rho_x = rho_FG(P1c, P2c, N_eff_x)
    #    QFG = total_QFG_per_area(rho_x, dx)
    #    VFB_t = dynamic_VFB(VFB0_value, QFG, cox_eq)
    #    Veff = Vg - VFB_t
    #    r01, r12, r21, r10, Tprog, Terase, Fvals = compute_rates_arrays(x, Veff, d_nc=d_nc, T=T)
    #    P0c, P1c, P2c = step_local_probabilities(P0c, P1c, P2c, r01, r12, r21, r10, dt)
    #    last_F = float(np.mean(Fvals)); last_Tprog = float(np.mean(Tprog)); last_Terase = float(np.mean(Terase))
     
    ##### bug fixed
    nsteps = max(1, int(math.ceil(dwell_time / dt)))
    actual_dt = dwell_time / nsteps
    P0c, P1c, P2c = P0.copy(), P1.copy(), P2.copy()
    last_F = last_Tprog = last_Terase = 0.0
    
    for _ in range(nsteps):
        rho_x = rho_FG(P1c, P2c, N_eff_x)
        QFG = total_QFG_per_area(rho_x, dx)
        VFB_t = dynamic_VFB(VFB0_value, QFG, cox_eq)
        Veff = Vg - VFB_t

        r01, r12, r21, r10, Tprog, Terase, Fvals = compute_rates_arrays(
            x, Veff, d_nc=d_nc, T=T
        )

        P0c, P1c, P2c = step_local_probabilities(
            P0c, P1c, P2c,
            r01, r12, r21, r10,
            actual_dt
        )

        last_F = float(np.mean(Fvals))
        last_Tprog = float(np.mean(Tprog))
        last_Terase = float(np.mean(Terase))
    ####
    
    rho_x = rho_FG(P1c, P2c, N_eff_x)
    QFG = total_QFG_per_area(rho_x, dx)
    VFB_t = dynamic_VFB(VFB0_value, QFG, cox_eq)
    Veff = Vg - VFB_t
    C = mos_total_capacitance(Veff, cox_eq)
    return {"P0": P0c, "P1": P1c, "P2": P2c, "rho_x": rho_x, "QFG": QFG, "VFB": VFB_t, "Veff": Veff, "C": C, "m_x": occupancy(P1c, P2c), "m_mean": float(np.mean(occupancy(P1c, P2c))), "F_mean": last_F, "Tprog_mean": last_Tprog, "Terase_mean": last_Terase}


def midpoint_voltage(V, C):
    Cmid = 0.5 * (np.max(C) + np.min(C))
    return float(V[np.argmin(np.abs(C - Cmid))])


def run_cv_sweep_distributed(Vlist, P0_init, P1_init, P2_init, x, dx, d_nc=d_nc_default, eta=eta_default, T=T_default, N_profile="front_loaded", dwell_time=dwell_time_per_step):
    cox_eq = equivalent_oxide_capacitance(); VFB0_value = V_FB0(cox_eq=cox_eq, T=T)
    P0, P1, P2 = P0_init.copy(), P1_init.copy(), P2_init.copy()
    C_hist=[]; VFB_hist=[]; Veff_hist=[]; QFG_hist=[]; mmean_hist=[]; rho_store=[]; mx_store=[]; F_hist=[]; Tprog_hist=[]; Terase_hist=[]
    for Vg in Vlist:
        out = one_voltage_point_relax(P0, P1, P2, Vg, x, dx, d_nc=d_nc, eta=eta, T=T, N_profile=N_profile, dwell_time=dwell_time, cox_eq=cox_eq, VFB0_value=VFB0_value)
        P0, P1, P2 = out["P0"], out["P1"], out["P2"]
        C_hist.append(out["C"]); VFB_hist.append(out["VFB"]); Veff_hist.append(out["Veff"]); QFG_hist.append(out["QFG"]); mmean_hist.append(out["m_mean"]); rho_store.append(out["rho_x"].copy()); mx_store.append(out["m_x"].copy()); F_hist.append(out["F_mean"]); Tprog_hist.append(out["Tprog_mean"]); Terase_hist.append(out["Terase_mean"])
    return {"P0": P0, "P1": P1, "P2": P2, "C": np.array(C_hist), "VFB": np.array(VFB_hist), "Veff": np.array(Veff_hist), "QFG": np.array(QFG_hist), "m_mean": np.array(mmean_hist), "rho_xt": np.array(rho_store), "m_xt": np.array(mx_store), "F_mean": np.array(F_hist), "Tprog_mean": np.array(Tprog_hist), "Terase_mean": np.array(Terase_hist), "VFB0": VFB0_value}


def simulate_cv_hysteresis_distributed(Vmin=-3.0, Vmax=3.0, npts=241, Nx=Nx_default, d_nc=d_nc_default, eta=eta_default, T=T_default, N_profile="front_loaded", dwell_time=dwell_time_per_step):
    x, dx = fg_grid(Nx=Nx)
    Vf = np.linspace(Vmin, Vmax, npts); Vb = np.linspace(Vmax, Vmin, npts)
    P0i, P1i, P2i = initialize_fg_state(Nx=Nx)
    fwd = run_cv_sweep_distributed(Vf, P0i, P1i, P2i, x, dx, d_nc=d_nc, eta=eta, T=T, N_profile=N_profile, dwell_time=dwell_time)
    bwd = run_cv_sweep_distributed(Vb, fwd["P0"], fwd["P1"], fwd["P2"], x, dx, d_nc=d_nc, eta=eta, T=T, N_profile=N_profile, dwell_time=dwell_time)
    Vmid_f = midpoint_voltage(Vf, fwd["C"]); Vmid_b = midpoint_voltage(Vb, bwd["C"])
    return {"x": x, "dx": dx, "Vf": Vf, "Vb": Vb, "forward": fwd, "backward": bwd, "memory_window": Vmid_b - Vmid_f, "Vmid_f": Vmid_f, "Vmid_b": Vmid_b}


def simulate_retention_flatband(P0_init, P1_init, P2_init, x, dx, d_nc=d_nc_default, eta=eta_default, T=T_default, N_profile="front_loaded", times=None):
    cox_eq = equivalent_oxide_capacitance(); VFB0_value = V_FB0(cox_eq=cox_eq, T=T)
    if times is None:
        times = np.logspace(np.log10(ret_t_start), np.log10(ret_t_stop), ret_npts)
    P0, P1, P2 = P0_init.copy(), P1_init.copy(), P2_init.copy()
    Q_hist=[]; VFB_hist=[]; m_hist=[]; rho_store=[]
    N_eff_x = N_eff_profile(x, d_nc=d_nc, eta=eta, profile=N_profile)
    rho0 = rho_FG(P1, P2, N_eff_x); Q0 = total_QFG_per_area(rho0, dx)
    Q_hist.append(Q0); VFB_hist.append(dynamic_VFB(VFB0_value, Q0, cox_eq)); m_hist.append(float(np.mean(occupancy(P1, P2)))); rho_store.append(rho0.copy())
    t_prev = times[0]
    for t in times[1:]:
        dt_total = t - t_prev; t_prev = t
        nsteps = max(1, int(math.ceil(dt_total / dt_internal))); dt_loc = dt_total / nsteps
        for _ in range(nsteps):
            out = one_voltage_point_relax(P0, P1, P2, Vg=VFB0_value, x=x, dx=dx, d_nc=d_nc, eta=eta, T=T, N_profile=N_profile, dwell_time=dt_loc, dt=dt_loc, cox_eq=cox_eq, VFB0_value=VFB0_value)
            P0, P1, P2 = out["P0"], out["P1"], out["P2"]
        Q_hist.append(out["QFG"]); VFB_hist.append(out["VFB"]); m_hist.append(out["m_mean"]); rho_store.append(out["rho_x"].copy())
    return {"times": np.array(times), "QFG": np.array(Q_hist), "VFB": np.array(VFB_hist), "m_mean": np.array(m_hist), "rho_xt": np.array(rho_store), "Vhold": VFB0_value}


def simulate_pulses_distributed(x, dx, Vprog=4.0, Verase=-4.0, Vread=0.0, t_prog=1.0, t_wait1=1.0, t_erase=1.0, t_wait2=1.0, d_nc=d_nc_default, eta=eta_default, T=T_default, N_profile="front_loaded"):
    cox_eq = equivalent_oxide_capacitance(); VFB0_value = V_FB0(cox_eq=cox_eq, T=T)
    P0, P1, P2 = initialize_fg_state(len(x))
    segments = [("program", Vprog, t_prog), ("wait1", Vread, t_wait1), ("erase", Verase, t_erase), ("wait2", Vread, t_wait2)]
    times=[0.0]; Vg_hist=[0.0]; Q_hist=[]; m_hist=[]; rho_store=[]
    N_eff_x = N_eff_profile(x, d_nc=d_nc, eta=eta, profile=N_profile)
    rho0 = rho_FG(P1, P2, N_eff_x); Q_hist.append(total_QFG_per_area(rho0, dx)); m_hist.append(float(np.mean(occupancy(P1, P2)))); rho_store.append(rho0.copy())
    t_now = 0.0
    for _, Vg, duration in segments:
        nsteps = max(1, int(math.ceil(duration / dt_internal)))
        for _ in range(nsteps):
            t_now += dt_internal
            out = one_voltage_point_relax(P0, P1, P2, Vg=Vg, x=x, dx=dx, d_nc=d_nc, eta=eta, T=T, N_profile=N_profile, dwell_time=dt_internal, dt=dt_internal, cox_eq=cox_eq, VFB0_value=VFB0_value)
            P0, P1, P2 = out["P0"], out["P1"], out["P2"]
            times.append(t_now); Vg_hist.append(Vg); Q_hist.append(out["QFG"]); m_hist.append(out["m_mean"]); rho_store.append(out["rho_x"].copy())
    return {"times": np.array(times), "Vg": np.array(Vg_hist), "QFG": np.array(Q_hist), "m_mean": np.array(m_hist), "rho_xt": np.array(rho_store)}


def sweep_diameter(d_values, Nx=Nx_default, eta=eta_default, T=T_default, N_profile="front_loaded", dwell_time=dwell_time_per_step):
    out=[]
    for d_nc in d_values:
        sim = simulate_cv_hysteresis_distributed(Nx=Nx, d_nc=d_nc, eta=eta, T=T, N_profile=N_profile, dwell_time=dwell_time)
        out.append({"d_nm": d_nc * 1e9, "MW": sim["memory_window"], "Ec_eV": charging_energy(d_nc) / Q, "gamma_c": gamma_c(d_nc, T=T), "QFG_max": float(np.max(sim["forward"]["QFG"])), "m_max_forward": float(np.max(sim["forward"]["m_mean"])), "m_end_backward": float(sim["backward"]["m_mean"][-1])})
    return out


def fig_cv(sim, title="Distributed FG hysteretic C-V"):
    fig = plt.figure(figsize=(8, 5)); plt.plot(sim["Vf"], sim["forward"]["C"], label="Forward"); plt.plot(sim["Vb"], sim["backward"]["C"], label="Backward"); plt.xlabel("Gate voltage (V)"); plt.ylabel("Capacitance density (F/m²)"); plt.title(title); plt.grid(True); plt.legend(); return fig


def fig_rho_profile(x, rho_xt, idx, title="rho_FG(x,t)"):
    fig = plt.figure(figsize=(8, 5)); plt.plot(x * 1e9, rho_xt[idx]); plt.xlabel("x in FG (nm)"); plt.ylabel("rho_FG(x,t) (C/m^3)"); plt.title(title); plt.grid(True); return fig


def fig_rho_heatmap(x, axis_values, rho_xt, title="rho_FG(x,t) heatmap", y_label="Index"):
    fig = plt.figure(figsize=(8, 5)); plt.imshow(rho_xt, origin="lower", aspect="auto", extent=[x[0]*1e9, x[-1]*1e9, axis_values[0], axis_values[-1]]); plt.colorbar(label="rho_FG (C/m^3)"); plt.xlabel("x in FG (nm)"); plt.ylabel(y_label); plt.title(title); return fig


def fig_retention(ret, title="Retention at flat-band"):
    fig = plt.figure(figsize=(8, 5)); plt.semilogx(ret["times"], ret["QFG"], label="QFG"); plt.semilogx(ret["times"], ret["m_mean"], label="m_mean"); plt.xlabel("Time (s)"); plt.ylabel("Value"); plt.title(title); plt.grid(True, which="both"); plt.legend(); return fig


def fig_pulses(pulse, title="Program / erase pulses"):
    fig = plt.figure(figsize=(8, 5)); plt.plot(pulse["times"], pulse["Vg"], label="Vg"); plt.plot(pulse["times"], pulse["QFG"], label="QFG"); plt.plot(pulse["times"], pulse["m_mean"], label="m_mean"); plt.xlabel("Time (s)"); plt.ylabel("Value"); plt.title(title); plt.grid(True); plt.legend(); return fig


def fig_diameter(sweep, title="Memory window vs nanocrystal diameter"):
    d_nm = np.array([r["d_nm"] for r in sweep]); MW = np.array([r["MW"] for r in sweep]); fig = plt.figure(figsize=(8, 5)); plt.plot(d_nm, MW, marker="o"); plt.xlabel("d_NC (nm)"); plt.ylabel("Memory window (V)"); plt.title(title); plt.grid(True); return fig


def export_cv(sim, tag="cv_distributed"):
    headers = ["Vg_V", "C_Fm2", "QFG_Cm2", "VFB_V", "Veff_V", "m_mean", "F_mean_Vm", "Tprog_mean", "Terase_mean"]
    f_rows = list(zip(sim["Vf"], sim["forward"]["C"], sim["forward"]["QFG"], sim["forward"]["VFB"], sim["forward"]["Veff"], sim["forward"]["m_mean"], sim["forward"]["F_mean"], sim["forward"]["Tprog_mean"], sim["forward"]["Terase_mean"]))
    b_rows = list(zip(sim["Vb"], sim["backward"]["C"], sim["backward"]["QFG"], sim["backward"]["VFB"], sim["backward"]["Veff"], sim["backward"]["m_mean"], sim["backward"]["F_mean"], sim["backward"]["Tprog_mean"], sim["backward"]["Terase_mean"]))
    save_csv(f"{tag}_forward.csv", headers, f_rows); save_csv(f"{tag}_backward.csv", headers, b_rows)


def export_rho_xt(x, axis_values, rho_xt, filename="rho_xt.csv", axis_name="axis"):
    rows=[]
    for i, a in enumerate(axis_values):
        for j, xx in enumerate(x):
            rows.append([a, xx, rho_xt[i, j]])
    save_csv(filename, [axis_name, "x_m", "rho_Cm3"], rows)


def main():
    cox_eq = equivalent_oxide_capacitance(); Vfb0 = V_FB0(cox_eq=cox_eq, T=T_default); Ec0 = charging_energy(d_nc_default) / Q; gc0 = gamma_c(d_nc_default, T=T_default)
    print("=" * 78); print("UNIFIED NC MEMORY MODEL V5.3 (TRAPEZOIDAL WKB + DWELL TIME)"); print("=" * 78); print("Outputs saved in:", os.path.abspath(OUTPUT_DIR)); print(f"Cox_eq       = {cox_eq:.4e} F/m^2"); print(f"V_FB0        = {Vfb0:.4f} V"); print(f"E_c          = {Ec0:.4e} eV"); print(f"gamma_c      = {gc0:.4f}"); print(f"dwell/point  = {dwell_time_per_step:.4e} s\n")
    sim = simulate_cv_hysteresis_distributed(Nx=Nx_default, d_nc=d_nc_default, eta=eta_default, T=T_default, N_profile="front_loaded", dwell_time=dwell_time_per_step)
    print(f"Reference MW = {sim['memory_window']:.4f} V"); print(f"QFG max fwd  = {np.max(sim['forward']['QFG']):.4e} C/m^2"); print(f"m max fwd    = {np.max(sim['forward']['m_mean']):.4f}\n")
    export_cv(sim, "cv_distributed"); export_rho_xt(sim["x"], sim["Vf"], sim["forward"]["rho_xt"], "rho_forward_xt.csv", "Vg_forward"); export_rho_xt(sim["x"], sim["Vb"], sim["backward"]["rho_xt"], "rho_backward_xt.csv", "Vg_backward")
    fig = fig_cv(sim, "Distributed FG hysteretic C-V (trapezoidal WKB)"); save_figure(fig, "cv_distributed.png"); save_figure(fig, "cv_distributed.pdf"); plt.close(fig)
    fig = fig_rho_profile(sim["x"], sim["forward"]["rho_xt"], idx=len(sim["Vf"])//2, title="rho_FG(x) at mid forward sweep"); save_figure(fig, "rho_profile_mid_forward.png"); save_figure(fig, "rho_profile_mid_forward.pdf"); plt.close(fig)
    fig = fig_rho_heatmap(sim["x"], sim["Vf"], sim["forward"]["rho_xt"], title="Forward rho_FG(x,Vg) heatmap", y_label="Vg (V)"); save_figure(fig, "rho_forward_heatmap.png"); save_figure(fig, "rho_forward_heatmap.pdf"); plt.close(fig)
    ret = simulate_retention_flatband(sim["forward"]["P0"], sim["forward"]["P1"], sim["forward"]["P2"], sim["x"], sim["dx"], d_nc=d_nc_default, eta=eta_default, T=T_default, N_profile="front_loaded")
    save_csv("retention_flatband.csv", ["time_s", "QFG_Cm2", "VFB_V", "m_mean"], list(zip(ret["times"], ret["QFG"], ret["VFB"], ret["m_mean"]))); export_rho_xt(sim["x"], ret["times"], ret["rho_xt"], "rho_retention_xt.csv", "time_s")
    fig = fig_retention(ret, "Retention at flat-band"); save_figure(fig, "retention_flatband.png"); save_figure(fig, "retention_flatband.pdf"); plt.close(fig)
    fig = fig_rho_heatmap(sim["x"], ret["times"], ret["rho_xt"], title="Retention rho_FG(x,t) heatmap", y_label="time (s)"); save_figure(fig, "rho_retention_heatmap.png"); save_figure(fig, "rho_retention_heatmap.pdf"); plt.close(fig)
    pulse = simulate_pulses_distributed(sim["x"], sim["dx"], d_nc=d_nc_default, eta=eta_default, T=T_default, N_profile="front_loaded")
    save_csv("pulses_distributed.csv", ["time_s", "Vg_V", "QFG_Cm2", "m_mean"], list(zip(pulse["times"], pulse["Vg"], pulse["QFG"], pulse["m_mean"]))); export_rho_xt(sim["x"], pulse["times"], pulse["rho_xt"], "rho_pulses_xt.csv", "time_s")
    fig = fig_pulses(pulse, "Program / erase pulses"); save_figure(fig, "pulses_distributed.png"); save_figure(fig, "pulses_distributed.pdf"); plt.close(fig)
    d_values = np.linspace(3e-9, 9e-9, 19); sw = sweep_diameter(d_values, Nx=Nx_default, eta=eta_default, T=T_default, N_profile="front_loaded", dwell_time=dwell_time_per_step)
    save_csv("diameter_sweep.csv", ["d_nm", "MW_V", "Ec_eV", "gamma_c", "QFG_max_Cm2", "m_max_forward", "m_end_backward"], [[r["d_nm"], r["MW"], r["Ec_eV"], r["gamma_c"], r["QFG_max"], r["m_max_forward"], r["m_end_backward"]] for r in sw])
    fig = fig_diameter(sw, "Memory window vs nanocrystal diameter"); save_figure(fig, "diameter_sweep.png"); save_figure(fig, "diameter_sweep.pdf"); plt.close(fig)
    best = max(sw, key=lambda r: r["MW"]); print("Best diameter in raw sweep:"); print(f"  d_NC      = {best['d_nm']:.3f} nm"); print(f"  MW        = {best['MW']:.4f} V"); print(f"  E_c       = {best['Ec_eV']:.4e} eV"); print(f"  gamma_c   = {best['gamma_c']:.4f}")
    save_json("run_metadata.json", {"Cox_eq_Fm2": cox_eq, "VFB0_V": Vfb0, "Ec_reference_eV": Ec0, "gamma_c_reference": gc0, "memory_window_reference_V": sim["memory_window"], "QFG_max_forward_Cm2": float(np.max(sim["forward"]["QFG"])), "m_max_forward": float(np.max(sim["forward"]["m_mean"])), "best_raw_diameter": best, "parameters": {"eta": eta_default, "d_nc_nm": d_nc_default * 1e9, "Phi_B_prog_eV": Phi_B_prog_eV, "Phi_B_erase_eV": Phi_B_erase_eV, "E_inj_eV": E_inj_eV, "nu0": nu0_default, "nu1": nu1_default, "nu2": nu2_default, "dwell_time_per_step": dwell_time_per_step, "dt_internal": dt_internal, "N_WKB": N_WKB}})

if __name__ == "__main__":
    main()
