# sharpcap-eqmod-ppec-auto-enable

**SharpCap IronPython startup script** that automatically enables **PPEC**
(Permanent Periodic Error Correction) in **EQMOD/EQASCOM** as soon as the
mount starts sidereal tracking.

The script launches a lightweight CPython worker that connects to
`EQMOD.Telescope` via a second independent ASCOM COM client and sends the
activation command directly to the mount firmware via EQMOD's low-level
motor-controller passthrough (`CommandString` with the `>` prefix).
No UI automation, no extra windows, no pywinauto required.

## Version

Current release: **1.0.2**

## Reference Setup

| Component | Model |
|---|---|
| Mount | Sky-Watcher EQ8R Pro |
| Driver | EQMOD EQASCOM v2.00w |
| Acquisition software | SharpCap Pro |
| Main scope | Celestron C8 + F/6.3 focal reducer |
| Main camera | ZWO ASI2600MC Pro |
| Guide scope | Sky-Watcher 50ED |
| Guide camera | ZWO ASI224MC |

## How It Works

```
SharpCap starts
        |
        +-- ppec_auto_enable.py  (IronPython, inside SharpCap)
                |
                |-- Launch background thread --> returns immediately
                |
                |   [background thread]
                |-- Poll every 30s until SharpCap has a mount connected
                |
                |-- Poll every 30s until mount.Tracking == True
                |
                +--> Launch ppec_worker.py via .venv CPython

ppec_worker.py  (CPython, subprocess)
        |
        |-- Poll every 10s until EQMOD.Telescope is connected + tracking
        |
        |-- Query PPEC state  (:q1010000 via CommandString passthrough)
        |       |-- =260001  --> Already active --> Disconnect --> END OK
        |       +--> =060001 --> Inactive       --> Continue
        |
        +--> Enable PPEC (:W1020000 via CommandString passthrough)
                |
                +--> Confirm :q1010000 --> =260001 --> Disconnect --> END OK
```

### Non-blocking startup

SharpCap executes startup scripts **sequentially** in a single thread.
If a script blocks (e.g. with a polling loop), the next script never runs
until the first one finishes.

`ppec_auto_enable.py` spawns a background daemon thread
(`System.Threading.Thread`, `IsBackground = True`) and returns
immediately, so any subsequent startup scripts (e.g. `log_conditions.py`
from [bme280-observatory](https://github.com/davidglt/bme280-observatory))
execute without delay.

### Why a subprocess?

SharpCap runs startup scripts in IronPython. The `mount.AscomMount` wrapper
exposed by SharpCap does not allow sending raw `CommandString` calls through
EQMOD's motor-controller passthrough. The worker is a second independent
CPython process that connects to `EQMOD.Telescope` as an additional ASCOM
client — EQASCOM is a COM local server that supports multiple simultaneous
clients.

### EQMOD Motor-Controller Passthrough

EQMOD exposes a direct passthrough to the mount firmware via
`ASCOM CommandString` with a `>` prefix and **no trailing `#`**:

```python
scope.CommandString(">:q1010000", False)  # Query PPEC state
scope.CommandString(">:W1020000", False)  # Enable PPEC
scope.CommandString(">:W1030000", False)  # Disable PPEC
```

Firmware responses:

| Command | Response | Meaning |
|---|---|---|
| `:q1010000` | `=260001\r` | PPEC active |
| `:q1010000` | `=060001\r` | PPEC inactive |
| `:W1020000` | `=\r` | Enable command accepted |
| `:W1030000` | `=\r` | Disable command accepted |

These commands were captured from EQMOD's internal serial-port log while
operating the Development Testing Area panel.

**Official EQASCOM CommandString reference:**
[EQASCOM Supported ASCOM Properties and Methods (PDF)](https://eq-mod.sourceforge.net/docs/EQASCOM_compliancy.pdf)

## Requirements

- Windows
- [ASCOM Platform](https://ascom-standards.org/) installed
- [EQASCOM](https://eq-mod.sourceforge.net/eqascom.html) installed and configured
- **SharpCap Pro** (startup scripts require the Pro licence)
- **A PPEC curve already recorded on the mount** — without it the firmware
  will ignore the enable command
- **Python 3.x** (for the `.venv`)
- **pywin32** — the only Python package required

## Installation

1. Clone or download this repository:

```bash
git clone https://github.com/davidglt/sharpcap-eqmod-ppec-auto-enable.git
cd sharpcap-eqmod-ppec-auto-enable
```

2. Create the virtual environment and install dependencies:

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements\requirements.txt
```

3. In SharpCap, open **File -> SharpCap Settings -> Scripting**.
4. Under **"Run these Python scripts when SharpCap starts"**, add the full
   path to `ppec_auto_enable.py`.
5. Restart SharpCap. The script runs automatically on every startup.

## Configuration

Edit the constants at the top of each script:

### ppec_auto_enable.py

| Variable | Default | Description |
|---|---|---|
| `CHECK_INTERVAL` | `30` | Seconds between SharpCap mount polling checks |

### ppec_worker.py

| Variable | Default | Description |
|---|---|---|
| `CONNECT_INTERVAL` | `10` | Seconds between EQMOD connection polling checks |

## Log Destinations

| Destination | How to view |
|---|---|
| SharpCap scripting console | `Scripting -> Show Console` or `Alt+F11` |
| SharpCap main log | `File -> Show Log` |
| Worker log file | `ppec_worker.log` in the project folder |

## License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.

You are free to use, study, modify and redistribute this software, provided
that all distributed versions and modifications remain under GPL v3.
See [LICENSE.txt](LICENSE.txt) for the full license text.
