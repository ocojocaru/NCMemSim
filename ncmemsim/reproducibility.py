from __future__ import annotations

from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
import os
from pathlib import Path
import platform
import subprocess
from typing import Any

import numpy as np

from ._version import __version__
from .device import Device
from .hashing import canonical_hash


def software_version() -> str:
    try:
        return version("ncmemsim")
    except PackageNotFoundError:
        return __version__


def git_commit(cwd: str | Path | None = None) -> str | None:
    env_commit = os.environ.get("GITHUB_SHA")
    if env_commit:
        return env_commit
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def build_reproducibility_manifest(
    device: Device,
    *,
    physics_model: str = "PhaseD6",
    simulation_config: dict[str, Any] | None = None,
    random_seed: int | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    materials = []
    seen = set()
    for fg in device.floating_gates():
        mat = fg.nc_material
        key = (mat.name, mat.model_version)
        if key not in seen:
            seen.add(key)
            materials.append(mat.to_dict())

    device_dict = device.to_dict()
    config = simulation_config or {}

    result = {
        "schema_version": 2,
        "software_version": software_version(),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "runtime": {
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "numpy_version": np.__version__,
        },
        "device": device_dict,
        "device_hash": canonical_hash(device_dict),
        "physics_model": physics_model,
        "simulation_config": config,
        "simulation_hash": canonical_hash(
            {
                "device": device_dict,
                "physics_model": physics_model,
                "config": config,
            }
        ),
        "material_models": materials,
        "random_seed": random_seed,
    }

    if extra:
        result["extra"] = extra

    return result


__all__ = [
    "build_reproducibility_manifest",
    "canonical_hash",
    "git_commit",
    "software_version",
]
