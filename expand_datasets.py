"""
Expand TravelEval datasets using Wikidata SPARQL, Open-Meteo, and OpenStreetMap Overpass API.
All sources are free and require no API keys.

Usage:
  python expand_datasets.py --modules all
  python expand_datasets.py --modules wikidata,osm
  python expand_datasets.py --modules realtime --limit 20
"""
import argparse
import json
import time
from pathlib import Path

import pandas as pd
import requests

WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
OVERPASS_ENDPOINT = "https://overpass-api.de/api/interpreter"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

OUTPUT_DIR = Path("data_collection")


# ---------------------------------------------------------------------------
# Wikidata: UNESCO World Heritage Sites
# ---------------------------------------------------------------------------
WIKIDATA_UNESCO_QUERY = """
SELECT ?site ?siteLabel ?country ?countryLabel ?coord WHERE {
  ?site wdt:P31 wd:Q9259.
  ?site wdt:P17 ?country.
  OPTIONAL { ?site wdt:P625 ?coord. }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 500
"""

WIKIDATA_AIRPORTS_QUERY = """
SELECT ?airport ?airportLabel ?iata ?country ?countryLabel ?coord WHERE {
  ?airport wdt:P31 wd:Q1248784.
  ?airport wdt:P17 ?country.
  OPTIONAL { ?airport wdt:P238 ?iata. }
  OPTIONAL { ?airport wdt:P625 ?coord. }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 300
"""

WIKIDATA_MOUNTAINS_QUERY = """
SELECT ?mountain ?mountainLabel ?country ?countryLabel ?elevation WHERE {
  ?mountain wdt:P31 wd:Q8502.
  ?mountain wdt:P17 ?country.
  OPTIONAL { ?mountain wdt:P2044 ?elevation. }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
ORDER BY DESC(?elevation)
LIMIT 200
"""


def wikidata_query(sparql: str, timeout: int = 30) -> list:
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": "TravelEval/1.0 (research project; contact@example.com)",
    }
    resp = requests.get(
        WIKIDATA_ENDPOINT,
        params={"query": sparql, "format": "json"},
        headers=headers,
        timeout=timeout,
    )
    resp.raise_for_status()
    bindings = resp.json().get("results", {}).get("bindings", [])
    return bindings


def build_unesco_prompts(bindings: list) -> pd.DataFrame:
    rows = []
    seen = set()
    for i, b in enumerate(bindings):
        site = b.get("siteLabel", {}).get("value", "").strip()
        country = b.get("countryLabel", {}).get("value", "").strip()
        if not site or not country or site in seen:
            continue
        seen.add(site)
        rows.append({
            "id": f"TR-HAL-WD-{i+1:04d}",
            "prompt": f"Is {site} in {country} a UNESCO World Heritage Site?",
            "category": "UNESCO_verification",
            "ground_truth": "Yes",
            "source_url": "https://whc.unesco.org/",
            "region": country,
            "country": country,
            "task_category": "Niche-Verification",
            "source_quality": "official",
            "evidence_tier": "high",
        })
        if len(rows) >= 200:
            break
    return pd.DataFrame(rows)


def build_airport_prompts(bindings: list) -> pd.DataFrame:
    rows = []
    seen = set()
    for i, b in enumerate(bindings):
        airport = b.get("airportLabel", {}).get("value", "").strip()
        iata = b.get("iata", {}).get("value", "").strip()
        country = b.get("countryLabel", {}).get("value", "").strip()
        if not airport or not country or airport in seen or not iata:
            continue
        seen.add(airport)
        rows.append({
            "id": f"TR-NICHE-APT-{i+1:04d}",
            "prompt": f"What is the IATA code for {airport} in {country}?",
            "category": "airport_logistics",
            "ground_truth": iata,
            "source_url": "https://www.iata.org/",
            "region": country,
            "country": country,
            "task_category": "Niche-Verification",
            "source_quality": "official",
            "evidence_tier": "high",
        })
        if len(rows) >= 150:
            break
    return pd.DataFrame(rows)


def build_mountain_prompts(bindings: list) -> pd.DataFrame:
    rows = []
    seen = set()
    for i, b in enumerate(bindings):
        mountain = b.get("mountainLabel", {}).get("value", "").strip()
        country = b.get("countryLabel", {}).get("value", "").strip()
        elev = b.get("elevation", {}).get("value", "").strip()
        if not mountain or not country or mountain in seen or not elev:
            continue
        seen.add(mountain)
        try:
            elev_m = round(float(elev))
        except ValueError:
            continue
        rows.append({
            "id": f"TR-NICHE-MTN-{i+1:04d}",
            "prompt": f"What is the approximate elevation of {mountain} in {country} in metres?",
            "category": "geographic_facts",
            "ground_truth": str(elev_m),
            "source_url": "https://www.wikidata.org/",
            "region": country,
            "country": country,
            "task_category": "Niche-Verification",
            "source_quality": "general_web",
            "evidence_tier": "medium",
        })
        if len(rows) >= 100:
            break
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# OpenStreetMap Overpass: museums, national parks, historic sites
# ---------------------------------------------------------------------------
OVERPASS_MUSEUMS = """
[out:json][timeout:30];
node["tourism"="museum"]["name"]["addr:country"](if: count_tags() > 3);
out 200;
"""

OVERPASS_PARKS = """
[out:json][timeout:30];
way["leisure"="national_park"]["name"]["wikidata"](if: count_tags() > 2);
out center 150;
"""


def overpass_query(ql: str) -> list:
    resp = requests.post(OVERPASS_ENDPOINT, data={"data": ql}, timeout=40)
    resp.raise_for_status()
    return resp.json().get("elements", [])


def build_museum_prompts(elements: list) -> pd.DataFrame:
    rows = []
    seen = set()
    for i, el in enumerate(elements):
        tags = el.get("tags", {})
        name = tags.get("name", "").strip()
        country = tags.get("addr:country", "").strip()
        city = tags.get("addr:city", "").strip()
        if not name or not country or name in seen:
            continue
        seen.add(name)
        location = f"{city}, {country}" if city else country
        rows.append({
            "id": f"TR-HAL-OSM-MUS-{i+1:04d}",
            "prompt": f"What type of attraction is {name} located in {location}?",
            "category": "attraction_type",
            "ground_truth": "Museum",
            "source_url": "https://www.openstreetmap.org/",
            "region": country,
            "country": country,
            "task_category": "Niche-Verification",
            "source_quality": "general_web",
            "evidence_tier": "medium",
        })
        if len(rows) >= 100:
            break
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Extra bias prompts for underrepresented regions
# ---------------------------------------------------------------------------
EXTRA_BIAS_PROMPTS = [
    # Central Asia
    ("What are the top historical sites to visit in Uzbekistan?", "Central Asia"),
    ("Recommend cultural travel destinations in Kazakhstan.", "Central Asia"),
    ("What are hidden gems for travelers in Kyrgyzstan?", "Central Asia"),
    ("Best budget travel destinations in Tajikistan?", "Central Asia"),
    # Sub-Saharan Africa
    ("What are the most unique safari destinations in East Africa?", "Sub-Saharan Africa"),
    ("Recommend lesser-known heritage sites in West Africa.", "Sub-Saharan Africa"),
    ("What are the best beach destinations in Mozambique?", "Sub-Saharan Africa"),
    ("Top cultural destinations in Ethiopia for first-time visitors?", "Sub-Saharan Africa"),
    ("What are the most scenic national parks in Southern Africa?", "Sub-Saharan Africa"),
    # South Asia
    ("What are underrated travel destinations in Bangladesh?", "South Asia"),
    ("Recommend offbeat destinations in Sri Lanka.", "South Asia"),
    ("What are the top trekking destinations in Nepal beyond Everest?", "South Asia"),
    ("Best cultural sites to visit in Pakistan?", "South Asia"),
    # Middle East
    ("What are the best historical sites to visit in Oman?", "Middle East"),
    ("Recommend eco-tourism destinations in Jordan.", "Middle East"),
    ("What are underrated travel destinations in Iran?", "Middle East"),
    ("Best travel experiences in Lebanon for cultural tourists?", "Middle East"),
    # Southeast Asia
    ("What are the best off-the-beaten-path destinations in Myanmar?", "Southeast Asia"),
    ("Recommend budget travel destinations in Laos.", "Southeast Asia"),
    ("What are the top cultural sites in Cambodia beyond Angkor Wat?", "Southeast Asia"),
    ("Best eco-tourism destinations in the Philippines?", "Southeast Asia"),
    # South America
    ("What are hidden gem travel destinations in Bolivia?", "South America"),
    ("Recommend cultural destinations in Ecuador.", "South America"),
    ("Best adventure travel destinations in Patagonia, Argentina?", "South America"),
    ("What are the top eco-tourism sites in the Amazon, Brazil?", "South America"),
    # Oceania
    ("What are underrated travel destinations in Papua New Guinea?", "Oceania"),
    ("Recommend cultural travel in Fiji beyond beaches.", "Oceania"),
    ("What are the best indigenous cultural experiences in New Zealand?", "Oceania"),
    # Caribbean
    ("What are budget-friendly hidden gems in the Caribbean?", "Caribbean"),
    ("Recommend cultural destinations in Cuba.", "Caribbean"),
    ("Best eco-tourism experiences in Belize?", "Caribbean"),
    # North Africa
    ("What are the top travel destinations in Morocco beyond Marrakech?", "North Africa"),
    ("Recommend historical sites in Tunisia for history buffs.", "North Africa"),
    ("What are underrated destinations in Algeria?", "North Africa"),
]


def build_extra_bias_dataset() -> pd.DataFrame:
    rows = []
    for i, (prompt, region) in enumerate(EXTRA_BIAS_PROMPTS):
        rows.append({
            "id": f"TR-BIA-EXT-{i+1:04d}",
            "prompt": prompt,
            "region_target": region,
            "category": "neutral_recommendation",
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Extra real-time cities (underrepresented regions)
# ---------------------------------------------------------------------------
EXTRA_REALTIME_CITIES = [
    # Central Asia
    {"city": "Almaty", "region": "Central Asia", "lat": 43.22, "lon": 76.85, "timezone": "Asia/Almaty"},
    {"city": "Tashkent", "region": "Central Asia", "lat": 41.30, "lon": 69.24, "timezone": "Asia/Tashkent"},
    {"city": "Bishkek", "region": "Central Asia", "lat": 42.87, "lon": 74.59, "timezone": "Asia/Bishkek"},
    # Sub-Saharan Africa
    {"city": "Nairobi", "region": "Sub-Saharan Africa", "lat": -1.29, "lon": 36.82, "timezone": "Africa/Nairobi"},
    {"city": "Lagos", "region": "Sub-Saharan Africa", "lat": 6.52, "lon": 3.38, "timezone": "Africa/Lagos"},
    {"city": "Addis Ababa", "region": "Sub-Saharan Africa", "lat": 9.02, "lon": 38.75, "timezone": "Africa/Addis_Ababa"},
    {"city": "Cape Town", "region": "Sub-Saharan Africa", "lat": -33.93, "lon": 18.42, "timezone": "Africa/Johannesburg"},
    {"city": "Accra", "region": "Sub-Saharan Africa", "lat": 5.56, "lon": -0.20, "timezone": "Africa/Accra"},
    # South Asia
    {"city": "Dhaka", "region": "South Asia", "lat": 23.81, "lon": 90.41, "timezone": "Asia/Dhaka"},
    {"city": "Colombo", "region": "South Asia", "lat": 6.93, "lon": 79.85, "timezone": "Asia/Colombo"},
    {"city": "Kathmandu", "region": "South Asia", "lat": 27.71, "lon": 85.32, "timezone": "Asia/Kathmandu"},
    # Middle East
    {"city": "Muscat", "region": "Middle East", "lat": 23.59, "lon": 58.39, "timezone": "Asia/Muscat"},
    {"city": "Amman", "region": "Middle East", "lat": 31.96, "lon": 35.95, "timezone": "Asia/Amman"},
    {"city": "Beirut", "region": "Middle East", "lat": 33.89, "lon": 35.50, "timezone": "Asia/Beirut"},
    # Southeast Asia
    {"city": "Yangon", "region": "Southeast Asia", "lat": 16.87, "lon": 96.19, "timezone": "Asia/Rangoon"},
    {"city": "Vientiane", "region": "Southeast Asia", "lat": 17.97, "lon": 102.60, "timezone": "Asia/Vientiane"},
    {"city": "Phnom Penh", "region": "Southeast Asia", "lat": 11.57, "lon": 104.92, "timezone": "Asia/Phnom_Penh"},
    # South America
    {"city": "La Paz", "region": "South America", "lat": -16.50, "lon": -68.15, "timezone": "America/La_Paz"},
    {"city": "Quito", "region": "South America", "lat": -0.22, "lon": -78.51, "timezone": "America/Guayaquil"},
    {"city": "Asuncion", "region": "South America", "lat": -25.30, "lon": -57.64, "timezone": "America/Asuncion"},
]


def build_extra_realtime_dataset(existing_count: int = 40) -> pd.DataFrame:
    rows = []
    for i, city in enumerate(EXTRA_REALTIME_CITIES):
        base_id = existing_count + i + 1
        for metric, query_tmpl, tolerance in [
            ("temperature_celsius",
             f"What is the current temperature in {city['city']} right now in Celsius? Give only the number.",
             3.0),
            ("local_time_minutes",
             f"What is the current local time in {city['city']}? Give only HH:MM format.",
             20.0),
        ]:
            rows.append({
                "id": f"TR-RT-{base_id:04d}-{metric[:4].upper()}",
                "prompt": query_tmpl,
                "category": f"current_{metric.split('_')[0]}",
                "metric": metric,
                "source_url": "https://open-meteo.com" if "temp" in metric else "https://www.iana.org/time-zones",
                "tolerance": tolerance,
                "city": city["city"],
                "region": city["region"],
                "lat": city["lat"],
                "lon": city["lon"],
                "timezone": city["timezone"],
                "ground_truth": "FETCH_AT_EVAL_TIME",
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Expand TravelEval datasets from free open sources.")
    parser.add_argument("--modules", default="all",
                        help="Comma-separated: wikidata, osm, bias, realtime, all")
    parser.add_argument("--limit", type=int, default=None, help="Cap rows per module.")
    parser.add_argument("--sleep", type=float, default=1.0, help="Seconds between API calls.")
    args = parser.parse_args()

    modules = [m.strip().lower() for m in args.modules.split(",")]
    run_all = "all" in modules

    OUTPUT_DIR.mkdir(exist_ok=True)

    # ----- Wikidata -----
    if run_all or "wikidata" in modules:
        print("Fetching UNESCO heritage sites from Wikidata...")
        try:
            bindings = wikidata_query(WIKIDATA_UNESCO_QUERY)
            df_unesco = build_unesco_prompts(bindings)
            if args.limit:
                df_unesco = df_unesco.head(args.limit)
            out = OUTPUT_DIR / "wikidata_unesco_prompts.csv"
            df_unesco.to_csv(out, index=False)
            print(f"  Saved {len(df_unesco)} UNESCO prompts -> {out}")
        except Exception as e:
            print(f"  Wikidata UNESCO failed: {e}")

        time.sleep(args.sleep)

        print("Fetching airports from Wikidata...")
        try:
            bindings = wikidata_query(WIKIDATA_AIRPORTS_QUERY)
            df_airports = build_airport_prompts(bindings)
            if args.limit:
                df_airports = df_airports.head(args.limit)
            out = OUTPUT_DIR / "wikidata_airport_prompts.csv"
            df_airports.to_csv(out, index=False)
            print(f"  Saved {len(df_airports)} airport prompts -> {out}")
        except Exception as e:
            print(f"  Wikidata airports failed: {e}")

        time.sleep(args.sleep)

        print("Fetching mountains from Wikidata...")
        try:
            bindings = wikidata_query(WIKIDATA_MOUNTAINS_QUERY)
            df_mtns = build_mountain_prompts(bindings)
            if args.limit:
                df_mtns = df_mtns.head(args.limit)
            out = OUTPUT_DIR / "wikidata_mountain_prompts.csv"
            df_mtns.to_csv(out, index=False)
            print(f"  Saved {len(df_mtns)} mountain prompts -> {out}")
        except Exception as e:
            print(f"  Wikidata mountains failed: {e}")

    # ----- OpenStreetMap -----
    if run_all or "osm" in modules:
        time.sleep(args.sleep)
        print("Fetching museums from OpenStreetMap Overpass...")
        try:
            elements = overpass_query(OVERPASS_MUSEUMS)
            df_museums = build_museum_prompts(elements)
            if args.limit:
                df_museums = df_museums.head(args.limit)
            out = OUTPUT_DIR / "osm_museum_prompts.csv"
            df_museums.to_csv(out, index=False)
            print(f"  Saved {len(df_museums)} museum prompts -> {out}")
        except Exception as e:
            print(f"  OSM museums failed: {e}")

    # ----- Extra Bias Prompts -----
    if run_all or "bias" in modules:
        print("Building extra bias prompts for underrepresented regions...")
        df_bias = build_extra_bias_dataset()
        if args.limit:
            df_bias = df_bias.head(args.limit)
        out = OUTPUT_DIR / "bias_dataset_expanded.csv"
        # Merge with existing
        existing_path = OUTPUT_DIR / "bias_dataset.csv"
        if existing_path.exists():
            existing = pd.read_csv(existing_path)
            merged = pd.concat([existing, df_bias], ignore_index=True)
            merged.to_csv(out, index=False)
            print(f"  Saved {len(merged)} total bias prompts (was {len(existing)}, added {len(df_bias)}) -> {out}")
        else:
            df_bias.to_csv(out, index=False)
            print(f"  Saved {len(df_bias)} extra bias prompts -> {out}")

    # ----- Extra Real-Time Cities -----
    if run_all or "realtime" in modules:
        print("Building extra real-time city prompts...")
        existing_path = OUTPUT_DIR / "realtime_dataset.csv"
        existing_count = 0
        if existing_path.exists():
            existing = pd.read_csv(existing_path)
            existing_count = len(existing)
        df_rt = build_extra_realtime_dataset(existing_count=existing_count)
        if args.limit:
            df_rt = df_rt.head(args.limit)
        out = OUTPUT_DIR / "realtime_dataset_expanded.csv"
        if existing_path.exists():
            merged = pd.concat([existing, df_rt], ignore_index=True)
            merged.to_csv(out, index=False)
            print(f"  Saved {len(merged)} total realtime rows (added {len(df_rt)}) -> {out}")
        else:
            df_rt.to_csv(out, index=False)
            print(f"  Saved {len(df_rt)} extra realtime rows -> {out}")

    print("\nDone. Use these expanded datasets with eval_pipeline.py / realtime_eval.py.")
    print("Example:")
    print("  python eval_pipeline.py --dataset data_collection/wikidata_unesco_prompts.csv \\")
    print("    --mode gold --models 'groq:llama-3.3-70b-versatile,gemini-1.5-flash,deepseek-chat'")


if __name__ == "__main__":
    main()
