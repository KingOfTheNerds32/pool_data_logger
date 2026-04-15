import asyncio
from datetime import datetime
import pytz

# Import the functions from your other files
from pool_logger import harvest_pool_data
from weather_logger import harvest_weather_data

async def main():
    # 1. Generate the single "Source of Truth" timestamp
    pacific_tz = pytz.timezone('America/Los_Angeles')
    unified_ts = datetime.now(pacific_tz).strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"Starting telemetry collection for: {unified_ts}")

    # 2. Run Pool Logger (with error handling)
    try:
        await harvest_pool_data(unified_ts)
        print("Successfully logged pool data.")
    except Exception as e:
        print(f"Pool Logger failed: {e}")

    # 3. Run Weather Logger (with error handling)
    try:
        harvest_weather_data(unified_ts)
        print("Successfully logged weather data.")
    except Exception as e:
        print(f"Weather Logger failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
