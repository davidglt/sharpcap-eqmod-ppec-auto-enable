#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Created: 2026-08-28
# Author: David González López-Tercero <davidglt@dragonit.es>
# SPDX-FileCopyrightText: 2026 David González López-Tercero <davidglt@dragonit.es>
# SPDX-License-Identifier: GPL-3.0-or-later

r"""
ppec_auto_enable.py — Automatic PPEC activation for EQMOD/EQASCOM.

SharpCap IronPython Startup Script  --  v1.0.2
Place this file in SharpCap Settings -> Scripting ->
"Run these Python scripts when SharpCap starts".

Why a subprocess?
-----------------
SharpCap runs scripts in IronPython, whose mount.AscomMount wrapper
does NOT expose the low-level EQMOD motor-controller passthrough in a
useful way for mount-native PPEC activation.

EQASCOM is a COM local server that supports multiple simultaneous
clients -- this is a second independent connection alongside SharpCap.
So we connect a second independent client (CPython + win32com) that
talks directly to EQMOD.Telescope and has full CommandString access.

This script (IronPython) waits for tracking, then launches the
CPython worker (ppec_worker.py) via the project .venv.

Non-blocking startup
--------------------
SharpCap executes startup scripts sequentially in the same thread.
To avoid blocking subsequent scripts (e.g. log_conditions.py from
bme280-observatory), the main logic runs in a background daemon thread
that returns control to SharpCap immediately.

Requirements
------------
From the project root:  .venv\Scripts\pip install -r requirements\requirements.txt
Both files must be in the same folder as .venv\

Author
------
David González López-Tercero

Contact
-------
Email: davidglt@dragonit.es
Website: https://www.dragonit.es

License
-------
GPL-3.0-or-later  <https://www.gnu.org/licenses/>
"""

import time
import datetime
import os
import subprocess

clr.AddReference("System.Threading")
from System.Threading import (
    AbandonedMutexException,
    ApartmentState,
    Mutex,
    Thread,
    ThreadStart,
)

# == CONFIGURATION ============================================================

CHECK_INTERVAL = 30   # seconds between polling attempts
MUTEX_NAME = "Local\\SharpCapEqmodPpecAutoEnable"

# CPython interpreter inside the project virtual environment.
# Assumes .venv is in the same folder as this script.
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE  = os.path.join(SCRIPT_DIR, ".venv", "Scripts", "python.exe")

# == LOGGING ==================================================================

def log(level, msg):
    """Write one timestamped message to the console and SharpCap log."""
    ts   = datetime.datetime.now().strftime("%H:%M:%S")
    line = "{}  {:8s}  [PPEC]  {}".format(ts, level, msg)
    print(line)
    try:
        SharpCap.WriteToLog(line)
    except Exception:
        pass

def info(msg):
    """Write an informational launcher message."""
    log("INFO", msg)


def error(msg):
    """Write an error launcher message."""
    log("ERROR", msg)

# == MAIN LOGIC ===============================================================

def enable_ppec_when_ready():
    """Wait for tracking, launch the worker once, and report its result."""
    mutex = Mutex(False, MUTEX_NAME)
    owns_mutex = False
    try:
        try:
            owns_mutex = mutex.WaitOne(0)
        except AbandonedMutexException:
            owns_mutex = True
            error("Recovered the PPEC auto-enable lock after an interrupted run.")

        if not owns_mutex:
            info("Another PPEC auto-enable instance is already active; skipping.")
            return

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
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=0x08000000,  # CREATE_NO_WINDOW
            )
        except Exception as exc:
            error("Could not launch worker: {}".format(exc))
            return

        info("Worker launched (PID {}).".format(proc.pid))
        info("Check logs/ppec_worker.log in: {}".format(SCRIPT_DIR))
        try:
            exit_code = proc.wait()
        except Exception as exc:
            error("Could not monitor worker completion: {}".format(exc))
        else:
            if exit_code == 0:
                info("Worker completed successfully (exit code 0).")
            else:
                error("Worker failed with exit code {}.".format(exit_code))

        info("END -- launcher finished.")
        info("=" * 52)
    finally:
        if owns_mutex:
            try:
                mutex.ReleaseMutex()
            except Exception as exc:
                error("Could not release the PPEC auto-enable lock: {}".format(exc))
        mutex.Close()


# == ENTRY POINT ==============================================================
# Run in a background daemon thread so SharpCap is not blocked and
# subsequent startup scripts execute immediately.

t = Thread(ThreadStart(enable_ppec_when_ready))
t.IsBackground = True
t.ApartmentState = ApartmentState.STA
t.Start()
