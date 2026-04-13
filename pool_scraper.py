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
        systems = await client.get_systems()
        if not systems:
            return
            
        system = list(systems.values())[0]
        await system.update()
        
        # 1. FETCH DEEP STATUS (The 'Teammate' Fix)
        # In 0.6.0, get_devices_list returns the raw JSON from the Jandy 'home' endpoint
        home_data = await system.get_devices_list()
        
        # Logic from your team: 0=Off, 1=Gas, 2=Solar, 3=Heat Pump
        # We check both possible nesting locations in the JSON
        pool_mode_int = home_data.get('pool_heat_mode', home_data.get('home', {}).get('pool_heat_mode', 0))
        spa_mode_int = home_data.get('spa_heat_mode', home_data.get('home', {}).get('spa_heat_mode', 0))

        def decode_heat_mode(val):
            mapping = {0: "OFF", 1: "GAS", 2: "SOLAR", 3: "HEAT PUMP"}
            try:
                return mapping.get(int(val), f"UNKNOWN ({val})")
            except (ValueError, TypeError):
                return "OFF"

        # 2. STANDARD DEVICE STATES
        row_data = {dev_id: device.state for dev_id, device in system.devices.items()}
        now = datetime.now(pytz.timezone('America/Los_Angeles'))

        def clean_binary(val):
            return "ON" if str(val) == '1' else "OFF"

        # 3. CONSTRUCT THE ROW
        final_row = {
            'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
            'pool_temp': row_data.get('pool_temp', 'N/A'),
            'air_temp': row_data.get('air_temp', 'N/A'),
            'pool_set_point': row_data.get('pool_set_point', 'N/A'),
            'filter_pump': clean_binary(row_data.get('pool_pump')),
            # THIS IS THE HEAT PUMP TRACKER
            'active_heat_source': decode_heat_mode(pool_mode_int),
            'spa_heat_source': decode_heat_mode(spa_mode_int),
            'gas_heater_mode': clean_binary(row_data.get('pool_heater')),
            'pool_light': clean_binary(row_data.get('aux_1')),
            'spillover': clean_binary(row_data.get('aux_3'))
        }

        # 4. SAVE TO CSV
        df = pd.DataFrame([final_row])
        file_path = 'pool_history.csv'
        
        if not os.path.exists(file_path) or os.stat(file_path).st_size == 0:
            df.to_csv(file_path, index=False)
        else:
            existing_df = pd.read_csv(file_path)
            pd.concat([existing_df, df], ignore_index=True).to_csv(file_path, index=False)
        
        print(f"[{now.strftime('%H:%M')}] Logged successfully.")
        print(f"Pool: {final_row['pool_temp']}F | Heat Source: {final_row['active_heat_source']}")

if __name__ == "__main__":
    asyncio.run(harvest_pool_data())
