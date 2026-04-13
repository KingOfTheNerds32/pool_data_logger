"""
iaqualink Heat Pump Diagnostic & State Reader
=============================================
Compatible with: iaqualink==0.6.0, Python 3.12

Usage:
    python iaqualink_heatpump_diagnostic.py

Set your credentials via environment variables (or GitHub Actions secrets):
    export IQUALINK_USER="your@email.com"
    export IQUALINK_PASS="yourpassword"
    export IQUALINK_SERIAL="your_serial_number"  # optional, auto-detected if omitted

What this script does:
    1. Connects to iAqualink and dumps ALL raw API data across every known endpoint
    2. Searches every response for heat-pump / dual-heat related keys
    3. Prints a clear summary of where the heat pump state lives
    4. Demonstrates ongoing state polling once the correct key is found
"""

import asyncio
import json
import os
import re
import sys
from typing import Any

import aiohttp
from iaqualink.client import AqualinkClient
from iaqualink.session import AqualinkSession


# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

USERNAME = os.environ.get("IQUALINK_USER", "")
PASSWORD = os.environ.get("IQUALINK_PASS", "")
TARGET_SERIAL = os.environ.get("IQUALINK_SERIAL", "")  # leave blank = first system

# Keys that suggest heat-pump / dual-heat / solar involvement.
# The diagnostic will flag any response field whose name matches any of these.
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


def _print_section(title: str) -> None:
    print(f"\n{'═' * 70}")
    print(f"  {title}")
    print("═" * 70)


def _highlight_matches(flat: dict) -> list[tuple[str, Any]]:
    """Return (key, value) pairs whose key matches a heat-pump pattern."""
    return [(k, v) for k, v in flat.items() if HEAT_PUMP_PATTERNS.search(k)]


# ──────────────────────────────────────────────────────────────────────────────
# Raw API helpers (reach past the high-level client when needed)
# ──────────────────────────────────────────────────────────────────────────────

async def _raw_get(session: AqualinkSession, path: str, params: dict | None = None) -> Any:
    """
    Fire a raw authenticated GET against the iAqualink base URL.
    Returns parsed JSON or None on failure.
    """
    try:
        resp = await session._session.get(
            f"{session.base_url}{path}",
            params=params,
            headers=session._headers,
        )
        text = await resp.text()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"_raw_text": text}
    except Exception as exc:
        return {"_error": str(exc)}


async def _dump_extra_endpoints(session: AqualinkSession, serial: str) -> dict[str, Any]:
    """
    Query every known iAqualink endpoint that might expose heat-pump data.
    Returns a mapping of endpoint → parsed response.
    """
    # The two major API bases used by the library across versions
    results: dict[str, Any] = {}

    extra_paths = [
        # Newer zodiac-io API
        f"/devices/{serial}/properties",
        f"/devices/{serial}/capabilities",
        f"/systems/{serial}",
        f"/systems/{serial}/equipment",
        # Older iaqualink.net paths (some installs still use these)
        f"/iphone/home.aspx",
        f"/iphone/get_devices.aspx",
        f"/iphone/pool_status.aspx",
    ]

    for path in extra_paths:
        data = await _raw_get(session, path, params={"serial": serial})
        results[path] = data

    return results


# ──────────────────────────────────────────────────────────────────────────────
# Main diagnostic
# ──────────────────────────────────────────────────────────────────────────────

async def run_diagnostic() -> None:
    if not USERNAME or not PASSWORD:
        print(
            "ERROR: Set IQUALINK_USER and IQUALINK_PASS environment variables.\n"
            "  export IQUALINK_USER='your@email.com'\n"
            "  export IQUALINK_PASS='yourpassword'"
        )
        sys.exit(1)

    _print_section("1 / 5  –  Connecting to iAqualink")
    async with aiohttp.ClientSession() as http_session:
        client = AqualinkClient(http_session)
        await client.login(USERNAME, PASSWORD)
        print("  ✓ Logged in")

        # ── Pick the target system ──────────────────────────────────────────
        systems = await client.get_systems()
        if not systems:
            print("  ERROR: No iAqualink systems found on this account.")
            return

        system = None
        if TARGET_SERIAL:
            system = systems.get(TARGET_SERIAL)
            if system is None:
                print(f"  WARNING: Serial '{TARGET_SERIAL}' not found. Falling back to first system.")

        if system is None:
            system = next(iter(systems.values()))

        print(f"  ✓ Using system: {system.serial} / {system.name!r}")

        # ── 2. Standard devices ────────────────────────────────────────────
        _print_section("2 / 5  –  Standard device list (get_devices)")
        devices = await system.get_devices()
        print(f"  Found {len(devices)} devices:\n")
        for name, dev in devices.items():
            state_val = getattr(dev, "state", "?")
            label     = getattr(dev, "label", name)
            dev_type  = type(dev).__name__
            marker    = "  🔆" if HEAT_PUMP_PATTERNS.search(name) else "    "
            print(f"{marker}  [{dev_type:30s}]  {name:20s}  state={state_val!r:10}  label={label!r}")

        # ── 3. Raw full JSON from system ───────────────────────────────────
        _print_section("3 / 5  –  Raw system JSON (full flattened dump)")
        raw_data: dict[str, Any] = {}

        # The internal session hangs off the system
        internal_session: AqualinkSession = system._session  # type: ignore[attr-defined]
        serial: str = system.serial

        # Grab whatever the high-level library last cached / fetches
        try:
            home_data = await internal_session.get_home(serial)
            raw_data["get_home"] = home_data
        except Exception as exc:
            raw_data["get_home"] = {"_error": str(exc)}

        flat_home = _flatten(raw_data.get("get_home", {}))
        matches_home = _highlight_matches(flat_home)

        print("\n  All keys from get_home():\n")
        for k, v in sorted(flat_home.items()):
            marker = "  🔆" if HEAT_PUMP_PATTERNS.search(k) else "    "
            print(f"{marker}  {k:60s} = {v!r}")

        # ── 4. Extra endpoints ─────────────────────────────────────────────
        _print_section("4 / 5  –  Extra endpoint sweep")
        extra_results = await _dump_extra_endpoints(internal_session, serial)

        all_matches: dict[str, list[tuple[str, Any]]] = {}
        for endpoint, data in extra_results.items():
            flat = _flatten(data)
            m = _highlight_matches(flat)
            if m:
                all_matches[endpoint] = m

            error = data.get("_error") if isinstance(data, dict) else None
            status = "error" if error else f"{len(flat)} keys"
            print(f"  {endpoint:50s} → {status}")

        # ── 5. Heat-pump summary ───────────────────────────────────────────
        _print_section("5 / 5  –  Heat-pump candidate fields (SUMMARY)")

        if not matches_home and not all_matches:
            print(
                "\n  ⚠  No heat-pump related keys found in ANY endpoint.\n"
                "  This usually means one of:\n"
                "    a) The system reports the heat pump via a non-standard key (see full dump above)\n"
                "    b) The heat pump is connected to an iLink/RS-485 board — check aux_B1..B8\n"
                "    c) The heat pump state is encoded inside pool_heat_mode / spa_heat_mode value\n"
                "       (3 = heat pump, 1 = gas heater, 2 = solar, 0 = off)\n"
            )
        else:
            print("\n  Flagged fields from get_home():\n")
            for k, v in matches_home:
                print(f"    🔆  {k:60s} = {v!r}")

            for endpoint, hits in all_matches.items():
                print(f"\n  Flagged fields from {endpoint}:\n")
                for k, v in hits:
                    print(f"    🔆  {k:60s} = {v!r}")

        # ── Save full dump to file ─────────────────────────────────────────
        dump_path = "iaqualink_full_dump.json"
        with open(dump_path, "w") as f:
            all_data = {
                "get_home": raw_data.get("get_home", {}),
                "extra_endpoints": extra_results,
                "devices": {
                    name: {
                        "type": type(dev).__name__,
                        "state": str(getattr(dev, "state", None)),
                        "label": getattr(dev, "label", None),
                    }
                    for name, dev in devices.items()
                },
            }
            json.dump(all_data, f, indent=2, default=str)

        print(f"\n  ✓ Full raw dump saved → {dump_path}")
        print("    Share this file if you need further help pinpointing the key.\n")


# ──────────────────────────────────────────────────────────────────────────────
# HeatPumpReader  –  use this once you know the correct key
# ──────────────────────────────────────────────────────────────────────────────

class HeatPumpReader:
    """
    Reads heat-pump state from an iAqualink system.

    Dual-heat systems most commonly expose the heat pump in one of three ways:

      MODE A – pool_heat_mode / spa_heat_mode
        The heater mode integer encodes which heat source is active:
          0 = Off, 1 = Gas heater, 2 = Solar, 3 = Heat pump
        → Pass body="pool" or body="spa"

      MODE B – dedicated home-data key (e.g. "dual_heat", "hp_state")
        A separate boolean/integer field in the get_home response.
        → Pass home_key="<the_key_you_found>"

      MODE C – aux relay (less common but possible with some iLink boards)
        → Just use the standard devices dict directly.

    Run the diagnostic first to determine which mode applies to your install.
    """

    def __init__(
        self,
        username: str,
        password: str,
        serial: str = "",
        mode: str = "pool_heat_mode",   # "pool_heat_mode" | "spa_heat_mode" | "home_key"
        home_key: str = "",              # only for mode="home_key"
        heat_pump_mode_value: int = 3,   # integer that means "heat pump is selected"
    ):
        self.username = username
        self.password = password
        self.serial = serial
        self.mode = mode
        self.home_key = home_key
        self.heat_pump_mode_value = heat_pump_mode_value

        self._client: AqualinkClient | None = None
        self._system = None
        self._http: aiohttp.ClientSession | None = None

    async def connect(self) -> None:
        self._http = aiohttp.ClientSession()
        self._client = AqualinkClient(self._http)
        await self._client.login(self.username, self.password)

        systems = await self._client.get_systems()
        if self.serial:
            self._system = systems.get(self.serial)
        if self._system is None:
            self._system = next(iter(systems.values()))

        print(f"Connected → {self._system.serial} / {self._system.name!r}")

    async def close(self) -> None:
        if self._http:
            await self._http.close()

    async def get_heat_pump_state(self) -> dict:
        """
        Returns a dict with:
          is_on      – bool: is the heat pump currently active?
          raw_value  – the raw API value for your own logic
          source     – which field/mode was read
        """
        if self._system is None:
            raise RuntimeError("Call connect() first.")

        session: AqualinkSession = self._system._session  # type: ignore[attr-defined]
        home_data: dict = await session.get_home(self._system.serial)
        flat = _flatten(home_data)

        if self.mode in ("pool_heat_mode", "spa_heat_mode"):
            raw = flat.get(self.mode)
            if raw is None:
                # Try nested path variants
                for k, v in flat.items():
                    if k.endswith(self.mode):
                        raw = v
                        break
            try:
                raw_int = int(raw)
            except (TypeError, ValueError):
                raw_int = -1
            return {
                "is_on": raw_int == self.heat_pump_mode_value,
                "raw_value": raw,
                "source": self.mode,
                "heat_mode_meaning": {
                    0: "Off",
                    1: "Gas heater",
                    2: "Solar",
                    3: "Heat pump",
                }.get(raw_int, f"Unknown ({raw_int})"),
            }

        elif self.mode == "home_key":
            if not self.home_key:
                raise ValueError("Provide home_key= when using mode='home_key'")
            raw = flat.get(self.home_key)
            return {
                "is_on": raw not in (None, 0, "0", False, "off", "Off", "OFF"),
                "raw_value": raw,
                "source": self.home_key,
            }

        else:
            raise ValueError(f"Unknown mode: {self.mode!r}. Use 'pool_heat_mode', 'spa_heat_mode', or 'home_key'.")

    async def poll(self, interval_seconds: int = 30) -> None:
        """Continuously poll and print heat pump state."""
        import datetime
        print(f"Polling every {interval_seconds}s. Ctrl-C to stop.\n")
        while True:
            try:
                state = await self.get_heat_pump_state()
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                status = "🟢 ON " if state["is_on"] else "⚫ OFF"
                extra = state.get("heat_mode_meaning", "")
                print(f"[{ts}]  Heat pump: {status}   raw={state['raw_value']!r}  {extra}")
            except Exception as exc:
                print(f"  ERROR: {exc}")
            await asyncio.sleep(interval_seconds)


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

async def main() -> None:
    # STEP 1 – run the diagnostic to find your heat pump key
    await run_diagnostic()

    # STEP 2 – once you know the key, use HeatPumpReader like this:
    #
    # Most common case (pool heat pump, mode integer = 3):
    #
    #   reader = HeatPumpReader(
    #       username=USERNAME,
    #       password=PASSWORD,
    #       mode="pool_heat_mode",         # or "spa_heat_mode"
    #       heat_pump_mode_value=3,
    #   )
    #   await reader.connect()
    #   state = await reader.get_heat_pump_state()
    #   print(state)
    #   # {'is_on': True, 'raw_value': '3', 'source': 'pool_heat_mode',
    #   #  'heat_mode_meaning': 'Heat pump'}
    #
    # If the diagnostic found a dedicated key (e.g. "dual_heat"):
    #
    #   reader = HeatPumpReader(
    #       username=USERNAME,
    #       password=PASSWORD,
    #       mode="home_key",
    #       home_key="dual_heat",
    #   )
    #   await reader.connect()
    #   state = await reader.get_heat_pump_state()
    #   print(state)
    #
    # For live polling:
    #   await reader.poll(interval_seconds=30)


if __name__ == "__main__":
    asyncio.run(main())
