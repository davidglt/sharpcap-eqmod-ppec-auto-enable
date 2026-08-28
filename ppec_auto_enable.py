# ppec_auto_enable.py -- Automatic PPEC activation for EQMOD/EQASCOM.
#
# Copyright (C) 2026  David González López-Tercero
#
# This file is part of sharpcap-eqmod-ppec-auto-enable.
# <https://github.com/davidglt/sharpcap-eqmod-ppec-auto-enable>
#
# sharpcap-eqmod-ppec-auto-enable is free software: you can redistribute
# it and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# sharpcap-eqmod-ppec-auto-enable is distributed in the hope that it will
# be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with sharpcap-eqmod-ppec-auto-enable. If not, see
# <https://www.gnu.org/licenses/>.
#
# ---------------------------------------------------------------------------
# SharpCap IronPython Startup Script  --  v1.0.2
# Place this file in SharpCap Settings -> Scripting ->
# "Run these Python scripts when SharpCap starts".
#
# Why a subprocess?
# -----------------
# SharpCap runs scripts in IronPython, whose mount.AscomMount wrapper
# does NOT expose the low-level EQMOD motor-controller passthrough in a
# useful way for mount-native PPEC activation.
#
# EQASCOM is a COM local server that supports multiple simultaneous
# clients -- this is a second independent connection alongside SharpCap.
# So we connect a second independent client (CPython + win32com) that
# talks directly to EQMOD.Telescope and has full CommandString access.
#
# This script (IronPython) waits for tracking, then launches the
# CPython worker (ppec_worker.py) via the project .venv.
#
# Requirements
# ------------
# From the project root:  .venv\Scripts\pip install -r requirements\requirements.txt
# Both files must be in the same folder as .venv\
# ---------------------------------------------------------------------------

import time
import datetime
import os
import subprocess

# == CONFIGURATION ============================================================

CHECK_INTERVAL = 30   # seconds between polling attempts

# CPython interpreter inside the project virtual environment.
# Assumes .venv is in the same folder as this script.
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE  = os.path.join(SCRIPT_DIR, ".venv", "Scripts", "python.exe")

# == LOGGING ==================================================================

def log(level, msg):
    ts   = datetime.datetime.now().strftime("%H:%M:%S")
    line = "{}  {:8s}  [PPEC]  {}".format(ts, level, msg)
    print(line)
    try:
        SharpCap.WriteToLog(line)
    except Exception:
        pass

def info(msg):  log("INFO",    msg)
def error(msg): log("ERROR",   msg)

# == MAIN LOGIC ===============================================================

def enable_ppec_when_ready():
    info("=" * 52)
    info("PPEC Auto-Enable v1.0.2 starting...")
    info("Worker interpreter: {}".format(PYTHON_EXE))

    if not os.path.exists(PYTHON_EXE):
        error(".venv not found at: {}".format(PYTHON_EXE))
        error("Run from project root:  python -m venv .venv")
        error("Then:  .venv\\Scripts\\pip install -r requirements\\requirements.txt")
        info("END -- script finished with errors.")
        info("=" * 52)
        return

    # 1) Wait until SharpCap has a mount connected
    info("Waiting for mount (checking every {}s)...".format(CHECK_INTERVAL))
    mount = SharpCap.Mounts.SelectedMount
    while mount is None:
        info("No mount connected yet. Next check in {}s...".format(CHECK_INTERVAL))
        time.sleep(CHECK_INTERVAL)
        mount = SharpCap.Mounts.SelectedMount

    info("Mount found: {}".format(mount.Name))

    # 2) Wait until sidereal tracking starts
    info("Waiting for tracking (checking every {}s)...".format(CHECK_INTERVAL))
    while not mount.Tracking:
        info("Mount not tracking yet. Next check in {}s...".format(CHECK_INTERVAL))
        time.sleep(CHECK_INTERVAL)

    info("Tracking detected. Launching CPython worker...")

    # 3) Launch ppec_worker.py via .venv CPython
    worker_path = os.path.join(SCRIPT_DIR, "ppec_worker.py")

    if not os.path.exists(worker_path):
        error("Worker not found: {}".format(worker_path))
        info("END -- script finished with errors.")
        info("=" * 52)
        return

    try:
        proc = subprocess.Popen(
            [PYTHON_EXE, worker_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=0x08000000,  # CREATE_NO_WINDOW
        )
        info("Worker launched (PID {}).".format(proc.pid))
        info("Check logs/ppec_worker.log in: {}".format(SCRIPT_DIR))
    except Exception as exc:
        error("Could not launch worker: {}".format(exc))

    info("END -- launcher finished.")
    info("=" * 52)


enable_ppec_when_ready()
