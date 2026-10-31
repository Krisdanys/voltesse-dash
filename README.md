> **Figma technician branch:** See [figma-gui/README.md](figma-gui/README.md) for the authenticated laptop GUI, local setup, and [Figma handoff](figma-gui/FIGMA_HANDOFF.md). The original driver application below is unchanged.

# Voltesse Dash ⚡ v2.0.2

[![Version](https://img.shields.io/badge/version-2.0.2-00F5A0.svg)](https://github.com/r2d2pr/voltesse-dash)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/PyQt-6-green.svg)](https://riverbankcomputing.com/software/pyqt/)
[![CAN](https://img.shields.io/badge/CAN-SocketCAN%20%7C%20virtual-orange.svg)](https://python-can.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A modern, high-contrast automotive digital cockpit instrument cluster and local telemetry logging engine engineered for embedded displays (e.g., Raspberry Pi) and EV powertrains. Built with **Python**, **PyQt6**, **python-can**, and **PostgreSQL**.

---

## What's New in Version 2.0.2 🚀

- 🌐 **Dual Metric & Imperial Unit System**: Seamless runtime switching between **Metric** (`km/h`, `km`, `°C`, `bar`, `Nm`) and **Imperial** (`mph`, `mi`, `°F`, `psi`, `lb-ft`) across all modes via hotkey `U` or CLI flag `--imperial`.
- 🕒 **12-Hour AM/PM Automotive Clock**: High-visibility digital clock in the top HUD ribbon formatted in 12-hour AM/PM (`hh:mm:ss AM/PM`) with live 1-second precision across all modes.

- 🏎️ **Tri-Mode Operating Architecture**: Instant switching between **Race Mode** (CAN bus), **Simulation Mode** (interactive keyboard video-game controls), and **Test Mode** (autonomous mock telemetry).
- ⚙️ **Dynamic Automatic Gear Display (`D1`–`D6`)**: In Auto mode, vehicle speed dynamically drives active gear calculation across 6 EV gear ratios (`D1` to `D6`) displayed on the central capsule, gear status hub, and HUD ribbon.
- 🕹️ **6-Speed Sequential Manual Transmission**: Driver-controlled shifting (`E` for upshift, `C` for downshift) covering gears `1`–`6`, `N`, and `R` in both Race and Simulation modes.
- 💾 **Granular Database Write Access Controls**: Pre-flight write permission verification, runtime logging toggle (`L` key), strict read-only execution mode (`--read-only`), and direct session export to CSV and JSON.
- 🖥️ **Variable Fullscreen Auto-Scaling Engine**: Native launch in borderless fullscreen with dynamic proportional scaling that adapts flawlessly across any aspect ratio and resolution (1024x600 RPi, 720p, 1080p, 1440p, 4K).

---

## Core Features

- **Three Operating Modes**:
  - 🏎️ **Race Mode (Default)**: Direct integration with **CAN Bus** (`SocketCAN` on Linux/RPi, virtual or hardware bus on other platforms). Decodes standard CAN frames for velocity, motor RPM, battery voltage/current/SoC, powertrain thermals, tire pressures/temps, steering angle, warnings, transmission mode, and active gear.
  - 🎮 **Simulation Mode**: Interactive video-game physics simulation mapped to keyboard inputs:
    - **Acceleration**: `W` or `Up Arrow`
    - **Braking & Regen**: `S` or `Down Arrow`
    - **Steering Wheel**: `A` / `Left Arrow` (steer left), `D` / `Right Arrow` (steer right) with self-centering spring dynamics
    - **Sequential Shifting**: `E` (Upshift 1–6), `C` (Downshift 6–1–N–R)
    - **Gear Shift / Cycle**: `G` (PRNDB in Auto, Upshift in Manual)
    - **Drive Mode**: `M` (ECO / DRIVE / SPORT)
  - 🧪 **Test Mode**: Autonomous canned driving cycle simulator pulling dynamic EV metrics from `telemetry_source.py` (restricted to Automatic transmission only).
- **Automatic vs. Sequential Manual Transmission**:
  - Dynamic transmission switching via hotkey `T` supported across **Race Mode** and **Simulation Mode**.
  - **Test Mode Exclusion**: Switching to manual transmission is locked in Test Mode; pressing `T` displays an on-screen warning badge (`⚠️ TEST MODE: AUTO ONLY`) and preserves automatic operation.
  - **Dynamic Automatic Gear Display**:
    - In **Auto Mode**, the active virtual gear is dynamically computed from vehicle velocity across 6 realistic EV gear ratios:
      - `D1`: 0 – 25 km/h
      - `D2`: 25 – 50 km/h
      - `D3`: 50 – 78 km/h
      - `D4`: 78 – 110 km/h
      - `D5`: 110 – 145 km/h
      - `D6`: 145+ km/h
    - Speedometer capsule dynamically reflects the active ratio: `[P] [R] [N] [D3] [B]`.
    - Prominent status hub pill: `AUTO • D3 (GEAR 3)`, `AUTO • PARK [P]`, `AUTO • REGEN [B]`, or `MANUAL • M4 (GEAR 4)`.
    - Top HUD Ribbon: Live `AUTO [D3]` or `MANUAL [M4]` mode badge.
- **Dual Metric & Imperial Unit Architecture**:
  - Global runtime switching via hotkey `U` dynamically transforms all cluster telemetry readouts across Race, Sim, and Test modes:
    - **Speed**: `KM/H` (0–180 scale) ⇄ `MPH` (0–120 scale)
    - **Estimated Range & Trip Odometer**: `km` ⇄ `mi`
    - **Thermal Temperatures (Motor, Inverter, Battery Pack)**: `°C` ⇄ `°F`
    - **4-Wheel Tire Pressure (TPMS)**: `bar` ⇄ `psi`
    - **Dual-Motor Torque Vectoring**: `Nm` ⇄ `lb-ft`
  - Top HUD ribbon features a dedicated `[METRIC]` / `[IMPERIAL]` badge for instantaneous driver awareness.
- **12-Hour AM/PM Precision Cockpit Clock**:
  - Top HUD ribbon clock upgraded to 12-hour AM/PM format with live second tracking, synchronized across all operating modes.
- **Granular Database Write Access & Storage Controls**:
  - **Pre-flight Write Verification**: Verifies directory existence and write permissions before logging.
  - **Runtime Write Toggle (`L` key)**: Drivers can pause and resume database logging on the fly without stopping vehicle telemetry or restarting the dashboard.
  - **Top Ribbon Status Indicator**: Live status badge shows `REC` (active writing), `LOG OFF` (writing paused), or `R/O` (strict read-only).
  - **Strict Read-Only Enforcement (`--read-only`)**: Safe post-race diagnostics without modifying existing trip sessions or records.
  - **Session Data Export**: Export trip sessions directly to CSV or structured JSON via CLI flags (`--export-csv`, `--export-json`, `--export-summary`).
- **Fullscreen & Dynamic Auto-Scaling**:
  - Runs in **fullscreen mode by default** on launch.
  - All dial gauges, cards, fonts, battery arcs, TPMS silhouettes, and HUD ribbons dynamically auto-scale to fit any display resolution (1024x600, 720p, 1080p, 1440p, 4K) without vertical stretching.
- **Distraction-Free Cyber-Mint Cockpit UI**:
  - **Dynamic Radial Speedometer**: Central gauge with digital speed numerals, motor RPM, gear capsule, dual throttle/brake micro-meters, and steering angle readout.
  - **Battery & Range Hero**: High-visibility SoC arc, pack voltage (V), current (A), and estimated range (km).
  - **Bidirectional Power / Regen Bar**: Live kW delivery and regenerative braking recapture indicators.
  - **4-Wheel TPMS Monitoring Pod**: Top-down chassis schematic tracking corner tire pressures and temperatures.
  - **AWD Dynamic Torque Vectoring Pod**: Real-time front and rear motor torque allocation (Nm) with mode bias.
  - **Thermal Diagnostics**: Continuous monitoring for motor, inverter, and battery pack temperatures.
  - **Live Oscilloscope Trace**: Rolling sparkline graph plotting speed and power curves.
- **Asynchronous Telemetry & Batched Logging**:
  - Dedicated `QThread` telemetry sources guarantee zero main GUI thread blocking.
  - PostgreSQL persistence (schema from the SRS, section 3.4) with micro-batched background writes, so database load never blocks the display and SD card writes stay low.
  - Session-based retention keeps the newest N vehicle sessions (`--keep-sessions`).

---

## Project Structure

```
voltesse-dash/
├── db/                        # PostgreSQL schema, sample data, local Docker setup, backup/migration scripts
│   └── README.md              # How to run the database locally and move it to the Raspberry Pi
├── data/
│   └── exports/               # Generated CSV & JSON session dumps (auto-created)
├── src/
│   ├── __init__.py
│   ├── can_bus_source.py      # CAN Bus interface, frame decoders, and synchronized mock transmitter
│   ├── simulation_source.py   # Video-game interactive EV dynamics engine (W/A/S/D, 6-speed manual, D1-D6 auto)
│   ├── telemetry_source.py    # Autonomous EV driving cycle telemetry stream (Test Mode, D1-D6 auto)
│   ├── dashboard_gui.py       # PyQt6 digital cluster interface & auto-scaling widgets
│   └── database.py            # PostgreSQL access: batched writer, sessions, retention, write controls, exports
├── tests/
│   └── test_voltesse.py       # Comprehensive unit and integration test suite (16 tests)
├── main.py                    # Application lifecycle, transmission, and mode controller
├── requirements.txt           # Python dependencies (PyQt6, python-can)
├── AGENTS.md                  # Embedded developer rules, architecture contracts & specifications
└── README.md                  # Project documentation
```

---

## Keyboard Controls & Hotkeys

| Key | Function | Mode Availability |
| :--- | :--- | :--- |
| `1` / `F1` / `Num 1` | Switch to **Race Mode (CAN Bus)** | Global |
| `2` / `F2` / `Num 2` | Switch to **Simulation Mode (Keyboard Game)** | Global |
| `3` / `F3` / `Num 3` | Switch to **Test Mode (Autonomous Mock)** | Global |
| `Tab` | Cycle through Operating Modes (Race ➔ Sim ➔ Test) | Global |
| `T` | **Toggle Transmission (Auto ⮂ Manual)** | **Race & Sim Modes** *(Disabled in Test Mode)* |
| `E` | **Upshift** (`1` ➔ `6` in Manual, or selector in Auto) | Global |
| `C` | **Downshift** (`6` ➔ `1` ➔ `N` ➔ `R` in Manual, or selector in Auto) | Global |
| `G` | Cycle Gear (`P-R-N-D-B` in Auto, Upshift in Manual) | Global |
| `L` | **Toggle Database Logging / Write Access** (`REC` ⮂ `LOG OFF`) | Global |
| `W` / `Up Arrow` | Accelerate (Throttle ramp-up) | Simulation Mode |
| `S` / `Down Arrow` | Brake (Regen & Friction brake) | Simulation Mode |
| `A` / `Left Arrow` | Steer Left | Simulation Mode |
| `D` / `Right Arrow` | Steer Right | Simulation Mode |
| `M` | Cycle Drive Mode (`ECO` ➔ `DRIVE` ➔ `SPORT`) | Global (Race, Sim, Test) |
| `Space` | Pause / Resume telemetry stream | Global |
| `F11` | Toggle Fullscreen / Windowed display | Global |
| `Esc` / `Q` | Graceful application shutdown | Global |

---

## Getting Started

### 1. Prerequisites

- Python 3.10+
- Virtual environment (recommended)

### 2. Installation

```bash
git clone https://github.com/r2d2pr/voltesse-dash.git
cd voltesse-dash

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# or: .venv\Scripts\activate     # Windows

# Install requirements
pip install -r requirements.txt

# Start the local PostgreSQL database (see db/README.md for details)
cd db && cp .env.example .env && docker compose up -d && cd ..
export VOLTESSE_DB_URL=postgresql://voltesse:voltesse@localhost:5432/voltesse_dash
# or (Windows PowerShell): $env:VOLTESSE_DB_URL="postgresql://voltesse:voltesse@localhost:5432/voltesse_dash"
```

No Docker? [db/README.md](db/README.md#without-docker-fallback) shows how to install PostgreSQL directly on macOS, Windows or the Pi. Without any database the dashboard still runs, with logging switched off.

### 3. Launching the Dashboard

```bash
# Launch in default Fullscreen Race Mode (CAN Bus)
python main.py

# Launch in windowed development mode with interactive simulation
python main.py --windowed --mode SIMULATION

# Launch with database logging initially paused (toggle on with key L)
python main.py --no-logging

# Launch in strict read-only database mode (disables session and telemetry writes)
python main.py --read-only

# Launch in Race Mode with mock CAN frame transmitter
python main.py --can-mock

# Launch with custom CAN interface (e.g., Linux SocketCAN)
python main.py --can-interface socketcan --can-channel can0
```

### 4. Database Export & Inspection Tools

You can export session logs directly from the command-line without launching the GUI:

```bash
# Export summary of all trip sessions to CSV
python main.py --export-summary

# Export specific trip session (e.g. Session 1) to CSV
python main.py --export-csv 1

# Export specific trip session to structured JSON
python main.py --export-json 1

# Export from a custom database location
python main.py --db-path data/voltesse_telemetry.db --export-csv 1
```

Generated files are saved directly to `data/exports/`.

#### Command-Line Options

| Flag | Default | Description |
| :--- | :--- | :--- |
| `--mode` | `RACE` | Initial telemetry mode (`RACE`, `SIMULATION`, `TEST`) |
| `--windowed` | `False` | Run in windowed mode (default is fullscreen) |
| `--read-only` | `False` | Open the database in strict read-only mode |
| `--no-logging`| `False` | Launch with database writing paused (toggleable with `L`) |
| `--export-csv` | `None` | Export a specific vehicle session ID to CSV and exit |
| `--export-json`| `None` | Export a specific vehicle session ID to JSON and exit |
| `--export-summary`| `False` | Export summary of all vehicle sessions to CSV and exit |
| `--can-interface` | `None` | CAN driver (`socketcan`, `virtual`, `pcan`, etc.) |
| `--can-channel` | `None` | CAN channel name (e.g., `can0`, `vcan0`) |
| `--can-mock` | `False` | Enable background mock CAN frame broadcaster for bench testing |
| `--interval-ms` | `40` | Telemetry poll interval in milliseconds (40ms = 25 Hz) |
| `--batch-size` | `25` | Number of records to batch before a PostgreSQL commit |
| `--flush-interval`| `1.0` | Max seconds between database batch flushes |
| `--db-url` | `$VOLTESSE_DB_URL` | PostgreSQL connection URL (default `postgresql://voltesse@localhost:5432/voltesse_dash`) |
| `--keep-sessions` | `20` | Keep only the newest N sessions at startup (`0` keeps everything) |

---

## Running Tests

Execute the automated test suite with Python's built-in `unittest`. The database tests need the local PostgreSQL from `db/` to be running (they create and delete their own temporary schemas inside the `voltesse_test` database) and are skipped if it can't be reached:

```bash
export VOLTESSE_TEST_DB_URL=postgresql://voltesse:voltesse@localhost:5432/voltesse_test
python -m unittest discover tests
```

---

## License

MIT License. Designed and engineered for high-performance EV telemetry systems.
