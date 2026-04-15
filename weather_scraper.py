import os
import requests
import pandas as pd
from datetime import datetime
import pytz

def harvest_weather_data():
    API_KEY = os.environ.get('OPENWEATHER_API_KEY')
    LAT = os.environ.get('LAT')
    LON = os.environ.get('LONG')
    
    if not all([API_KEY, LAT, LON]):
        print("Error: Missing Environment Variables (API_KEY, LAT, or LON)")
        return

    # Using the standard 2.5 endpoint for maximum reliability on free tier
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={API_KEY}&units=imperial"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if response.status_code == 200:
            pacific_tz = pytz.timezone('America/Los_Angeles')
            now = datetime.now(pacific_tz)
            
            # THE "EVERYTHING" LOG
            weather_row = {
                'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
                
                # TEMPERATURE SUITE
                'temp_actual': data['main'].get('temp'),
                'temp_feels_like': data['main'].get('feels_like'), # Disney: For comfort levels
                'temp_min': data['main'].get('temp_min'),
                'temp_max': data['main'].get('temp_max'),
                
                # ATMOSPHERIC SUITE
                'humidity': data['main'].get('humidity'),         # Pool: Vital for Heat Pump COP
                'pressure': data['main'].get('pressure'),
                'pressure_sea': data['main'].get('sea_level'),
                'visibility_meters': data.get('visibility'),      # Solar: Measures "haze"
                'clouds_percent': data['clouds'].get('all'),      # Solar: Main production factor
                
                # WIND SUITE
                'wind_speed': data['wind'].get('speed'),          # Pool: Main evaporation factor
                'wind_deg': data['wind'].get('deg'),              # Home: Identifies "wind tunnels"
                'wind_gust': data['wind'].get('gust', 0),
                
                # PRECIPITATION (Checks if the 'rain' or 'snow' keys exist)
                'rain_1h_mm': data.get('rain', {}).get('1h', 0),
                'snow_1h_mm': data.get('snow', {}).get('1h', 0),
                
                # SUNLIGHT (Useful for Pool/Solar timing)
                'sunrise_unix': data['sys'].get('sunrise'),
                'sunset_unix': data['sys'].get('sunset'),
                
                # CONDITION CODES
                'weather_id': data['weather'][0].get('id'),       # Numeric code for easy plotting
                'condition_main': data['weather'][0].get('main'),
                'condition_desc': data['weather'][0].get('description')
            }
            
            df = pd.DataFrame([weather_row])
            file_path = 'weather_history.csv'
            
            # Logic to handle headers and appending
            header_needed = not os.path.exists(file_path) or os.stat(file_path).st_size == 0
            df.to_csv(file_path, mode='a', header=header_needed, index=False)
            
            print(f"[{now.strftime('%H:%M')}] Logged {len(weather_row)} data points for {LAT}, {LON}")
        else:
            print(f"API Error {response.status_code}: {data.get('message')}")
            
    except Exception as e:
        print(f"Execution Error: {e}")

if __name__ == "__main__":
    harvest_weather_data()
