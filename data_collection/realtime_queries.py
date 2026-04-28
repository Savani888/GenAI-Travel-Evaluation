import os
from pathlib import Path

import pandas as pd


OUTPUT_CSV = "data_collection/realtime_dataset.csv"


CITIES = [
    {"name": "London", "region": "Europe", "lat": 51.5074, "lon": -0.1278, "timezone": "Europe/London"},
    {"name": "Paris", "region": "Europe", "lat": 48.8566, "lon": 2.3522, "timezone": "Europe/Paris"},
    {"name": "Reykjavik", "region": "Europe", "lat": 64.1466, "lon": -21.9426, "timezone": "Atlantic/Reykjavik"},
    {"name": "Tokyo", "region": "Asia", "lat": 35.6762, "lon": 139.6503, "timezone": "Asia/Tokyo"},
    {"name": "Seoul", "region": "Asia", "lat": 37.5665, "lon": 126.9780, "timezone": "Asia/Seoul"},
    {"name": "Mumbai", "region": "South Asia", "lat": 19.0760, "lon": 72.8777, "timezone": "Asia/Kolkata"},
    {"name": "Kathmandu", "region": "South Asia", "lat": 27.7172, "lon": 85.3240, "timezone": "Asia/Kathmandu"},
    {"name": "Dubai", "region": "Middle East", "lat": 25.2048, "lon": 55.2708, "timezone": "Asia/Dubai"},
    {"name": "Amman", "region": "Middle East", "lat": 31.9539, "lon": 35.9106, "timezone": "Asia/Amman"},
    {"name": "Nairobi", "region": "Africa", "lat": -1.2921, "lon": 36.8219, "timezone": "Africa/Nairobi"},
    {"name": "Cape Town", "region": "Africa", "lat": -33.9249, "lon": 18.4241, "timezone": "Africa/Johannesburg"},
    {"name": "Marrakesh", "region": "Africa", "lat": 31.6295, "lon": -7.9811, "timezone": "Africa/Casablanca"},
    {"name": "New York", "region": "North America", "lat": 40.7128, "lon": -74.0060, "timezone": "America/New_York"},
    {"name": "Mexico City", "region": "North America", "lat": 19.4326, "lon": -99.1332, "timezone": "America/Mexico_City"},
    {"name": "Vancouver", "region": "North America", "lat": 49.2827, "lon": -123.1207, "timezone": "America/Vancouver"},
    {"name": "Buenos Aires", "region": "South America", "lat": -34.6037, "lon": -58.3816, "timezone": "America/Argentina/Buenos_Aires"},
    {"name": "Lima", "region": "South America", "lat": -12.0464, "lon": -77.0428, "timezone": "America/Lima"},
    {"name": "La Paz", "region": "South America", "lat": -16.4897, "lon": -68.1193, "timezone": "America/La_Paz"},
    {"name": "Sydney", "region": "Oceania", "lat": -33.8688, "lon": 151.2093, "timezone": "Australia/Sydney"},
    {"name": "Auckland", "region": "Oceania", "lat": -36.8509, "lon": 174.7645, "timezone": "Pacific/Auckland"},
]


def main() -> None:
    print("Generating real-time benchmark prompts.")
    rows = []
    prompt_id = 1
    for city in CITIES:
        base = {
            "city": city["name"],
            "region": city["region"],
            "lat": city["lat"],
            "lon": city["lon"],
            "timezone": city["timezone"],
            "ground_truth": "FETCH_AT_EVAL_TIME",
        }
        rows.append(
            {
                "id": f"TR-RT-{prompt_id:04d}",
                "prompt": f"What is the current temperature in {city['name']} in Celsius?",
                "category": "current_weather",
                "metric": "temperature_celsius",
                "source_url": "https://open-meteo.com/",
                "tolerance": 3.0,
                **base,
            }
        )
        prompt_id += 1
        rows.append(
            {
                "id": f"TR-RT-{prompt_id:04d}",
                "prompt": f"What is the current local time in {city['name']}?",
                "category": "current_time",
                "metric": "local_time_minutes",
                "source_url": "IANA time zone database via Python zoneinfo",
                "tolerance": 20.0,
                **base,
            }
        )
        prompt_id += 1

    output = Path(OUTPUT_CSV)
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output, index=False)
    print(f"Successfully generated {len(rows)} rows and saved to {output}.")


if __name__ == "__main__":
    main()
