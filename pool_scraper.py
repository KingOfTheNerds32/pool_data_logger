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
        
        # Capture all raw states
        row_data = {dev_id: device.state for dev_id, device in system.devices.items()}

        # PST Time
        pacific_tz = pytz.timezone('America/Los_Angeles')
        now = datetime.now(pacific_tz)

        # Standardizing "ON/OFF"
        def on_off(val):
            # iAqualink 0.6.0 often uses empty strings for 'No State'
            if val is None or str(val).strip() == "": return "OFF"
            s = str(val).lower()
            return "ON" if s in ['1', 'on', 'true', 'enabled'] else "OFF"

        final_row = {
            'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
            
            # Temperatures
            'air_temp': row_data.get('air_temp', 'N/A'),
            'pool_temp': row_data.get('pool_temp', 'N/A'),
            'pool_set_point': row_data.get('pool_set_point', 'N/A'),
            
            # The Equipment "Power" States
            'filter_pump': on_off(row_data.get('pool_pump')),
            'gas_heater_mode': on_off(row_data.get('pool_heater')),
            
            # --- THE HEAT PUMP TARGETS ---
            # Most likely candidate: solar_heater
            'heat_pump_solar': on_off(row_data.get('solar_heater')),
            # Second candidate: aux_EA (Extra Aux)
            'heat_pump_extra': on_off(row_data.get('aux_EA')),
            
            # Other Features
            'pool_light': on_off(row_data.get('aux_1')),
            'spa_light': on_off(row_data.get('aux_2')),
            'spillover': on_off(row_data.get('aux_3'))
        }

        # Save to CSV
        df = pd.DataFrame([final_row])
        file_path = 'pool_history.csv'
       #  df.to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)
        
        # Verification Print
        print(f"[{now.strftime('%H:%M')}] Logged. Solar/HP State: {final_row['heat_pump_solar']}")

if __name__ == "__main__":
    asyncio.run(harvest_pool_data())
