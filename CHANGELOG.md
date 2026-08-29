# Changelog

All notable changes to this project are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.0.2] - 2026-08-29

### Fixed

- `ppec_auto_enable.py`: the main logic (`enable_ppec_when_ready`) now runs
  in a **background daemon thread** (`System.Threading.Thread`,
  `IsBackground = True`, `ApartmentState.STA`).
  Previously the script blocked SharpCap's startup sequence while polling
  for mount connection and tracking — any subsequent startup script (e.g.
  `log_conditions.py` from *bme280-observatory*) would not execute until
  PPEC was fully activated.  The fix returns control to SharpCap
  immediately after the thread is started.

### Changed

- Version string in script header and log output updated to `v1.0.2`.
- README updated: version badge → 1.0.2, added *Non-blocking startup*
  section explaining the threading model.

---

## [1.0.1] - 2026-08-28

### Changed

- README: minor corrections and formatting.

---

## [1.0.0] - 2026-08-28

### Added

- `ppec_auto_enable.py` — IronPython startup script for SharpCap.
  Polls `SharpCap.Mounts.SelectedMount` every 30 s until the mount is
  connected and sidereal tracking, then launches `ppec_worker.py` via
  the project `.venv` CPython interpreter.

- `ppec_worker.py` — CPython worker that activates mount-native PPEC on
  the EQ8-R Pro via EQMOD's low-level motor-controller passthrough:

  ```python
  scope.CommandString(">:q1010000", False)  # query PPEC state
  scope.CommandString(">:W1020000", False)  # enable PPEC
  ```

  Firmware responses:

  | Command | Response | Meaning |
  |---|---|---|
  | `:q1010000` | `=260001\r` | PPEC active |
  | `:q1010000` | `=060001\r` | PPEC inactive |
  | `:W1020000` | `=\r` | Enable accepted |

  The worker polls `EQMOD.Telescope` every 10 s until connected and
  tracking, reads current state, enables PPEC if inactive, and confirms
  with a second query.

- `requirements/requirements.txt` — single dependency: `pywin32>=306`.

### Notes

- No UI automation required: the native `CommandString` passthrough was
  confirmed from EQMOD serial-port log capture (Development Testing Area)
  and validated with direct Python testing.
- EQASCOM is a COM local server; `ppec_worker.py` connects as a second
  independent client alongside SharpCap without conflicts.
- The EQMOD panel does not update its checkbox state when PPEC is enabled
  externally, but clicking Refresh confirms `PPEC is ON`.
