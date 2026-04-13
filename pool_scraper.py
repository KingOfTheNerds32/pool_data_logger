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
        
        pacific_tz = pytz.timezone('America/Los_Angeles')
        now = datetime.now(pacific_tz)

        # 1. DEEP AUDIT: Print all system attributes to find the Heat Pump
        print(f"--- SYSTEM DEEP AUDIT @ {now.strftime('%H:%M')} ---")
        # This looks for hidden properties like 'heater_priority' or 'heat_pump'
        for attr in dir(system):
            if not attr.startswith('_'): # Ignore internal python stuff
                try:
                    value = getattr(system, attr)
                    if not callable(value): # Only print data, not functions
                        print(f"ATTR: {attr:20} | VALUE: {value}")
                except:
                    continue
        print("--- END AUDIT ---")

        # 2. BRUTE FORCE DEVICE LOG
        row = {'timestamp': now.strftime("%Y-%m-%d %H:%M:%S")}
        for dev_id, device in system.devices.items():
            # We log the RAW value this time to see if it's something other than 0 or 1
            val = device.state
            row[dev_id] = "OFF" if (val == '0' or val == 0 or val == "") else ("ON" if (val == '1' or val == 1) else val)

        # 3. ROBUST CSV SAVE
        df_new = pd.DataFrame([row])
        file_path = 'pool_history.csv'
        
        if not os.path.exists(file_path) or os.stat(file_path).st_size == 0:
            df_new.to_csv(file_path, index=False)
        else:
            try:
                existing_df = pd.read_csv(file_path)
                # If you added new devices, this ensures the columns align
                combined = pd.concat([existing_df, df_new], ignore_index=True)
                combined.to_csv(file_path, index=False)
            except pd.errors.EmptyDataError:
                df_new.to_csv(file_path, index=False)
        
        print(f"\nSUCCESS: Logged {len(row)} data points to CSV.")

if __name__ == "__main__":
    asyncio.run(harvest_pool_data())
