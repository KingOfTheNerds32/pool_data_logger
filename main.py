import asyncio
import os
import pandas as pd
from datetime import datetime
import pytz

# Import the functions from your other files
from pool_logger import harvest_pool_data
from weather_logger import harvest_weather_data

async def main():
    # 1. Generate the single "Source of Truth" timestamp
    pacific_tz = pytz.timezone('America/Los_Angeles')
    now = datetime.now(pacific_tz)
    unified_ts = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # Track success for logging/summary
    results = {"Pool": False, "Weather": False}
    
    print(f"Starting telemetry collection for: {unified_ts}")

    # 2. Run Pool Logger (with error handling)
    try:
        await harvest_pool_data(unified_ts)
        results["Pool"] = True
        print("Successfully logged pool data.")
    except Exception as e:
        print(f"Pool Logger failed: {e}")

    # 3. Run Weather Logger (with error handling)
    try:
        harvest_weather_data(unified_ts)
        results["Weather"] = True
        print("Successfully logged weather data.")
    except Exception as e:
        print(f"Weather Logger failed: {e}")

    # --- NEW LOGGING INTEGRATIONS ---

    # 4. Write to historical execution CSV (Appends for data analysis)
    status_row = {
        'timestamp': unified_ts,
        'pool_status': 'OK' if results["Pool"] else 'FAIL',
        'weather_status': 'OK' if results["Weather"] else 'FAIL'
    }
    status_df = pd.DataFrame([status_row])
    status_file = 'execution_log.csv'
    status_df.to_csv(status_file, mode='a', 
                      header=not os.path.exists(status_file), index=False)

    # 5. Write to GitHub Step Summary (For the UI table)
    with open("job_summary.md", "w") as f:
        f.write("## 🚀 Telemetry Run Summary\n")
        f.write(f"**Timestamp:** `{unified_ts}`\n\n")
        f.write("| Service | Status |\n")
        f.write("| :--- | :--- |\n")
        f.write(f"| Pool Data | {'✅ OK' if results['Pool'] else '❌ FAILED'} |\n")
        f.write(f"| Weather Data | {'✅ OK' if results['Weather'] else '❌ FAILED'} |\n")

if __name__ == "__main__":
    asyncio.run(main())
