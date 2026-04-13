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
        system = list(systems.values())[0]
        await system.update()
        
        print("--- INTERNAL OBJECT AUDIT ---")
        # 1. Check for the hidden raw data cache
        if hasattr(system, '_data'):
            print(f"INTERNAL _DATA FOUND:\n{json.dumps(system._data, indent=2)}")
        
        # 2. Check every device's internal dictionary
        print("\n--- INDIVIDUAL DEVICE INTERNAL DATA ---")
        for dev_id, device in system.devices.items():
            # Most iAquaLink objects store their raw API attributes in .data
            raw = getattr(device, 'data', 'No internal data')
            print(f"ID: {dev_id:20} | Raw Data: {raw}")

        # 3. Standard CSV Logging (so we don't miss a data point)
        row_data = {dev_id: device.state for dev_id, device in system.devices.items()}
        now = datetime.now(pytz.timezone('America/Los_Angeles'))
        
        final_row = {
            'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
            'pool_temp': row_data.get('pool_temp', 'N/A'),
            'air_temp': row_data.get('air_temp', 'N/A'),
            'filter_pump': "ON" if str(row_data.get('pool_pump')) == '1' else "OFF",
            'gas_heater': "ON" if str(row_data.get('pool_heater')) == '1' else "OFF"
        }

        df = pd.DataFrame([final_row])
        file_path = 'pool_history.csv'
        if not os.path.exists(file_path):
            df.to_csv(file_path, index=False)
        else:
            existing_df = pd.read_csv(file_path)
            pd.concat([existing_df, df], ignore_index=True).to_csv(file_path, index=False)
        
        print(f"\n[{now.strftime('%H:%M')}] Audit complete. Please share the 'INTERNAL _DATA' section from the log.")

if __name__ == "__main__":
    asyncio.run(harvest_pool_data())
