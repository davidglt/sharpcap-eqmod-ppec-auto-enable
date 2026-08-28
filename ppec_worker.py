# ppec_worker.py -- CPython worker for PPEC activation.
#
# Copyright (C) 2026 David Gonzalez Lopez-Tercero
#
# This file is part of sharpcap-eqmod-ppec-auto-enable.
#
# sharpcap-eqmod-ppec-auto-enable is free software: you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# sharpcap-eqmod-ppec-auto-enable is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with sharpcap-eqmod-ppec-auto-enable. If not, see
# <https://www.gnu.org/licenses/>.
#
# ---------------------------------------------------------------------------
# CPython worker -- v1.0.0
#
# Activates mount-native PPEC on the EQ8-R Pro via EQMOD.Telescope
# CommandString passthrough. No UI automation required.
#
# How it works
# ------------
# EQMOD.Telescope.CommandString accepts low-level motor-controller
# passthroughs using the '>' prefix WITHOUT a trailing '#':
#
#   scope.CommandString('>:q1010000', False)  ->  '=060001\r' (PPEC off)
#                                                 '=260001\r' (PPEC on)
#   scope.CommandString('>:W1020000', False)  ->  '=\r'       (enable)
#   scope.CommandString('>:W1030000', False)  ->  '=\r'       (disable)
#
# Requirements
# ------------
# .venv\Scripts\pip install -r requirements\requirements.txt
#
# Log
# ---
# ppec_worker.log  (same folder as this script)
# ---------------------------------------------------------------------------

import time
import datetime
import sys
import os
import logging

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ppec_worker.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  [PPEC-worker]  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# == CONFIGURATION ============================================================

CONNECT_INTERVAL = 10
PPEC_ON_RESPONSE  = "=260001\r"
PPEC_OFF_RESPONSE = "=060001\r"

# == HELPERS ==================================================================

def motor_cmd(scope, command):
    return scope.CommandString(">" + command, False)


def read_ppec_status(scope):
    try:
        response = motor_cmd(scope, ":q1010000")
        log.info("PPEC query response: %r", response)
        if PPEC_ON_RESPONSE in response:
            return "ON"
        if PPEC_OFF_RESPONSE in response:
            return "OFF"
        return "unknown ({})".format(response.strip())
    except Exception as exc:
        log.error("Error querying PPEC status: %s", exc)
        return "error"

# == MAIN =====================================================================

def main():
    log.info("=" * 52)
    log.info("PPEC worker v1.0.0 starting -- %s",
             datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))

    try:
        import win32com.client
    except ImportError:
        log.error("pywin32 not installed.")
        log.error("Run: .venv\\Scripts\\pip install -r requirements\\requirements.txt")
        sys.exit(1)

    log.info("Waiting for EQMOD.Telescope (checking every %ds)...", CONNECT_INTERVAL)
    scope = None
    while True:
        try:
            s = win32com.client.Dispatch("EQMOD.Telescope")
            if not s.Connected:
                s.Connected = True
            if s.Tracking:
                scope = s
                log.info("EQMOD connected and tracking.")
                break
            log.info("Connected but not tracking yet. Next check in %ds...",
                     CONNECT_INTERVAL)
        except Exception as exc:
            log.info("EQMOD not ready (%s). Next check in %ds...",
                     exc, CONNECT_INTERVAL)
        time.sleep(CONNECT_INTERVAL)

    status = read_ppec_status(scope)
    log.info("PPEC status: %s", status)

    if status == "ON":
        log.info("PPEC already active. Nothing to do.")
        log.info("END -- worker finished successfully.")
        log.info("=" * 52)
        sys.exit(0)

    log.info("Enabling PPEC via :W1020000...")
    try:
        response = motor_cmd(scope, ":W1020000")
        log.info("Enable command response: %r", response)
    except Exception as exc:
        log.error("Failed to send enable command: %s", exc)
        sys.exit(1)

    time.sleep(2)
    final_status = read_ppec_status(scope)
    log.info("PPEC status after enable: %s", final_status)

    if final_status == "ON":
        log.info("PPEC firmware enabled and confirmed: PPEC is ON.")
    else:
        log.warning("PPEC status is '%s' after enable command. Check EQMOD Development Testing Area.", final_status)

    log.info("END -- worker finished successfully.")
    log.info("=" * 52)


if __name__ == "__main__":
    main()
