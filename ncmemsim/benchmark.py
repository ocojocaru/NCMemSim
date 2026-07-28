from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from time import perf_counter
import tracemalloc

from .builder import DeviceBuilder
from .simulator import Simulator
from .state import DeviceState


@dataclass(frozen=True)
class BenchmarkRecord:
    case: str
    n_fgs: int
    elapsed_s: float
    peak_memory_bytes: int
    qfg_C_m2: float


def benchmark_case(n_fgs: int, repeats: int = 3) -> BenchmarkRecord:
    if repeats < 1:
        raise ValueError("repeats must be positive")
    device = DeviceBuilder.v2(n_fgs)
    sim = Simulator(device)
    best = float("inf")
    peak = 0
    qfg = 0.0
    for _ in range(repeats):
        state = DeviceState.empty_for_device(device)
        tracemalloc.start()
        start = perf_counter()
        out = sim.relax_voltage(state, 2.0, dwell_time_s=2e-5, internal_dt_s=1e-5)
        elapsed = perf_counter() - start
        _, current_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        best = min(best, elapsed)
        peak = max(peak, current_peak)
        qfg = float(out["qfg_C_m2"])
    return BenchmarkRecord(f"v2_{n_fgs}fg", n_fgs, best, peak, qfg)


def run_benchmark_suite(repeats: int = 3) -> list[BenchmarkRecord]:
    return [benchmark_case(n, repeats=repeats) for n in (1, 2, 3)]


def write_benchmark_report(path: str | Path, repeats: int = 3) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "records": [asdict(r) for r in run_benchmark_suite(repeats)]}
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target
