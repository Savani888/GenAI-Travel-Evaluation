import os
import json
import time
import pandas as pd
from dotenv import load_dotenv
from serpapi import GoogleSearch
from groq import Groq

load_dotenv()
SERP_API_KEY = os.getenv("SERP_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not SERP_API_KEY or not GROQ_API_KEY:
    raise ValueError("Missing API Keys in .env file")

client = Groq(api_key=GROQ_API_KEY)
DATA_OUTPUT = "travel_benchmark_niche.csv"

# Target regions and countries to ensure global coverage
TARGETS = [
    {"region": "Central Asia", "points": ["Kyrgyzstan", "Tajikistan", "Uzbekistan", "Turkmenistan", "Kazakhstan"]},
    {"region": "Sub-Saharan Africa", "points": ["Namibia", "Botswana", "Zambia", "Zimbabwe", "DR Congo", "Mali", "Senegal", "Ethiopia", "Rwanda", "Uganda"]},
    {"region": "Southeast Asia", "points": ["Laos", "Cambodia", "Myanmar", "Vietnam", "Indonesia", "Philippines", "Timor-Leste"]},
    {"region": "South America", "points": ["Bolivia", "Paraguay", "Ecuador", "Guyana", "Suriname", "Colombia", "Peru"]},
    {"region": "Middle East", "points": ["Oman", "Jordan", "Lebanon", "Yemen", "Iraq", "Saudi Arabia"]},
    {"region": "Oceania", "points": ["Vanuatu", "Solomon Islands", "Papua New Guinea", "Fiji", "Samoa", "Tonga"]},
    {"region": "Caribbean & CA", "points": ["Belize", "Nicaragua", "Honduras", "El Salvador", "Guatemala", "Cuba", "Haiti"]},
    {"region": "South Asia", "points": ["Bhutan", "Nepal", "Bangladesh", "Sri Lanka", "Maldives"]},
    {"region": "North Africa", "points": ["Morocco", "Algeria", "Tunisia", "Libya", "Egypt"]}
]

# Diverse query templates
QUERY_TEMPLATES = [
    "recent unexpected visa changes land border crossing rules {country} 2025 2026",
    "obscure local laws tourist bans weird fines {country} 2025 2026",
    "hidden scams transportation restrictions permits {country} 2025 2026",
    "currency restrictions cash requirements payment bans {country} 2025 2026"
]

def get_serp_snippets(query: str, num_results: int = 5) -> str:
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERP_API_KEY,
        "num": num_results
    }
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
    except Exception as e:
        print(f"SerpAPI Error: {e}")
        return ""
    
    snippets = []
    if "organic_results" in results:
        for result in results["organic_results"]:
            snippets.append(f"Source: {result.get('link')} | Snippet: {result.get('snippet')}")
            
    return "\n".join(snippets)

def extract_niche_facts(snippets: str, region: str, country: str) -> list:
    if not snippets.strip():
        return []
        
    prompt = f"""
    You are an expert travel researcher gathering data for an LLM benchmarking dataset. 
    Analyze the following search snippets and extract distinct, highly niche, hard-to-know, and verifiable travel facts (e.g. obscure laws, strict border rules, hidden transit fines, weird permit requirements).
    
    Context Region: {region}
    Context Country: {country}
    Snippets:
    {snippets}
    
    Output a JSON object with the following schema:
    {{
        "facts": [
            {{
                "prompt": "Create a user-like tricky geographical or legal question based on the fact.",
                "ground_truth": "The accurate, verifiable answer",
                "source_url": "The source url from the snippet supporting this"
            }}
        ]
    }}
    IMPORTANT: Only output the raw JSON object. Do not duplicate facts.
    """
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content.strip()
        data = json.loads(content)
        return data.get("facts", [])
    except Exception as e:
        print(f"Error extracting facts: {e}")
        return []

def main():
    print("Initializing Niche Dataset Scaler...")
    
    # Load existing dataset to prevent duplicates
    existing_prompts = set()
    if os.path.exists(DATA_OUTPUT):
        df_existing = pd.read_csv(DATA_OUTPUT)
        dataset = df_existing.to_dict('records')
        existing_prompts = set(df_existing['prompt'].tolist())
        print(f"Loaded existing dataset with {len(dataset)} entries.")
    else:
        dataset = []

    target_count = 350
    consecutive_errors = 0

    # Generator Loop
    for target in TARGETS:
        region = target["region"]
        for country in target["points"]:
            for template in QUERY_TEMPLATES:
                if len(dataset) >= target_count:
                    print(f"\nReached target limit of {target_count}. Stopping.")
                    return

                query = template.format(country=country)
                print(f"[{len(dataset)}/{target_count}] ({country}) -> {query[:60]}...")
                
                snippets = get_serp_snippets(query, num_results=4)
                extracted_facts = extract_niche_facts(snippets, region, country)
                
                added = 0
                for fact in extracted_facts:
                    # Deduplication check
                    if fact['prompt'] not in existing_prompts:
                        fact['region'] = region
                        fact['country'] = country
                        fact['id'] = f"TR-NICHE-{len(dataset)+1:04d}"
                        fact['category'] = "Niche-Verification"
                        dataset.append(fact)
                        existing_prompts.add(fact['prompt'])
                        added += 1
                
                print(f"  + Added {added} unique prompts.")
                
                if added == 0:
                    consecutive_errors += 1
                else:
                    consecutive_errors = 0
                    
                # Save aggressively to avoid data loss
                df = pd.DataFrame(dataset)
                try:
                    df.to_csv(DATA_OUTPUT, index=False)
                except PermissionError:
                    backup_file = DATA_OUTPUT.replace('.csv', '_backup.csv')
                    df.to_csv(backup_file, index=False)
                    print(f"File locked, saved backup to {backup_file}")
                
                # Protect rate limits (Groq allows ~30 RPM usually, SerpAPI mostly unlimited until cap)
                time.sleep(3)
                
                # Safety break
                if consecutive_errors > 15:
                    print("Too many consecutive zero-fact generations or rate limits. Halting early.")
                    return

    print(f"\nCompleted run! Total unique prompts: {len(dataset)}")

if __name__ == "__main__":
    main()
