#!/usr/bin/env python3
"""
preflight.py — System readiness checker for the E³-Hybrid Thesis Simulator.

Run this before executing any benchmark to confirm the environment is
correctly configured. Exits with code 0 on success, 1 on failure.

Usage:
    python preflight.py
"""

import hashlib
import json
import multiprocessing
import os
import pathlib
import platform
import shutil
import subprocess
import sys

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
REPO_ROOT = pathlib.Path(__file__).resolve().parent
NETWORK_FILE = REPO_ROOT / "data" / "networks" / "midtown_manhattan.net.xml"
NETWORK_SHA256 = "c2f5702163acf3377f74e03e4bce9598f17aeab54f245edc3daf12de8bf63275"
OUTPUTS_DIR = REPO_ROOT / "outputs"
SNAPSHOT_DIR = REPO_ROOT / "outputs" / "thesis_results"

REQUIRED_PYTHON = (3, 10)
MIN_FREE_DISK_GB = 2.0

REQUIRED_PACKAGES = [
    ("numpy", "numpy"),
    ("scipy", "scipy"),
    ("matplotlib", "matplotlib"),
    ("pydantic", "pydantic"),
    ("yaml", "pyyaml"),
    ("traci", "eclipse-sumo"),
]

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _ok(msg: str) -> None:
    print(f"  {GREEN}✔{RESET}  {msg}")


def _fail(msg: str) -> None:
    print(f"  {RED}✘{RESET}  {msg}")


def _warn(msg: str) -> None:
    print(f"  {YELLOW}⚠{RESET}  {msg}")


def _header(title: str) -> None:
    width = 60
    print()
    print(BOLD + "─" * width + RESET)
    print(BOLD + f"  {title}" + RESET)
    print(BOLD + "─" * width + RESET)


# ─────────────────────────────────────────────────────────────────────────────
# Check functions — each returns True on pass, False on failure
# ─────────────────────────────────────────────────────────────────────────────

def check_python() -> bool:
    major, minor = sys.version_info[:2]
    ver = f"{major}.{minor}.{sys.version_info.micro}"
    if (major, minor) >= REQUIRED_PYTHON:
        _ok(f"Python {ver}")
        return True
    else:
        _fail(f"Python {ver}  (requires >= {'.'.join(map(str, REQUIRED_PYTHON))})")
        return False


def check_sumo() -> tuple[bool, str]:
    try:
        raw = subprocess.check_output(
            ["sumo", "--version"], stderr=subprocess.STDOUT
        ).decode().strip()
        version_line = raw.split("\n")[0]
        _ok(f"SUMO  →  {version_line}")
        return True, version_line
    except (FileNotFoundError, subprocess.CalledProcessError):
        _fail("sumo binary not found. Install SUMO and ensure it is on $PATH.")
        return False, "not found"


def check_dependencies() -> bool:
    all_ok = True
    for import_name, package_name in REQUIRED_PACKAGES:
        try:
            __import__(import_name)
            _ok(f"{package_name}")
        except ImportError:
            _fail(f"{package_name}  (run: pip install {package_name})")
            all_ok = False
    return all_ok


def check_network_file() -> tuple[bool, str]:
    if not NETWORK_FILE.exists():
        _fail(f"Network file not found: {NETWORK_FILE}")
        return False, "missing"

    sha256 = hashlib.sha256()
    with open(NETWORK_FILE, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    actual = sha256.hexdigest()

    size_mb = NETWORK_FILE.stat().st_size / (1024**2)
    if actual == NETWORK_SHA256:
        _ok(
            f"midtown_manhattan.net.xml  ({size_mb:.1f} MB)\n"
            f"       SHA256  {actual[:32]}…  ✔"
        )
        return True, actual
    else:
        _warn(
            f"midtown_manhattan.net.xml found but SHA256 mismatch.\n"
            f"       Expected: {NETWORK_SHA256[:32]}…\n"
            f"       Got:      {actual[:32]}…"
        )
        return True, actual  # file exists; mismatch is a warning not a blocker


def check_disk_space() -> bool:
    _, _, free = shutil.disk_usage(REPO_ROOT)
    free_gb = free / (1024**3)
    if free_gb >= MIN_FREE_DISK_GB:
        _ok(f"{free_gb:.1f} GB free (min {MIN_FREE_DISK_GB:.0f} GB required)")
        return True
    else:
        _fail(f"Only {free_gb:.1f} GB free — at least {MIN_FREE_DISK_GB:.0f} GB required.")
        return False


def check_cpu() -> int:
    cores = multiprocessing.cpu_count()
    _ok(f"{cores} CPU core{'s' if cores > 1 else ''} detected")
    return cores


def check_write_permissions() -> bool:
    try:
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        test_file = OUTPUTS_DIR / ".write_test"
        test_file.touch()
        test_file.unlink()
        _ok(f"Write permission  →  {OUTPUTS_DIR}")
        return True
    except OSError as e:
        _fail(f"Cannot write to {OUTPUTS_DIR}: {e}")
        return False


def save_snapshot(results: dict) -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOT_DIR / "environment_snapshot.json"
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Snapshot saved → {path.relative_to(REPO_ROOT)}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    print(BOLD + "\n  E³-Hybrid Thesis — Pre-flight System Check" + RESET)

    failures: list[str] = []

    _header("Python")
    if not check_python():
        failures.append("python_version")

    _header("SUMO Simulator")
    sumo_ok, sumo_version = check_sumo()
    if not sumo_ok:
        failures.append("sumo")

    _header("Python Dependencies")
    if not check_dependencies():
        failures.append("dependencies")

    _header("Manhattan Network File")
    net_ok, net_sha = check_network_file()
    if not net_ok:
        failures.append("network_file")

    _header("Disk Space")
    if not check_disk_space():
        failures.append("disk_space")

    _header("CPU")
    cores = check_cpu()

    _header("Output Write Permissions")
    if not check_write_permissions():
        failures.append("write_permissions")

    # ── Snapshot ──────────────────────────────────────────────────────────────
    snapshot = {
        "timestamp": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
        "os": platform.platform(),
        "python_version": sys.version,
        "sumo_version": sumo_version,
        "cpu_cores": cores,
        "network_file": str(NETWORK_FILE.relative_to(REPO_ROOT)),
        "network_sha256": net_sha,
        "all_checks_passed": len(failures) == 0,
        "failures": failures,
    }
    save_snapshot(snapshot)

    # ── Summary ───────────────────────────────────────────────────────────────
    width = 60
    print()
    print(BOLD + "─" * width + RESET)
    if not failures:
        print(f"{GREEN}{BOLD}  ✔  ALL CHECKS PASSED — ready to run benchmarks.{RESET}")
    else:
        print(f"{RED}{BOLD}  ✘  PREFLIGHT FAILED: {', '.join(failures)}{RESET}")
    print(BOLD + "─" * width + RESET + "\n")

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
