import iaqualink
import asyncio
import pandas as pd
from datetime import datetime
import os
import pytz
# In 0.6.0, we have to import the specific Client class like this:
from iaqualink.client import AqualinkClient

async def harvest_pool_data():
    USERNAME = os.environ.get('IQUALINK_USER')
    PASSWORD = os.environ.get('IQUALINK_PASS')

    # Initialize the client using the explicit class
    async with AqualinkClient(USERNAME, PASSWORD) as client:
        systems = await client.get_systems()
        
        if not systems:
            print("Login successful, but no systems found.")
            return

        system = list(systems.values())[0]
        await system.update()
        
        # --- DISCOVERY LOGGING ---
        print(f"--- DEVICE DISCOVERY (v0.6.0) ---")
        row_data = {}
        # In 0.6.0, devices are stored in the .devices dictionary
        for dev_id, device in system.devices.items():
            print(f"ID: {dev_id:20} | Label: {device.label:20} | State: {device.state}")
            row_data[dev_id] = device.state
        print("--- END DISCOVERY ---\n")

        # --- TIMEZONE (PST) ---
        pacific_tz = pytz.timezone('America/Los_Angeles')
        now = datetime.now(pacific_tz)

        # --- DATA MAPPING ---
        def clean_state(val):
            if val is None: return "N/A"
            s = str(val).lower()
            if s in ['on', '1', 'true', 'enabled']: return "ON"
            if s in ['off', '0', 'false', 'disabled']: return "OFF"
            return val

        final_row = {
            'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
            'pool_temp': row_data.get('pool_temp', 'N/A'),
            'air_temp': row_data.get('air_temp', 'N/A'),
            'spa_temp': row_data.get('spa_temp', 'N/A'),
            'filter_pump': clean_state(row_data.get('filter_pump')),
            'pool_heater': clean_state(row_data.get('pool_heater'))
        }

        # SAVE TO CSV
        df = pd.DataFrame([final_row])
        file_path = 'pool_history.csv'
        # df.to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)
        print(f"Success! Logged {final_row['pool_temp']}°F at {now.strftime('%I:%M %p')} PT")

if __name__ == "__main__":
    asyncio.run(harvest_pool_data())
