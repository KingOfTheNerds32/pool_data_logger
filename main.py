import asyncio
import os
import pandas as pd
from datetime import datetime
import pytz

# Import the functions from your other files
from pool_logger import harvest_pool_data
from weather_logger import harvest_weather_data

async def main():
    pacific_tz = pytz.timezone('America/Los_Angeles')
    now = datetime.now(pacific_tz)
    unified_ts = now.strftime("%Y-%m-%d %H:%M:%S")
    
    results = {"Pool": False, "Weather": False}
    errors = {"Pool": "", "Weather": ""}
    
    # --- PART 1: CALCULATE TIME SINCE LAST SYNC ---
    last_sync_text = "No previous successful sync found"
    status_file = 'execution_log.csv'
    
    if os.path.exists(status_file):
        try:
            df_status = pd.read_csv(status_file)
            # Find the most recent row where pool_status was 'OK'
            successes = df_status[df_status['pool_status'] == 'OK']
            if not successes.empty:
                last_ok_str = successes['timestamp'].iloc[-1]
                last_ok_dt = datetime.strptime(last_ok_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pacific_tz)
                diff = now - last_ok_dt
                
                hours, remainder = divmod(int(diff.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)
                last_sync_text = f"{hours}h {minutes}m ago"
        except Exception as e:
            print(f"Metadata lookup failed: {e}")

    # --- PART 2: RUN POOL LOGGER (WITH RETRIES) ---
    for attempt in range(1, 4): # Try 3 times
        try:
            print(f"Pool Sync Attempt {attempt}/3...")
            await harvest_pool_data(unified_ts)
            results["Pool"] = True
            errors["Pool"] = "Synchronized"
            break 
        except Exception as e:
            errors["Pool"] = str(e)
            if attempt < 3:
                print(f"Attempt {attempt} failed: {e}. Retrying in 10s...")
                await asyncio.sleep(10)
            else:
                print(f"All 3 pool attempts failed.")

    # --- PART 3: RUN WEATHER LOGGER ---
    try:
        harvest_weather_data(unified_ts)
        results["Weather"] = True
    except Exception as e:
        errors["Weather"] = str(e)
        print(f"Weather Logger failed: {e}")

    # --- PART 4: LOGGING & SUMMARY ---
    # Log to CSV
    status_row = {
        'timestamp': unified_ts,
        'pool_status': 'OK' if results["Pool"] else 'FAIL',
        'weather_status': 'OK' if results["Weather"] else 'FAIL'
    }
    pd.DataFrame([status_row]).to_csv(status_file, mode='a', 
                                     header=not os.path.exists(status_file), index=False)

    # Write to GitHub Step Summary
    with open("job_summary.md", "w") as f:
        f.write("## 🚀 Telemetry Run Summary\n")
        f.write(f"**Current Run:** `{unified_ts}`\n")
        f.write(f"**Last Successful Pool Sync:** `{last_sync_text}`\n\n")
        f.write("| Service | Status | Details |\n")
        f.write("| :--- | :--- | :--- |\n")
        f.write(f"| Pool Data | {'✅ OK' if results['Pool'] else '❌ FAILED'} | {errors['Pool']} |\n")
        f.write(f"| Weather Data | {'✅ OK' if results['Weather'] else '❌ FAILED'} | {errors['Weather'] if not results['Weather'] else 'Synchronized'} |\n")

if __name__ == "__main__":
    asyncio.run(main())
