import iaqualink
import asyncio
import pandas as pd
from datetime import datetime
import os
import pytz

async def harvest_pool_data():
    # Credentials from GitHub Secrets
    USERNAME = os.environ.get('IQUALINK_USER')
    PASSWORD = os.environ.get('IQUALINK_PASS')

    # 1. Newest Entry Point: iaqualink.Aqualink
    async with iaqualink.Aqualink(USERNAME, PASSWORD) as client:
        systems = await client.get_systems()
        
        if not systems:
            print("No pool systems found. Check credentials or iAquaLink server status.")
            return

        # Pick the first system
        system = list(systems.values())[0]
        
        # 2. DISCOVERY: This will list all your devices in the GitHub Action Logs
        print(f"--- DEVICE DISCOVERY FOR {system.name} ---")
        await system.update() # Refresh the data
        
        # We'll store our row data here
        row_data = {}
        
        # This loop prints every device to the log so you can find the names
        for dev_name, device in system.devices.items():
            print(f"Device Key: {dev_name} | Label: {device.label} | State: {device.state}")
            # Map common sensors to our CSV row
            row_data[dev_name] = device.state

        print("--- END DISCOVERY ---\n")

        # 3. Handle Time (PST/PDT)
        pacific_tz = pytz.timezone('America/Los_Angeles')
        now_pacific = datetime.now(pacific_tz)

        # Build the specific CSV row
        # We use .get() so it doesn't crash if a specific sensor is missing
        final_row = {
            'timestamp': now_pacific.strftime("%Y-%m-%d %H:%M:%S"),
            'pool_temp': row_data.get('pool_temp', 'N/A'),
            'spa_temp': row_data.get('spa_temp', 'N/A'),
            'air_temp': row_data.get('air_temp', 'N/A'),
            'filter_pump': row_data.get('filter_pump', 'N/A'),
            'heater': row_data.get('pool_heater', 'N/A')
        }

        # Save to CSV
        df = pd.DataFrame([final_row])
        file_path = 'pool_history.csv'
        df.to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)
        
        print(f"Logged: Pool {final_row['pool_temp']}° / Air {final_row['air_temp']}° at {now_pacific.strftime('%I:%M %p')} PT")

if __name__ == "__main__":
    asyncio.run(harvest_pool_data())
