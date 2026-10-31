"""Deterministic, SIMULATED vehicle telemetry for a presentation demo.

No database, backend, or CAN hardware is used. None of these values are real
Voltesse vehicle measurements, engineering models, or approved safety limits.
"""

import math

SESSIONS = [
    {"id": "#14", "date": "Sep 27, 2026", "duration": "18:42", "max_temp": 97},
    {"id": "#13", "date": "Sep 20, 2026", "duration": "22:10", "max_temp": 91},
    {"id": "#12", "date": "Sep 13, 2026", "duration": "15:05", "max_temp": 88},
    {"id": "#11", "date": "Sep 6, 2026", "duration": "20:31", "max_temp": 93},
]

EFFICIENCY_OFFSETS = {"#14": 0, "#13": 8, "#12": -6, "#11": 12}
POWER_OFFSETS = {"#14": 0, "#13": -450, "#12": -800, "#11": 250}
BATTERY_RATES = {"#14": 1.6, "#13": 1.8, "#12": 1.4, "#11": 2.0}


def live_metrics(t):
    """Return simulated speed, RPM, remaining battery, temperature at time t."""
    speed = round(max(0, 45 + 22 * math.sin(t / 14)), 1)
    rpm = int(1400 + speed * 58)
    battery = round(90 - t * 0.08, 1)
    temperature = round(38 + t * 0.25 + 3 * math.sin(t / 8), 1)
    return {"speed": speed, "rpm": rpm, "battery": battery, "temperature": temperature}


def live_temperature_history(t):
    """Show up to the last 60 seconds of the same simulated temperature data."""
    times = list(range(max(0, t - 60), t + 1))
    temperatures = [live_metrics(x)["temperature"] for x in times]
    return times, temperatures


def diagnostics_data(session=None):
    """Return all five chart datasets, with adjustments by historical session."""
    session_id = session["id"] if session else None
    efficiency_offset = EFFICIENCY_OFFSETS.get(session_id, 0)
    power_offset = POWER_OFFSETS.get(session_id, 0)
    battery_rate = BATTERY_RATES.get(session_id, 1.6)

    speeds = list(range(10, 111, 5))
    efficiency = [
        round(135 + 0.055 * (speed - 60) ** 2 + efficiency_offset, 1)
        for speed in speeds
    ]

    motor_temps = list(range(30, 96, 5))
    power_draws = [
        3500 + 135 * (temp - 30) + ((i % 5) - 2) * 170 + power_offset
        for i, temp in enumerate(motor_temps)
    ]
    trend_power = [3500 + 135 * (temp - 30) + power_offset for temp in motor_temps]

    distances = [round(i * 0.5, 1) for i in range(21)]
    battery_levels = [round(90 - battery_rate * d, 1) for d in distances]

    motor_rpms = list(range(2000, 8001, 400))
    power_values = [
        round(2500 + 1.7 * (rpm - 2000) + ((i % 4) - 1.5) * 200 + power_offset)
        for i, rpm in enumerate(motor_rpms)
    ]
    trend_values = [2500 + 1.7 * (rpm - 2000) + power_offset for rpm in motor_rpms]

    if session:
        minutes, seconds = map(int, session["duration"].split(":"))
        duration_minutes = minutes + seconds / 60
        peak_temp = session["max_temp"]
    else:
        duration_minutes = 15
        peak_temp = 57

    time_minutes = [round(duration_minutes * i / 30, 2) for i in range(31)]
    temp_rise = [
        round(32 + (peak_temp - 32) * (1 - 0.75 ** (i / 2)) / (1 - 0.75 ** 15), 1)
        for i in range(31)
    ]

    return {
        "speeds": speeds, "efficiency": efficiency,
        "motor_temps": motor_temps, "power_draws": power_draws,
        "trend_power": trend_power, "distances": distances,
        "battery_levels": battery_levels, "motor_rpms": motor_rpms,
        "power_values": power_values, "trend_values": trend_values,
        "time_minutes": time_minutes, "temp_rise": temp_rise,
        "peak_temp": peak_temp,
    }
