import iaqualink
import asyncio
import pandas as pd
from datetime import datetime
import os
import pytz
from iaqualink.client import AqualinkClient
import json

async def harvest_pool_data():
    USERNAME = os.environ.get('IQUALINK_USER')
    PASSWORD = os.environ.get('IQUALINK_PASS')

    async with AqualinkClient(USERNAME, PASSWORD) as client:
        # Get the systems
        systems = await client.get_systems()
        system = list(systems.values())[0]
        
        # This is the "Magic" line: 
        # We are going to look at the rawest possible data internal to the object
        await system.update()
        
        print("--- ABSOLUTE RAW DATA DUMP ---")
        # In 0.6.0, the actual API response is often in system._data or system.devices
        # We will loop through everything in the object to find the hidden JSON
        for attr in dir(system):
            if attr == 'data' or attr == '_data':
                val = getattr(system, attr)
                print(f"Prop: {attr}\n{json.dumps(val, indent=2)}")
        print("--- END RAW DATA ---")

        # Standard Logging for your CSV
        row_data = {dev_id: device.state for dev_id, device in system.devices.items()}
        now = datetime.now(pytz.timezone('America/Los_Angeles'))

        def clean(val):
            if val is None or str(val).strip() == "": return "OFF"
            return "ON" if str(val) == "1" else ("OFF" if str(val) == "0" else val)

        final_row = {
            'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
            'pool_temp': row_data.get('pool_temp', 'N/A'),
            'air_temp': row_data.get('air_temp', 'N/A'),
            'filter_pump': clean(row_data.get('pool_pump')),
            'gas_heater': clean(row_data.get('pool_heater'))
        }

        df = pd.DataFrame([final_row])
        file_path = 'pool_history.csv'
        if not os.path.exists(file_path):
            df.to_csv(file_path, index=False)
        else:
            existing_df = pd.read_csv(file_path)
            pd.concat([existing_df, df], ignore_index=True).to_csv(file_path, index=False)
        
        print(f"\n[{now.strftime('%H:%M')}] Logged. Waiting for Raw Dump inspection...")

if __name__ == "__main__":
    asyncio.run(harvest_pool_data())
