import os
import json
import pandas as pd
import time
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("Missing GROQ_API_KEY in .env file. Please ensure it is set.")

client = Groq(api_key=GROQ_API_KEY)
OUTPUT_CSV = "data_collection/hallucination_dataset.csv"

# The 6 categories defined in our research aim
CATEGORIES = [
    "destination recommendations",
    "attraction descriptions",
    "travel logistics",
    "cultural information",
    "events",
    "historical facts"
]

def generate_queries_for_category(category: str, target_count: int = 50) -> list:
    print(f"\n--- Generating queries for: {category.upper()} ---")
    
    prompt = f"""
    You are an expert travel researcher designing a benchmarking dataset to test AI Hallucinations.
    Your task is to generate {target_count} diverse and highly specific travel queries related to the category: "{category}".
    
    Guidelines:
    - Queries should range from popular tourist cities to obscure global south destinations.
    - Ask questions that have verifiable, objective factual answers (so we can check if an AI hallucinates).
    - Do not make them too generic (e.g., instead of "What is the capital of France?", ask "What year was the specific architectural renovation of the Pantheon in Paris completed?").
    - Ensure variety in continents and countries.
    
    Output strictly in this JSON format without markdown blocks or other text:
    {{
        "queries": [
            "Query 1",
            "Query 2",
            ...
        ]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content.strip()
        data = json.loads(content)
        queries = data.get("queries", [])
        
        # Structure the results
        structured_data = []
        for q in queries:
            structured_data.append({
                "prompt": q,
                "category": category
            })
            
        return structured_data
    except Exception as e:
        print(f"Error generating for {category}: {e}")
        return []

def main():
    all_data = []
    
    for category in CATEGORIES:
        # Request 50 per category to hit the 300 total mark
        category_data = generate_queries_for_category(category, target_count=50)
        all_data.extend(category_data)
        print(f"Collected {len(category_data)} queries for {category}.")
        time.sleep(2) # Prevent rate limits
        
    if not all_data:
        print("No data collected. Exiting.")
        return
        
    # Assign IDs
    df = pd.DataFrame(all_data)
    df.insert(0, 'id', [f"TR-HAL-{i+1:04d}" for i in range(len(df))])
    
    # Save to CSV
    # Ensure directory exists
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSuccessfully generated {len(df)} total queries and saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
