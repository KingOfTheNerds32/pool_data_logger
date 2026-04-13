import iaqualink
import asyncio
import pandas as pd
from datetime import datetime
import os
import pytz
from iaqualink.client import AqualinkClient

async def harvest_pool_data():
    # Credentials from GitHub Secrets
    USERNAME = os.environ.get('IQUALINK_USER')
    PASSWORD = os.environ.get('IQUALINK_PASS')

    async with AqualinkClient(USERNAME, PASSWORD) as client:
        systems = await client.get_systems()
        if not systems: return
        system = list(systems.values())[0]
        await system.update()
        
        # 1. Capture All Devices
        row_data = {dev_id: device for dev_id, device in system.devices.items()}
        now = datetime.now(pytz.timezone('America/Los_Angeles'))

        def get_state(dev_id):
            dev = row_data.get(dev_id)
            if dev is None: return "OFF"
            val = str(dev.state).lower()
            return "ON" if val in ['1', 'on', 'true'] else "OFF"

        # 2. SEARCH FOR THE HEAT PUMP BUTTON
        # We'll check the 'solar_heater' ID again, but also look for 'ext_heat' 
        # or any device that has "Heat Pump" in the label.
        hp_id = 'solar_heater' # Default suspect
        for dev_id, device in system.devices.items():
            if "heat pump" in str(device.label).lower():
                hp_id = dev_id
                break

        # 3. MAPPING THE DATA
        final_row = {
            'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
            'air_temp': getattr(row_data.get('air_temp'), 'state', 'N/A'),
            'pool_temp': getattr(row_data.get('pool_temp'), 'state', 'N/A'),
            'pool_set_point': getattr(row_data.get('pool_set_point'), 'state', 'N/A'),
            'filter_pump': get_state('pool_pump'),
            'gas_heater': get_state('pool_heater'),
            'spa_heater': get_state('spa_heater'),
            # This uses our discovered ID
            'heat_pump': get_state(hp_id),
            'hp_label': getattr(row_data.get(hp_id), 'label', 'Unknown HP'),
            'pool_light': get_state('aux_1'),
            'spillover': get_state('aux_3')
        }

        # 4. SAVE TO CSV
        df = pd.DataFrame([final_row])
        file_path = 'pool_history.csv'
        if not os.path.exists(file_path):
            df.to_csv(file_path, index=False)
        else:
            existing_df = pd.read_csv(file_path)
            pd.concat([existing_df, df], ignore_index=True).to_csv(file_path, index=False)
        
        print(f"[{now.strftime('%H:%M')}] Logged: HP ({final_row['hp_label']}) is {final_row['heat_pump']}")

if __name__ == "__main__":
    asyncio.run(harvest_pool_data())
