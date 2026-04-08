import os
import pandas as pd
import requests
import json
import time

OUTPUT_CSV = "data_collection/realtime_dataset.csv"

# Using open-meteo for weather and some mocked/fixed formats for events/transport
# We will primarily focus on weather as it's purely factual and real-time without needing a paid API.

CITIES = [
    {"name": "London", "lat": 51.5074, "lon": -0.1278},
    {"name": "Tokyo", "lat": 35.6762, "lon": 139.6503},
    {"name": "Nairobi", "lat": -1.2921, "lon": 36.8219},
    {"name": "Buenos Aires", "lat": -34.6037, "lon": -58.3816},
    {"name": "Reykjavik", "lat": 64.1466, "lon": -21.9426},
    {"name": "Sydney", "lat": -33.8688, "lon": 151.2093},
    {"name": "Cairo", "lat": 30.0444, "lon": 31.2357},
    {"name": "New York", "lat": 40.7128, "lon": -74.0060},
    {"name": "Mumbai", "lat": 19.0760, "lon": 72.8777},
    {"name": "Cape Town", "lat": -33.9249, "lon": 18.4241}
]

def fetch_current_temperature(lat: float, lon: float) -> str:
    # Open-Meteo API doesn't require keys
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            temp = data['current_weather']['temperature']
            return f"{temp} °C"
    except Exception as e:
        print(f"Error fetching weather: {e}")
    return "Unknown"

def main():
    print("Generating Real-Time queries for Module 3...")
    data = []
    
    prompt_id = 1
    
    for city in CITIES:
        print(f"Fetching ground truth weather for {city['name']}...")
        temp = fetch_current_temperature(city['lat'], city['lon'])
        
        # Weather Query
        data.append({
            "id": f"TR-RT-{prompt_id:04d}",
            "prompt": f"What is the current temperature in {city['name']} in Celsius?",
            "category": "current weather",
            "city": city['name'],
            "ground_truth": temp
        })
        prompt_id += 1
        
        # We can also add time zone queries
        data.append({
            "id": f"TR-RT-{prompt_id:04d}",
            "prompt": f"What is the current local time in {city['name']}?",
            "category": "current time",
            "city": city['name'],
            "ground_truth": "Dynamic Time Evaluation needed"
        })
        prompt_id += 1
        
        time.sleep(1) # Be polite to APIs
        
    df = pd.DataFrame(data)
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Successfully generated {len(df)} real-time queries and saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
