"""
iaqualink Heat Pump Diagnostic & State Reader
=============================================
Compatible with: iaqualink==0.6.0, Python 3.12

Dependencies:
    pip install iaqualink==0.6.0

GitHub Actions secrets required:
    IQUALINK_USER  - your iAqualink account email
    IQUALINK_PASS  - your iAqualink account password
    IQUALINK_SERIAL (optional) - system serial; auto-selects first system if omitted

Usage:
    python iaqualink_heatpump_diagnostic.py
"""

import asyncio
import json
import os
import re
import sys
from typing import Any

from iaqualink import AqualinkClient


# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

USERNAME      = os.environ.get("IQUALINK_USER", "")
PASSWORD      = os.environ.get("IQUALINK_PASS", "")
TARGET_SERIAL = os.environ.get("IQUALINK_SERIAL", "")  # optional

# Any device key whose name matches this pattern gets flagged as a
# potential heat-pump data point in the diagnostic output.
HEAT_PUMP_PATTERNS = re.compile(
    r"(heat_pump|heatpump|hp_|dual_heat|dualheater|solar_heat"
    r"|pool_heat|spa_heat|heater_mode|heat_mode|heating|booster)",
    re.IGNORECASE,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _flatten(obj: Any, prefix: str = "") -> dict:
    """Recursively flatten a nested dict/list into dot-notation key→value pairs."""
    items: dict = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            full_key = f"{prefix}.{k}" if prefix else k
            items.update(_flatten(v, full_key))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            items.update(_flatten(v, f"{prefix}[{i}]"))
    else:
        items[prefix] = obj
    return items


def _highlight_matches(flat: dict) -> list[tuple[str, Any]]:
    return [(k, v) for k, v in flat.items() if HEAT_PUMP_PATTERNS.search(k)]


def _print_section(title: str) -> None:
    print(f"\n{'═' * 70}")
    print(f"  {title}")
    print("═" * 70)


# ──────────────────────────────────────────────────────────────────────────────
# Diagnostic
# ──────────────────────────────────────────────────────────────────────────────

async def run_diagnostic() -> None:
    if not USERNAME or not PASSWORD:
        print(
            "ERROR: credentials not found.\n"
            "Set IQUALINK_USER and IQUALINK_PASS environment variables / GitHub secrets."
        )
        sys.exit(1)

    _print_section("1 / 4  -  Connecting")
    async with AqualinkClient(USERNAME, PASSWORD) as client:
        print("  + Logged in")

        systems = await client.get_systems()
        if not systems:
            print("  ERROR: No systems found on this account.")
            return

        system = None
        if TARGET_SERIAL:
            system = systems.get(TARGET_SERIAL)
            if system is None:
                print(f"  WARNING: serial '{TARGET_SERIAL}' not found, using first system.")

        if system is None:
            system = next(iter(systems.values()))

        print(f"  + System: {system.serial} / {system.name!r}")

        # ── 2. All devices ─────────────────────────────────────────────────
        _print_section("2 / 4  -  All devices")
        devices = await system.get_devices()
        print(f"  {len(devices)} device(s) found:\n")

        all_device_data: dict = {}
        for name, dev in devices.items():
            state_val = getattr(dev, "state", "?")
            label     = getattr(dev, "label", name)
            dev_type  = type(dev).__name__
            marker    = "  [HP]" if HEAT_PUMP_PATTERNS.search(name) else "     "
            print(f"{marker}  [{dev_type:30s}]  {name:20s}  state={str(state_val):10}  label={label!r}")

            all_device_data[name] = {
                k: str(getattr(dev, k))
                for k in dir(dev)
                if not k.startswith("_") and not callable(getattr(dev, k, None))
            }

        # ── 3. Heat-pump candidates ─────────────────────────────────────────
        _print_section("3 / 4  -  Heat-pump candidate fields")

        flat_devices = _flatten(all_device_data)
        matches = _highlight_matches(flat_devices)

        if matches:
            print()
            for k, v in matches:
                print(f"  [HP]  {k:60s} = {v!r}")
        else:
            print(
                "\n  No heat-pump keys found in the device list.\n"
                "\n  This is normal for dual-heat systems. The heat pump is usually\n"
                "  encoded inside pool_heat_mode / spa_heat_mode as an integer:\n"
                "    0 = Off  |  1 = Gas heater  |  2 = Solar  |  3 = Heat pump\n"
                "\n  Check the full dump (iaqualink_full_dump.json) for these fields."
            )

        # Print pool/spa heat mode directly if present
        print()
        for key in ("pool_heat_mode", "spa_heat_mode"):
            dev = devices.get(key)
            if dev is not None:
                try:
                    mode = int(dev.state)
                    label = {0: "Off", 1: "Gas heater", 2: "Solar", 3: "Heat pump"}.get(mode, f"Unknown ({mode})")
                except (TypeError, ValueError):
                    label = "(could not parse)"
                print(f"  {key} = {dev.state!r}  ->  {label}")

        # ── 4. Save full dump ───────────────────────────────────────────────
        _print_section("4 / 4  -  Saving full dump")
        dump_path = "iaqualink_full_dump.json"
        with open(dump_path, "w") as f:
            json.dump(all_device_data, f, indent=2, default=str)
        print(f"\n  Saved -> {dump_path}")
        print("  Share this file if you need further help locating the heat-pump key.\n")


# ──────────────────────────────────────────────────────────────────────────────
# HeatPumpReader
# ──────────────────────────────────────────────────────────────────────────────

class HeatPumpReader:
    """
    Reads heat-pump state from an iAqualink dual-heat system.

    Dual-heat systems expose the heat pump in one of two ways:

      MODE A - pool_heat_mode / spa_heat_mode  (most common)
        Integer device in the device list:
          0 = Off  |  1 = Gas  |  2 = Solar  |  3 = Heat pump
        Pass: mode="pool_heat_mode" or mode="spa_heat_mode"

      MODE B - named device key found by the diagnostic
        A dedicated boolean/integer device (e.g. "dual_heat", "hp_state").
        Pass: mode="device_key" and device_key="<key_from_diagnostic>"

    Example:
        async with HeatPumpReader(USERNAME, PASSWORD, mode="pool_heat_mode") as reader:
            state = await reader.get_heat_pump_state()
            print(state)
        # {'is_on': True, 'raw_value': '3', 'source': 'pool_heat_mode',
        #  'heat_mode_meaning': 'Heat pump'}
    """

    HEAT_MODE_MAP = {0: "Off", 1: "Gas heater", 2: "Solar", 3: "Heat pump"}

    def __init__(
        self,
        username: str,
        password: str,
        serial: str = "",
        mode: str = "pool_heat_mode",
        device_key: str = "",
        heat_pump_mode_value: int = 3,
    ):
        self.username = username
        self.password = password
        self.serial = serial
        self.mode = mode
        self.device_key = device_key
        self.heat_pump_mode_value = heat_pump_mode_value
        self._client: AqualinkClient | None = None
        self._system = None

    async def __aenter__(self):
        self._client = AqualinkClient(self.username, self.password)
        await self._client.__aenter__()
        systems = await self._client.get_systems()
        if self.serial:
            self._system = systems.get(self.serial)
        if self._system is None:
            self._system = next(iter(systems.values()))
        print(f"Connected -> {self._system.serial} / {self._system.name!r}")
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.__aexit__(*args)

    async def get_heat_pump_state(self) -> dict:
        if self._system is None:
            raise RuntimeError("Use 'async with HeatPumpReader(...) as reader:'")

        devices = await self._system.get_devices()

        if self.mode in ("pool_heat_mode", "spa_heat_mode"):
            dev = devices.get(self.mode)
            if dev is None:
                raise KeyError(
                    f"Device '{self.mode}' not found. "
                    "Run the diagnostic to confirm the correct key name."
                )
            raw = dev.state
            try:
                raw_int = int(raw)
            except (TypeError, ValueError):
                raw_int = -1
            return {
                "is_on": raw_int == self.heat_pump_mode_value,
                "raw_value": raw,
                "source": self.mode,
                "heat_mode_meaning": self.HEAT_MODE_MAP.get(raw_int, f"Unknown ({raw_int})"),
            }

        elif self.mode == "device_key":
            if not self.device_key:
                raise ValueError("Provide device_key= when using mode='device_key'")
            dev = devices.get(self.device_key)
            if dev is None:
                raise KeyError(f"Device '{self.device_key}' not found.")
            raw = dev.state
            return {
                "is_on": raw not in (None, 0, "0", False, "off", "Off", "OFF"),
                "raw_value": raw,
                "source": self.device_key,
            }

        raise ValueError(f"Unknown mode: {self.mode!r}. Use 'pool_heat_mode', 'spa_heat_mode', or 'device_key'.")

    async def poll(self, interval_seconds: int = 30) -> None:
        import datetime
        print(f"Polling every {interval_seconds}s - Ctrl-C to stop.\n")
        while True:
            try:
                state  = await self.get_heat_pump_state()
                ts     = datetime.datetime.now().strftime("%H:%M:%S")
                status = "ON " if state["is_on"] else "OFF"
                extra  = state.get("heat_mode_meaning", "")
                print(f"[{ts}]  Heat pump: {status}   raw={state['raw_value']!r}  {extra}")
            except Exception as exc:
                print(f"  ERROR: {exc}")
            await asyncio.sleep(interval_seconds)


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

async def main() -> None:
    # STEP 1 - run the diagnostic to identify the correct key for your system
    await run_diagnostic()

    # STEP 2 - once confirmed, use HeatPumpReader. Uncomment one of:

    # Pool heat pump (most common):
    # async with HeatPumpReader(USERNAME, PASSWORD, mode="pool_heat_mode") as reader:
    #     state = await reader.get_heat_pump_state()
    #     print(state)

    # Spa heat pump:
    # async with HeatPumpReader(USERNAME, PASSWORD, mode="spa_heat_mode") as reader:
    #     state = await reader.get_heat_pump_state()
    #     print(state)

    # Dedicated device key from diagnostic (e.g. "dual_heat"):
    # async with HeatPumpReader(USERNAME, PASSWORD, mode="device_key", device_key="dual_heat") as reader:
    #     state = await reader.get_heat_pump_state()
    #     print(state)

    # Live polling:
    # async with HeatPumpReader(USERNAME, PASSWORD, mode="pool_heat_mode") as reader:
    #     await reader.poll(interval_seconds=30)


if __name__ == "__main__":
    asyncio.run(main())
