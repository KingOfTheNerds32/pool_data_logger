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
        
        # --- DEEP SEARCH LOGGING ---
        print(f"--- ACTIVE DEVICE SEARCH ---")
        row_data = {}
        for dev_id, device in system.devices.items():
            # If the state is 1, it's ON. Let's see what's active!
            if str(device.state) == '1':
                print(f"ACTIVE >> ID: {dev_id:20} | Label: {device.label}")
            
            row_data[dev_id] = device.state
        
        # Check for hidden heater attributes
        if hasattr(system, 'heater_options'):
            print(f"Heater Options Found: {system.heater_options}")
        
        print("--- END SEARCH ---")

        # PST Time
        pacific_tz = pytz.timezone('America/Los_Angeles')
        now = datetime.now(pacific_tz)

        def on_off(val):
            return "ON" if str(val) == "1" else "OFF"

        # Current Mapping
        final_row = {
            'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
            'air_temp': row_data.get('air_temp', 'N/A'),
            'pool_temp': row_data.get('pool_temp', 'N/A'),
            'pool_set_point': row_data.get('pool_set_point', 'N/A'),
            'pool_pump': on_off(row_data.get('pool_pump')),
            'gas_pool_mode': on_off(row_data.get('pool_heater')),
            # We'll leave this as a placeholder until we find the real ID
            'heat_pump_active': "UNKNOWN" 
        }

        # Save to CSV
        df = pd.DataFrame([final_row])
        file_path = 'pool_history.csv'
        # df.to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)

if __name__ == "__main__":
    asyncio.run(harvest_pool_data())
