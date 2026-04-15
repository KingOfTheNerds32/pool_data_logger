import asyncio
from datetime import datetime
import pytz

# Import the functions from your other files
from pool_scraper import run_pool_scrape
from weather_logger import run_weather_scrape

async def main():
    # 1. Generate the single "Source of Truth" timestamp
    pacific_tz = pytz.timezone('America/Los_Angeles')
    unified_ts = datetime.now(pacific_tz).strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"Starting telemetry collection for: {unified_ts}")

    # 2. Run Pool Scraper (with error handling)
    try:
        await run_pool_scrape(unified_ts)
        print("Successfully logged pool data.")
    except Exception as e:
        print(f"Pool Scraper failed: {e}")

    # 3. Run Weather Scraper (with error handling)
    try:
        run_weather_scrape(unified_ts)
        print("Successfully logged weather data.")
    except Exception as e:
        print(f"Weather Scraper failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
