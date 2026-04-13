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
        systems = await client.get_systems()
        if not systems:
            print("Login failed or no systems found.")
            return
            
        system = list(systems.values())[0]
        await system.update()
        
        # --- THE PACKET SNIFFER ---
        # This is the important part. It prints the raw data from Jandy.
        print("--- RAW API DATA SNIFFER ---")
        print(json.dumps(system.data, indent=2))
        print("--- END RAW DATA ---")

        # --- LOGGING TO CSV ---
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
        
        print(f"\n[{now.strftime('%H:%M')}] Data logged. Check the Raw Sniffer output above for Heat Pump keys.")

if __name__ == "__main__":
    asyncio.run(harvest_pool_data())
