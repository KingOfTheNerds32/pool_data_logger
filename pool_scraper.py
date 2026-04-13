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
        # 1. INITIALIZE CONNECTION
        systems = await client.get_systems()
        if not systems:
            print("Login failed or no systems found.")
            return
            
        system = list(systems.values())[0]
        await system.update()
        
        # 2. FETCH DEEP STATUS (For Heat Pump mode)
        # We reach through the client's session to get the 'home' data
        serial = system.serial
        home_data = await client.session.get_home(serial)
        
        # Pulling the integer modes identified by your teammate
        # 0=Off, 1=Gas, 2=Solar, 3=Heat Pump
        raw_home = home_data.get('home', {})
        pool_mode_int = raw_home.get('pool_heat_mode', 0)
        spa_mode_int = raw_home.get('spa_heat_mode', 0)

        def decode_heat_mode(val):
            mapping = {0: "OFF", 1: "GAS", 2: "SOLAR", 3: "HEAT PUMP"}
            try:
                return mapping.get(int(val), f"UNKNOWN ({val})")
            except:
                return "OFF"

        # 3. CAPTURE DEVICE STATES
        row_data = {dev_id: device.state for dev_id, device in system.devices.items()}
        now = datetime.now(pytz.timezone('America/Los_Angeles'))

        def clean_binary(val):
            return "ON" if str(val) == '1' else "OFF"

        # 4. CONSTRUCT THE ROW
        final_row = {
            'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
            'air_temp': row_data.get('air_temp', 'N/A'),
            'pool_temp': row_data.get('pool_temp', 'N/A'),
            'pool_set_point': row_data.get('pool_set_point', 'N/A'),
            'filter_pump': clean_binary(row_data.get('pool_pump')),
            # MAPPING THE HEATER SOURCE
            'active_heat_source': decode_heat_mode(pool_mode_int),
            'spa_heat_source': decode_heat_mode(spa_mode_int),
            'gas_heater_enabled': clean_binary(row_data.get('pool_heater')),
            # EQUIPMENT
            'pool_light': clean_binary(row_data.get('aux_1')),
            'spillover': clean_binary(row_data.get('aux_3')),
            'jet_pump': clean_binary(row_data.get('aux_4'))
        }

        # 5. SAVE TO CSV
        df = pd.DataFrame([final_row])
        file_path = 'pool_history.csv'
        
        if not os.path.exists(file_path):
            df.to_csv(file_path, index=False)
        else:
            try:
                existing_df = pd.read_csv(file_path)
                # Concat ensures we preserve existing data even if columns expand
                pd.concat([existing_df, df], ignore_index=True).to_csv(file_path, index=False)
            except:
                df.to_csv(file_path, index=False)
        
        print(f"[{now.strftime('%H:%M')}] Logged Successfully.")
        print(f"Pool: {final_row['pool_temp']}F | Mode: {final_row['active_heat_source']}")

if __name__ == "__main__":
    asyncio.run(harvest_pool_data())
