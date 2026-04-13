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
        if not systems: return
        system = list(systems.values())[0]
        await system.update()
        
        # 1. THE HUNTER: Look for "Heat Pump" in every hidden property
        print("--- SEARCHING FOR HEAT PUMP STATE ---")
        # Check raw JSON data from Jandy
        raw_data = system.data
        for key, value in raw_data.items():
            if 'heat' in key.lower() or 'pump' in key.lower() or 'hp' in key.lower():
                print(f"FOUND IN DATA: {key} = {value}")

        # Check for specific heater attributes
        for attr in ['heater_mode', 'heater_state', 'heat_pump', 'hot_button']:
            if hasattr(system, attr):
                print(f"FOUND ATTR: {attr} = {getattr(system, attr)}")
        print("--- END SEARCH ---")

        # 2. THE LOGGER
        row_data = {dev_id: device.state for dev_id, device in system.devices.items()}
        now = datetime.now(pytz.timezone('America/Los_Angeles'))

        def clean(val):
            if val is None or str(val).strip() == "": return "OFF"
            return "ON" if str(val) == "1" else ("OFF" if str(val) == "0" else val)

        final_row = {
            'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
            'pool_temp': row_data.get('pool_temp', 'N/A'),
            'air_temp': row_data.get('air_temp', 'N/A'),
            'pool_set_point': row_data.get('pool_set_point', 'N/A'),
            'gas_heater': clean(row_data.get('pool_heater')),
            'filter_pump': clean(row_data.get('pool_pump')),
            # We will use this to see if any unknown ID is actually the HP
            'hp_id_mystery': clean(row_data.get('aux_EA')) 
        }

        # Save to CSV
        df = pd.DataFrame([final_row])
        file_path = 'pool_history.csv'
        if not os.path.exists(file_path):
            df.to_csv(file_path, index=False)
        else:
            existing_df = pd.read_csv(file_path)
            pd.concat([existing_df, df], ignore_index=True).to_csv(file_path, index=False)

if __name__ == "__main__":
    asyncio.run(harvest_pool_data())
