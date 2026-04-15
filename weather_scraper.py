import os
import requests
import pandas as pd
from datetime import datetime
import pytz

def harvest_weather_data():
    API_KEY = os.environ.get('OPENWEATHER_API_KEY')
  
    # Get coordinates
    LAT = os.environ.get('LAT')
    LON = os.environ.get('LONG')
    
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={API_KEY}&units=imperial"
    
    response = requests.get(url)
    data = response.json()
    
    if response.status_code == 200:
        pacific_tz = pytz.timezone('America/Los_Angeles')
        now = datetime.now(pacific_tz)
        
        weather_row = {
            'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
            'outside_temp': data['main']['temp'],
            'humidity': data['main']['humidity'],
            'wind_speed': data['wind']['speed'],
            'wind_deg': data['wind']['deg'],
            'condition': data['weather'][0]['description'],
            'pressure': data['main']['pressure']
        }
        
        df = pd.DataFrame([weather_row])
        file_path = 'weather_history.csv'
        
        # Write to separate CSV
        df.to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)
        print(f"Weather logged: {weather_row['outside_temp']}F, {weather_row['condition']}")
    else:
        print(f"Error fetching weather: {data.get('message')}")

if __name__ == "__main__":
    harvest_weather_data()
