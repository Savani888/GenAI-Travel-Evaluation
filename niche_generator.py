import os
import json
import time
import pandas as pd
from dotenv import load_dotenv
from serpapi import GoogleSearch
from groq import Groq

# Load environment variables
load_dotenv()
SERP_API_KEY = os.getenv("SERP_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not SERP_API_KEY or not GROQ_API_KEY:
    raise ValueError("Missing API Keys in .env file")

client = Groq(api_key=GROQ_API_KEY)

# Define niches
NICHES = [
    {"region": "Central Asia", "query": "recent visa changes Kyrgyzstan land border crossing requirements 2026"},
    {"region": "Sub-Saharan Africa", "query": "obscure local laws or bans tourists Namibia Botswana 2026"},
    {"region": "Southeast Asia", "query": "scams tourists strict unexpected transportation fines Vietnam Indonesia 2026"},
    {"region": "South America", "query": "hiking permits currency restrictions Patagonia strict trails 2026"},
    {"region": "Middle East", "query": "specific cultural offenses dual passport border crossing issues Oman Jordan 2026"}
]

DATA_OUTPUT = "travel_benchmark_niche.csv"

def get_serp_snippets(query: str, num_results: int = 5) -> str:
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERP_API_KEY,
        "num": num_results
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    
    snippets = []
    if "organic_results" in results:
        for result in results["organic_results"]:
            snippets.append(f"Source: {result.get('link')} | Snippet: {result.get('snippet')}")
            
    return "\n".join(snippets)

def extract_niche_facts(snippets: str, region: str) -> list:
    prompt = f"""
    You are an expert travel researcher gathering data for an LLM benchmarking dataset. 
    Analyze the following search snippets and extract distinct, highly niche, hard-to-know, and verifiable travel facts (e.g. obscure laws, strict border rules, hidden transit fines, weird permit requirements).
    
    Context Region: {region}
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
    IMPORTANT: Only output the raw JSON object.
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
        import traceback
        print(f"Error extracting facts: {e}")
        traceback.print_exc()
        if 'content' in locals():
            print(f"Raw output: {content}")
        return []

def main():
    print("Initializing Niche Dataset Generator...")
    dataset = []
    
    # Process queries in a batch
    for niche in NICHES:
        print(f"\nSearching SerpAPI for: {niche['query']}")
        snippets = get_serp_snippets(niche['query'])
        
        print(f"Extracting facts using Groq for region: {niche['region']}...")
        extracted_facts = extract_niche_facts(snippets, niche['region'])
        
        for fact in extracted_facts:
            fact['region'] = niche['region']
            fact['id'] = f"TR-NICHE-{len(dataset)+1:03d}"
            fact['category'] = "Niche-Verification"
            dataset.append(fact)
            print(f"  + Added Prompt: {fact['prompt'][:50]}...")
            
        # Rate limit compliance
        time.sleep(2)
        
    print(f"\nGenerated {len(dataset)} niche prompts in initial batch.")
    
    # Save partial dataset
    if dataset:
        df = pd.DataFrame(dataset)
        df.to_csv(DATA_OUTPUT, index=False)
        print(f"Saved to {DATA_OUTPUT}")
    else:
        print("No facts generated. Check API connections.")

if __name__ == "__main__":
    main()
