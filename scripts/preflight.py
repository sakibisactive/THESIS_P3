#!/usr/bin/env python3
"""Preflight system checks and environment validation script."""

import hashlib
import json
import multiprocessing
import os
import platform
import shutil
import subprocess
import sys

OUTPUT_DIR = "outputs/thesis_results"


def get_git_info() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
    except Exception:
        return "unknown"


def get_sumo_version() -> str:
    try:
        out = subprocess.check_output(["sumo", "--version"]).decode("utf-8").strip()
        return out.split("\n")[0]
    except Exception:
        return "unknown"


def get_network_checksum(filepath: str) -> str:
    try:
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception:
        return "unknown"


def run_checks() -> dict:
    print("============================================================")
    print("              THESIS SYSTEM PREFLIGHT CHECK")
    print("============================================================")

    # 1. Python Version
    py_version = sys.version
    py_ok = sys.version_info >= (3, 10)
    print(f"Python Version: {py_version.split()[0]} -> {'OK' if py_ok else 'WARNING (>=3.10 recommended)'}")

    # 2. SUMO Installation
    sumo_v = get_sumo_version()
    sumo_ok = sumo_v != "unknown"
    print(f"SUMO Version: {sumo_v} -> {'OK' if sumo_ok else 'FAILED (sumo not found)'}")

    # 3. Required Dependencies
    dependencies = ["numpy", "scipy", "matplotlib", "pydantic", "yaml", "traci"]
    missing = []
    for dep in dependencies:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)
    
    deps_ok = len(missing) == 0
    print(f"Dependencies: {'OK' if deps_ok else 'FAILED (missing: ' + ', '.join(missing) + ')'}")

    # 4. Manhattan Network Checksum
    net_path = "data/networks/midtown_manhattan.net.xml"
    net_exists = os.path.exists(net_path)
    expected_sha = "c2f5702163acf3377f74e03e4bce9598f17aeab54f245edc3daf12de8bf63275"
    actual_sha = get_network_checksum(net_path) if net_exists else "none"
    net_ok = net_exists and actual_sha == expected_sha
    print(f"Network File: {net_path} -> {'OK' if net_ok else 'FAILED'}")
    if net_exists:
        print(f"  - SHA256: {actual_sha}")
    else:
        print("  - File NOT found!")

    # 5. Disk Space
    total, used, free = shutil.disk_usage(".")
    free_gb = free / (1024**3)
    space_ok = free_gb >= 1.0  # Require at least 1GB free
    print(f"Free Disk Space: {free_gb:.2f} GB -> {'OK' if space_ok else 'WARNING (<1GB)'}")

    # 6. CPU Core Count
    cores = multiprocessing.cpu_count()
    print(f"CPU Cores: {cores} -> {'OK (multiprocessing enabled)' if cores > 1 else 'OK (sequential only)'}")

    # Compile environment snapshot
    snapshot = {
        "timestamp": platform.node(),
        "os": platform.platform(),
        "python_version": py_version,
        "sumo_version": sumo_v,
        "git_commit": get_git_info(),
        "cores": cores,
        "free_disk_space_gb": free_gb,
        "network_file": net_path,
        "network_sha256": actual_sha,
        "dependencies": {dep: "installed" if dep not in missing else "missing" for dep in dependencies},
        "all_checks_passed": py_ok and sumo_ok and deps_ok and net_ok and space_ok
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    snapshot_path = os.path.join(OUTPUT_DIR, "environment_snapshot.json")
    with open(snapshot_path, "w") as f:
        json.dump(snapshot, f, indent=2)
    print(f"-> Environment snapshot saved to: {snapshot_path}")

    print("============================================================")
    if snapshot["all_checks_passed"]:
        print("                 PREFLIGHT SUCCESSFUL")
    else:
        print("                 PREFLIGHT FAILED / WARNINGS")
    print("============================================================")
    return snapshot


if __name__ == "__main__":
    snapshot = run_checks()
    if not snapshot["all_checks_passed"]:
        sys.exit(1)
