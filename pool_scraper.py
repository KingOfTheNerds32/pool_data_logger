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
            print("No systems found.")
            return

        system = list(systems.values())[0]
        await system.update()
        
        # Capture all raw states
        row_data = {dev_id: device.state for dev_id, device in system.devices.items()}

        # PST Time for Rolling Hills Estates
        pacific_tz = pytz.timezone('America/Los_Angeles')
        now = datetime.now(pacific_tz)

        def on_off(val):
            if val is None or str(val).strip() == "": return "OFF"
            s = str(val).lower()
            return "ON" if s in ['1', 'on', 'true', 'enabled'] else "OFF"

        # --- CONSOLE LOGGING (EVERY DEVICE) ---
        print(f"--- STATUS REPORT @ {now.strftime('%I:%M %p')} ---")
        for dev_id, state in row_data.items():
            # We print only the devices that have a '1' or are actually doing something
            # to make the console easier to read
            status = on_off(state)
            label = system.devices[dev_id].label
            print(f"[{status:3}] {label:20} (ID: {dev_id}) | Raw: {state}")
        print("--- END REPORT ---")

        # Map to CSV row
        final_row = {
            'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
            'air_temp': row_data.get('air_temp', 'N/A'),
            'pool_temp': row_data.get('pool_temp', 'N/A'),
            'pool_set_point': row_data.get('pool_set_point', 'N/A'),
            'filter_pump': on_off(row_data.get('pool_pump')),
            'gas_heater': on_off(row_data.get('pool_heater')),
            'heat_pump_solar': on_off(row_data.get('solar_heater')),
            'heat_pump_extra': on_off(row_data.get('aux_EA')),
            'pool_light': on_off(row_data.get('aux_1'))
        }

        # Save to CSV
        df = pd.DataFrame([final_row])
        file_path = 'pool_history.csv'
       #  df.to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)
        print(f"\nCSV row added for {now.strftime('%I:%M %p')}.")

if __name__ == "__main__":
    asyncio.run(harvest_pool_data())
