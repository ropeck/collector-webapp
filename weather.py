import requests
from datetime import datetime
import os
import pytz

def fetch_weather(api_key, city_id):
    url = f"http://api.openweathermap.org/data/2.5/forecast?id={city_id}&appid={api_key}&units=imperial"
    response = requests.get(url)
    data = response.json()
    # Get today's date in the local timezone
    local_tz = pytz.timezone('America/Los_Angeles')
    today = datetime.now(local_tz).date()

    # Find the forecast for today
    for entry in data['list']:
        forecast_time = datetime.fromtimestamp(entry['dt'], local_tz)
        if forecast_time.date() == today:
            temp = entry['main']['temp']
            temp_min = entry['main']['temp_min']
            temp_max = entry['main']['temp_max']
            description = entry['weather'][0]['description'].capitalize()
            return f"Aptos Weather: {description}, {temp:.0f}°F ({temp_min:.0f}/{temp_max:.0f})"

    return "Weather data not available."


def fetch_aptos_weather():
    global file
    API_KEY = os.getenv("OPENWEATHERMAP_API_KEY", None)
    if API_KEY is None:
        raise ValueError("set OPENWEATHERMAP_API_KEY environment variable")
    CITY_ID = '5325111'  # City ID for Aptos, California
    weather_text = fetch_weather(API_KEY, CITY_ID)
    with open('weather.txt', 'w') as file:
        file.write(weather_text)


if __name__ == "__main__":
    fetch_aptos_weather()
