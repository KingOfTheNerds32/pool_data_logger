import iaqualink
import asyncio
import pandas as pd
from datetime import datetime
import os

async def harvest_pool_data():
    # Credentials (You'll put these in GitHub Secrets later)
    USERNAME = os.environ.get('IQUALINK_USER')
    PASSWORD = os.environ.get('IQUALINK_PASS')

    # Log in and fetch devices
    async with iaqualink.AqualinkClient(USERNAME, PASSWORD) as client:
        systems = await client.get_systems()
        # Assume you have one pool system
        pool = list(systems.values())[0]
        await pool.update()

        for device in pool.devices.values():
            print(f"Device Name: {device.name} | Type: {device.label}")
        
        # Extract data points
        data = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'pool_temp': pool.pool_temp,
            'spa_temp': pool.spa_temp,
            'air_temp': pool.air_temp,
            # This checks if specific buttons are "On"
            'filter_pump': pool.get_device('Filter Pump').is_on,
            'cleaner': pool.get_device('Cleaner').is_on if pool.get_device('Cleaner') else "N/A",
            'heater': pool.get_device('Pool Heater').is_on
        }

        # Save to CSV (just like your Disney project)
        df = pd.DataFrame([data])
        file_path = 'pool_history.csv'
        df.to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)

if __name__ == "__main__":
    asyncio.run(harvest_pool_data())
