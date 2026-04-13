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
        
        # PST Time
        pacific_tz = pytz.timezone('America/Los_Angeles')
        now = datetime.now(pacific_tz)

        # 1. Create a dictionary for the CSV row
        row = {'timestamp': now.strftime("%Y-%m-%d %H:%M:%S")}
        
        # 2. Add every device found in discovery to the CSV automatically
        for dev_id, device in system.devices.items():
            # Clean up the state for the CSV
            state = device.state
            if state is None or str(state).strip() == "":
                state = "OFF"
            elif str(state) == "1":
                state = "ON"
            elif str(state) == "0":
                state = "OFF"
            
            row[dev_id] = state

        # 3. Check for hidden Heat Pump attributes (v0.6.0 specific)
        # Some systems store HP state here instead of the device list
        hp_state = getattr(system, 'heat_pump', 'UNKNOWN')
        row['hp_internal_state'] = hp_state

        # Save to CSV (This will automatically add new columns if the device list grows)
        df = pd.DataFrame([row])
        file_path = 'pool_history.csv'
        
        # Handle header logic for a dynamic CSV
        if not os.path.exists(file_path):
            df.to_csv(file_path, index=False)
        else:
            existing_df = pd.read_csv(file_path)
            combined = pd.concat([existing_df, df], ignore_index=True)
            combined.to_csv(file_path, index=False)
        
        print(f"[{now.strftime('%I:%M %p')}] Brute-force log complete. {len(row)} data points saved.")

if __name__ == "__main__":
    asyncio.run(harvest_pool_data())
