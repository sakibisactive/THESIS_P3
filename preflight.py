#!/usr/bin/env python3
"""
preflight.py — System readiness checker for the E³-Hybrid Thesis Simulator.

Verifies Python version, SUMO (system binary and Python bindings separately),
required packages, network file integrity, disk space, CPU count, and write
permissions. Prints available experiment presets regardless of check results.

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

# Pure Python packages (installed via pip)
PYTHON_PACKAGES = [
    ("numpy",      "numpy"),
    ("scipy",      "scipy"),
    ("matplotlib", "matplotlib"),
    ("pydantic",   "pydantic"),
    ("yaml",       "pyyaml"),
]

# Python SUMO bindings (installed via pip install eclipse-sumo OR as part of
# the system SUMO distribution under $SUMO_HOME/tools)
SUMO_PYTHON_BINDINGS = [
    ("traci",   "traci   (pip install eclipse-sumo  OR  install system SUMO)"),
    ("sumolib", "sumolib (pip install eclipse-sumo  OR  install system SUMO)"),
]

# System executables (separate from Python bindings)
SUMO_SYSTEM_TOOLS = ["sumo", "sumo-gui", "netconvert"]

PRESETS = {
    "smoke":   ("~30 s",   "2 algorithms × 1 scenario × 25 vehicles × 1 seed  (2 runs)"),
    "light":   ("~5 min",  "3 algorithms × 2 scenarios × 25 vehicles × 2 seeds (12 runs)"),
    "heavy":   ("~1-2 h",  "6 algorithms × 6 scenarios × 4 vehicle counts × 10 seeds (1,440 runs)"),
    "extreme": ("~4-8 h",  "Same as heavy but with full research-mode swarm parameters"),
}

# ─────────────────────────────────────────────────────────────────────────────
# ANSI colours (disabled automatically when not a TTY)
# ─────────────────────────────────────────────────────────────────────────────
_USE_COLOR = sys.stdout.isatty()
GREEN  = "\033[92m" if _USE_COLOR else ""
RED    = "\033[91m" if _USE_COLOR else ""
YELLOW = "\033[93m" if _USE_COLOR else ""
BOLD   = "\033[1m"  if _USE_COLOR else ""
DIM    = "\033[2m"  if _USE_COLOR else ""
RESET  = "\033[0m"  if _USE_COLOR else ""

WIDTH = 62


def _ok(msg: str) -> None:
    print(f"  {GREEN}✔{RESET}  {msg}")


def _fail(msg: str) -> None:
    print(f"  {RED}✘{RESET}  {msg}")


def _warn(msg: str) -> None:
    print(f"  {YELLOW}⚠{RESET}  {msg}")


def _info(msg: str) -> None:
    print(f"  {DIM}ℹ{RESET}  {msg}")


def _header(title: str) -> None:
    print()
    print(BOLD + "─" * WIDTH + RESET)
    print(BOLD + f"  {title}" + RESET)
    print(BOLD + "─" * WIDTH + RESET)


# ─────────────────────────────────────────────────────────────────────────────
# Individual checks
# ─────────────────────────────────────────────────────────────────────────────

def check_python() -> bool:
    major, minor, micro = sys.version_info[:3]
    ver = f"{major}.{minor}.{micro}"
    if (major, minor) >= REQUIRED_PYTHON:
        _ok(f"Python {ver}")
        return True
    _fail(f"Python {ver}  (need >= {'.'.join(map(str, REQUIRED_PYTHON))})")
    return False


def check_sumo_binary() -> tuple[bool, str]:
    """Checks that the *system* SUMO binary is on $PATH."""
    try:
        raw = subprocess.check_output(
            ["sumo", "--version"], stderr=subprocess.STDOUT
        ).decode().strip()
        version_line = raw.split("\n")[0]
        _ok(f"sumo binary  →  {version_line}")
    except FileNotFoundError:
        _fail("sumo binary not found on $PATH.")
        _info("Install SUMO: https://sumo.dlr.de/docs/Installing/index.html")
        return False, "not found"
    except subprocess.CalledProcessError as exc:
        version_line = exc.output.decode().split("\n")[0] if exc.output else "unknown"
        _ok(f"sumo binary  →  {version_line}")

    # Optional system tools (warnings, not failures)
    for tool in ["sumo-gui", "netconvert"]:
        if shutil.which(tool):
            _ok(f"{tool} found")
        else:
            _warn(f"{tool} not found (optional — only needed for GUI / OSM import)")

    return True, version_line


def check_sumo_python_bindings() -> bool:
    """Checks the Python SUMO bindings (traci, sumolib) — separate from binary."""
    all_ok = True
    for import_name, label in SUMO_PYTHON_BINDINGS:
        try:
            __import__(import_name)
            _ok(label.split("(")[0].strip())
        except ImportError:
            _fail(label)
            all_ok = False
    return all_ok


def check_python_packages() -> bool:
    all_ok = True
    for import_name, package_name in PYTHON_PACKAGES:
        try:
            __import__(import_name)
            _ok(package_name)
        except ImportError:
            _fail(f"{package_name}  →  pip install {package_name}")
            all_ok = False
    return all_ok


def check_network_file() -> tuple[bool, str]:
    if not NETWORK_FILE.exists():
        _fail(f"Not found: {NETWORK_FILE.relative_to(REPO_ROOT)}")
        _info("Place your compiled .net.xml at: data/networks/midtown_manhattan.net.xml")
        return False, "missing"

    sha256 = hashlib.sha256()
    with open(NETWORK_FILE, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    actual = sha256.hexdigest()
    size_mb = NETWORK_FILE.stat().st_size / (1024 ** 2)

    if actual == NETWORK_SHA256:
        _ok(
            f"midtown_manhattan.net.xml  ({size_mb:.1f} MB)\n"
            f"       SHA256  {actual[:32]}…  ✔"
        )
        return True, actual
    else:
        _warn(
            f"midtown_manhattan.net.xml found ({size_mb:.1f} MB) — SHA256 mismatch.\n"
            f"       Expected: {NETWORK_SHA256[:32]}…\n"
            f"       Got:      {actual[:32]}…\n"
            f"       File will be used, but reproducibility cannot be guaranteed."
        )
        return True, actual   # file exists; mismatch is a warning, not a hard failure


def check_disk_space() -> bool:
    _, _, free = shutil.disk_usage(REPO_ROOT)
    free_gb = free / (1024 ** 3)
    if free_gb >= MIN_FREE_DISK_GB:
        _ok(f"{free_gb:.1f} GB free  (minimum {MIN_FREE_DISK_GB:.0f} GB required)")
        return True
    _fail(f"Only {free_gb:.1f} GB free — at least {MIN_FREE_DISK_GB:.0f} GB required.")
    return False


def check_cpu() -> int:
    cores = multiprocessing.cpu_count()
    note = "multiprocessing will be used" if cores > 1 else "sequential execution only"
    _ok(f"{cores} CPU core{'s' if cores > 1 else ''} detected  ({note})")
    return cores


def check_write_permissions() -> bool:
    try:
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        test = OUTPUTS_DIR / ".write_test"
        test.touch()
        test.unlink()
        _ok(f"Write permission OK  →  {OUTPUTS_DIR.relative_to(REPO_ROOT)}/")
        return True
    except OSError as exc:
        _fail(f"Cannot write to {OUTPUTS_DIR.relative_to(REPO_ROOT)}/: {exc}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Preset summary (always printed)
# ─────────────────────────────────────────────────────────────────────────────

def print_presets() -> None:
    print()
    print(BOLD + "─" * WIDTH + RESET)
    print(BOLD + "  Available Experiment Presets" + RESET)
    print(BOLD + "─" * WIDTH + RESET)
    for name, (runtime, desc) in PRESETS.items():
        flag = f"--preset {name}"
        print(f"\n  {BOLD}{flag:<22}{RESET}  {runtime}")
        print(f"  {DIM}{desc}{RESET}")
    print()
    print(f"  {BOLD}Run:{RESET}  python run_thesis.py --preset heavy")
    print(f"  {BOLD}Help:{RESET} python run_thesis.py --help")


# ─────────────────────────────────────────────────────────────────────────────
# Snapshot
# ─────────────────────────────────────────────────────────────────────────────

def save_snapshot(data: dict) -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOT_DIR / "environment_snapshot.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\n  Snapshot → {path.relative_to(REPO_ROOT)}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    print(BOLD + "\n  E³-Hybrid Thesis — Pre-flight System Check" + RESET)

    failures: list[str] = []

    _header("Python")
    if not check_python():
        failures.append("python_version")

    _header("SUMO — System Binary")
    sumo_ok, sumo_ver = check_sumo_binary()
    if not sumo_ok:
        failures.append("sumo_binary")

    _header("SUMO — Python Bindings  (traci / sumolib)")
    _info("These are separate from the system binary.")
    _info("Install with:  pip install eclipse-sumo")
    if not check_sumo_python_bindings():
        failures.append("sumo_python_bindings")

    _header("Python Packages")
    if not check_python_packages():
        failures.append("python_packages")

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

    # Always save snapshot (captures partial state too)
    save_snapshot({
        "timestamp": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
        "os": platform.platform(),
        "python_version": sys.version,
        "sumo_version": sumo_ver,
        "cpu_cores": cores,
        "network_file": str(NETWORK_FILE.relative_to(REPO_ROOT)),
        "network_sha256": net_sha,
        "all_checks_passed": len(failures) == 0,
        "failures": failures,
    })

    # Result banner
    print()
    print(BOLD + "─" * WIDTH + RESET)
    if not failures:
        print(f"{GREEN}{BOLD}  ✔  ALL CHECKS PASSED — ready to run benchmarks.{RESET}")
    else:
        print(f"{RED}{BOLD}  ✘  PREFLIGHT FAILED  [{', '.join(failures)}]{RESET}")
        print(f"{YELLOW}     Fix the issues above, then re-run: python preflight.py{RESET}")
    print(BOLD + "─" * WIDTH + RESET)

    # Always print available presets
    print_presets()

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
