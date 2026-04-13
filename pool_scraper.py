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
        
        row_data = {dev_id: device.state for dev_id, device in system.devices.items()}

        # PST Time
        pacific_tz = pytz.timezone('America/Los_Angeles')
        now = datetime.now(pacific_tz)

        # Helper to convert 0/1 or "0"/"1" to ON/OFF
        def on_off(val):
            if val is None or val == "": return "OFF"
            return "ON" if str(val) == "1" else "OFF"

        # Mapping every sensor from your specific Discovery Log
        final_row = {
            'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
            
            # Temperatures (Note: iAquaLink often returns empty string if sensor is off)
            'air_temp': row_data.get('air_temp', 'N/A'),
            'pool_temp': row_data.get('pool_temp', 'N/A'),
            'spa_temp': row_data.get('spa_temp', 'N/A'),
            
            # Set Points
            'pool_set_point': row_data.get('pool_set_point', 'N/A'),
            'spa_set_point': row_data.get('spa_set_point', 'N/A'),
            
            # Equipment Status
            'pool_pump': on_off(row_data.get('pool_pump')),
            'spa_pump': on_off(row_data.get('spa_pump')),
            'pool_heater': on_off(row_data.get('pool_heater')),
            'spa_heater': on_off(row_data.get('spa_heater')),
            'solar_heater': on_off(row_data.get('solar_heater')),
            
            # Lights & Features
            'pool_light': on_off(row_data.get('aux_1')),
            'spa_light': on_off(row_data.get('aux_2')),
            'spillover': on_off(row_data.get('aux_3')),
            'jet_pump': on_off(row_data.get('aux_4')),
            
            # Chemistry (If active)
            'ph': row_data.get('ph', 'N/A'),
            'orp': row_data.get('orp', 'N/A'),
            'salinity': row_data.get('pool_salinity', 'N/A')
        }

        # Save to CSV
        df = pd.DataFrame([final_row])
        file_path = 'pool_history.csv'
        df.to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)
        print(f"Logged all equipment states at {now.strftime('%I:%M %p')} PT")

if __name__ == "__main__":
    asyncio.run(harvest_pool_data())
