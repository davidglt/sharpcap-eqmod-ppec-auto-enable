# EQASCOM CommandString Interface — Reference

> **Source:** Official EQASCOM documentation  
> [EQASCOM_compliancy.pdf](https://eq-mod.sourceforge.net/docs/EQASCOM_compliancy.pdf)  
> EQMOD project — <https://eq-mod.sourceforge.net/>

---

## Overview

The ASCOM `CommandString` method is the mechanism by which EQASCOM exposes
additional proprietary properties and functions beyond the standard ASCOM
telescope interface.

These commands are **specific to EQASCOM** and are not part of the ASCOM
standard. They are unlikely to be found on other ASCOM drivers.

---

## Send Low Level Comms (Motor Controller Passthrough)

The most relevant command for this project is the **low-level comms
passthrough**, which forwards raw firmware commands directly to the mount
motor controller:

| Command String | Response | Description |
|---|---|---|
| `>XX..XXX` | `YYYYY` | Send raw low-level command to mount motor controller |

**Rules:**
- The passthrough prefix is **`>`** (greater-than sign).
- `XX..XXX` are the raw low-level comms characters to send (e.g. `>:j1`
  will send `:j1` to the mount, with LF+CR appended automatically).
- The mount motor controller response is returned as-is.

**Usage in Python (win32com):**

```python
# Correct: '>' prefix, no trailing '#', raw_string=False
response = scope.CommandString(">:q1010000", False)

# Wrong: EQASCOM high-level command format (uses ':' and '#')
response = scope.CommandString(":PECSTA#", False)
```

> **Important:** Do NOT append `#` when using the `>` passthrough prefix.
> The `#` terminator is only used for EQASCOM high-level CommandString
> commands (see table below), not for firmware passthroughs.

---

## EQASCOM High-Level CommandString Commands

These are EQASCOM-level commands (not firmware passthroughs). They use the
`:COMMAND#` format and are handled internally by the EQASCOM driver:

### PEC / PPEC

| Function | Command String | Response |
|---|---|---|
| Disable PEC | `:PECENA,0#` | — |
| Enable PEC | `:PECENA,1#` | — |
| Get PEC State | `:PECSTA#` | `0#` (disabled) / `1#` (enabled) |
| Get Worm Tooth Count | `:PECWTC#` | `worm_tooth_count#` |
| Get Worm Position | `:PECIDX#` | `worm_position#` |
| Get PEC Info | `:PECINFO#` | `row_count,max_position#` |
| Set Table Row | `:PECSET,row_index,worm_position,pe#` | `1#` (success) / `0#` (failure) |
| Get Table Row | `:PECSET,row_index#` | `1,worm_position,pe#` / `0#` |
| Load PEC Table | `:PECLOAD,full_file_name#` | `1#` / `0#` |
| Save PEC Table | `:PECSAVE,full_file_name#` | `1#` / `0#` |
| Get PEC Gain | `:PECGAIN` | `gain#` |
| Set PEC Gain | `:PECGAIN,gain#` | `1#` / `0#` |
| Get PEC Phase | `:PECPHASE` | `phase#` |
| Set PEC Phase | `:PECPHASE,phase#` | `1#` / `0#` |

### Mount / Driver Info

| Function | Command String | Response |
|---|---|---|
| Get Mount Version | `:MOUNTVER#` | `MountVersionString` |
| Get EQASCOM Version | `:DRIVERVER#` | EQASCOM version string |
| Get eqcontrl.dll version | `:DLLVER#` | DLL version string |

### Park / Unpark

| Function | Command String | Response |
|---|---|---|
| Park | `:PARK,parkmode#` | `1#` (parked/parking) / `0#` (unparked) |
| Unpark | `:UNPARK,unparkmode#` | `1#` / `0#` |

`parkmode` values: `0` = current EQASCOM setting, `1` = Home, `2` = current
position, `3`–`7` = user positions 1–5.

### Encoders

| Function | Command String | Response |
|---|---|---|
| Get RA encoder | `:RA_ENC#` | Encoder position |
| Get DEC encoder | `:DEC_ENC#` | Encoder position |

### Guide Rates

| Function | Command String | Response |
|---|---|---|
| Get ST4 RA Guide Rate | `:ST4_RARATE#` | `ST4GuideRate#` |
| Set ST4 RA Guide Rate | `:ST4_RARATE,ST4GuideRate#` | `1#` / `0#` |
| Get ST4 DEC Guide Rate | `:ST4_DECRATE#` | `ST4GuideRate#` |
| Set ST4 DEC Guide Rate | `:ST4_DECRATE,ST4GuideRate#` | `1#` / `0#` |
| Get PulseGuide RA Rate | `:PG_RARATE#` | `PGGuideRate#` |
| Set PulseGuide RA Rate | `:PG_RARATE,PGGuideRate#` | `1#` / `0#` |
| Get PulseGuide DEC Rate | `:PG_DECRATE#` | `PGGuideRate#` |
| Set PulseGuide DEC Rate | `:PG_DECRATE,PGGuideRate#` | `1#` / `0#` |

Valid `ST4GuideRate` values: `0.25`, `0.5`, `0.75`, `1.00`  
Valid `PGGuideRate` values: `0.1` – `0.9` (in 0.1 steps)

### Alignment

| Function | Command String | Response |
|---|---|---|
| Get Alignment mode | `:ALIGN_MODE#` | `1#` (append) / `0#` (dialog) |
| Set Alignment mode | `:ALIGN_MODE,0#` / `:ALIGN_MODE,1#` | `1#` (success) |
| Clear sync | `:ALIGN_CLEAR_SYNC#` | `1#` / `0#` |
| Clear points | `:ALIGN_CLEAR_POINTS#` | `1#` / `0#` |
| Get sync limit status | `:ALIGN_SYNC_LIMIT#` | `1#` (active) / `0#` |
| Set sync limit status | `:ALIGN_SYNC_LIMIT,0#` / `:ALIGN_SYNC_LIMIT,1#` | `1#` |
| Get Flipped Goto status | `:FLIP_GOTO#` | `1#` (active) / `0#` |
| Set Flipped Goto status | `:FLIP_GOTO,0#` / `:FLIP_GOTO,1#` | `1#` |

### SNAP Ports

| Function | Command String | Response |
|---|---|---|
| Set SNAP Port 1 | `:SNAP1,0#` / `:SNAP1,1#` | `0#` or `1#` (mirrors requested state) |
| Set SNAP Port 2 | `:SNAP2,0#` / `:SNAP2,1#` | `0#` or `1#` |

---

## Formatting Rules

- All high-level commands begin with `:` and end with `#`.
- Parameters are comma-separated, ASCII-encoded integers.
- **Avoid locale grouping** — send `50132`, not `50,132`.
- For the `>` passthrough, no `#` terminator is used; LF+CR is appended
  automatically by EQASCOM.

---

## How This Project Uses the Passthrough

`ppec_worker.py` uses the `>` passthrough to query and control the
EQ8-R Pro mount-native PPEC firmware feature:

```python
# Query PPEC state (firmware level)
response = scope.CommandString(">:q1010000", False)
# Returns: "=260001\r" (active) or "=060001\r" (inactive)

# Enable PPEC (firmware level)
response = scope.CommandString(">:W1020000", False)
# Returns: "=\r" (command accepted)

# Disable PPEC (firmware level)
response = scope.CommandString(">:W1030000", False)
# Returns: "=\r" (command accepted)
```

These firmware commands (`:q1010000`, `:W1020000`, `:W1030000`) were
identified by capturing EQMOD's internal serial-port log while operating the
**Development Testing Area** panel in the EQMOD UI, and validated with direct
Python testing against the EQ8-R Pro.
