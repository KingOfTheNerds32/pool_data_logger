import iaqualink
import asyncio
import pandas as pd
from datetime import datetime
import os
import pytz
from iaqualink.client import AqualinkClient

async def harvest_pool_data():
    USERNAME = os.environ.get('IQUALINK_USER')
    PASSWORD = os.environ.get('IQUALINK_PASS')

    async with AqualinkClient(USERNAME, PASSWORD) as client:
        # 1. Initialize and get systems
        systems = await client.get_systems()
        if not systems:
            print("No systems found.")
            return
            
        system = list(systems.values())[0]
        await system.update()
        
        # 2. Get the "Home" data (The teammate's fix)
        # We call get_home directly on the client object
        serial = system.serial
        home_data = await client.get_home(serial)
        
        # Logic: 0=Off, 1=Gas, 2=Solar, 3=Heat Pump
        pool_mode_int = home_data.get('pool_heat_mode', 0)
        spa_mode_int = home_data.get('spa_heat_mode', 0)

        def decode_heat_mode(val):
            mapping = {0: "OFF", 1: "GAS", 2: "SOLAR", 3: "HEAT PUMP"}
            try:
                # API sometimes returns strings, so we convert to int safely
                return mapping.get(int(val), f"UNKNOWN ({val})")
            except (ValueError, TypeError):
                return "OFF"

        # 3. Standard device states
        row_data = {dev_id: device.state for dev_id, device in system.devices.items()}
        now = datetime.now(pytz.timezone('America/Los_Angeles'))

        def clean_binary(val):
            return "ON" if str(val) == '1' else "OFF"

        # 4. Construct the row
        final_row = {
            'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
            'pool_temp': row_data.get('pool_temp', 'N/A'),
            'air_temp': row_data.get('air_temp', 'N/A'),
            'pool_set_point': row_data.get('pool_set_point', 'N/A'),
            'filter_pump': clean_binary(row_data.get('pool_pump')),
            # Tracking the hidden mode
            'active_heat_source': decode_heat_mode(pool_mode_int),
            'spa_heat_source': decode_heat_mode(spa_mode_int),
            'gas_heater_mode': clean_binary(row_data.get('pool_heater')),
            'pool_light': clean_binary(row_data.get('aux_1')),
            'spillover': clean_binary(row_data.get('aux_3'))
        }

        # 5. Save to CSV
        df = pd.DataFrame([final_row])
        file_path = 'pool_history.csv'
        
        if not os.path.exists(file_path) or os.stat(file_path).st_size == 0:
            df.to_csv(file_path, index=False)
        else:
            existing_df = pd.read_csv(file_path)
            pd.concat([existing_df, df], ignore_index=True).to_csv(file_path, index=False)
        
        print(f"[{now.strftime('%H:%M')}] Logged. Pool {final_row['pool_temp']}F | Mode: {final_row['active_heat_source']}")

if __name__ == "__main__":
    asyncio.run(harvest_pool_data())
