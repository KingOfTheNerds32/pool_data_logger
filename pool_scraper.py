import iaqualink
import asyncio
import pandas as pd
from datetime import datetime
import os
import pytz
from iaqualink.client import AqualinkClient
import json

async def harvest_pool_data():
    # Credentials from GitHub Secrets
    USERNAME = os.environ.get('IQUALINK_USER')
    PASSWORD = os.environ.get('IQUALINK_PASS')

    async with AqualinkClient(USERNAME, PASSWORD) as client:
        systems = await client.get_systems()
        if not systems: return
        system = list(systems.values())[0]
        await system.update()
        
        # 1. ACCESS RAW HOME DATA (Where the Heat Mode lives)
        # We reach into the session to get the flattened home data
        session = system._session
        home_data = await session.get_home(system.serial)
        
        # This function flattens the nested JSON so we can find 'pool_heat_mode'
        def flatten(obj, prefix=""):
            items = {}
            if isinstance(obj, dict):
                for k, v in obj.items():
                    full_key = f"{prefix}.{k}" if prefix else k
                    items.update(flatten(v, full_key))
            else:
                items[prefix] = obj
            return items

        flat_data = flatten(home_data)

        # 2. EXTRACT HEATER MODES
        # Logic: 0=Off, 1=Gas, 2=Solar, 3=Heat Pump
        def decode_heat_mode(val):
            mapping = {0: "OFF", 1: "GAS", 2: "SOLAR", 3: "HEAT PUMP"}
            try:
                return mapping.get(int(val), f"UNKNOWN ({val})")
            except:
                return "OFF"

        pool_mode_raw = flat_data.get("pool_heat_mode") or flat_data.get("home.pool_heat_mode")
        spa_mode_raw = flat_data.get("spa_heat_mode") or flat_data.get("home.spa_heat_mode")

        # 3. CAPTURE STANDARD DEVICES
        row_data = {dev_id: device.state for dev_id, device in system.devices.items()}
        now = datetime.now(pytz.timezone('America/Los_Angeles'))

        def clean_binary(val):
            return "ON" if str(val) == '1' else "OFF"

        # 4. CONSTRUCT THE ROW
        final_row = {
            'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
            'air_temp': row_data.get('air_temp', 'N/A'),
            'pool_temp': row_data.get('pool_temp', 'N/A'),
            'pool_set_point': row_data.get('pool_set_point', 'N/A'),
            'filter_pump': clean_binary(row_data.get('pool_pump')),
            # This is the NEW logic you found!
            'active_heat_source': decode_heat_mode(pool_mode_raw),
            'spa_heat_source': decode_heat_mode(spa_mode_raw),
            # Standard toggles
            'gas_heater_enabled': clean_binary(row_data.get('pool_heater')),
            'pool_light': clean_binary(row_data.get('aux_1')),
            'spillover': clean_binary(row_data.get('aux_3'))
        }

        # 5. SAVE TO CSV
        df = pd.DataFrame([final_row])
        file_path = 'pool_history.csv'
        if not os.path.exists(file_path):
            df.to_csv(file_path, index=False)
        else:
            existing_df = pd.read_csv(file_path)
            pd.concat([existing_df, df], ignore_index=True).to_csv(file_path, index=False)
        
        print(f"[{now.strftime('%H:%M')}] Logged. Mode: {final_row['active_heat_source']} | Pool: {final_row['pool_temp']}F")

if __name__ == "__main__":
    asyncio.run(harvest_pool_data())
