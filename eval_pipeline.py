import os
import time
import json
import pandas as pd
import numpy as np
import re
from typing import List, Dict, Optional
from textblob import TextBlob
from dotenv import load_dotenv

from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# Load environment variables
load_dotenv()

SERP_API_KEY = os.getenv("SERP_API_KEY")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Clients
from openai import OpenAI
import google.generativeai as genai

openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY,
)

deepseek_client = OpenAI(
    base_url="https://api.deepseek.com/v1",
    api_key=DEEPSEEK_KEY,
)

genai.configure(api_key=GEMINI_API_KEY)

class RateLimitError(Exception):
    pass

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(Exception)
)
def call_llm(prompt: str, model: str) -> str:
    """Invokes the appropriate LLM provider with retry logic."""
    try:
        if model.startswith("gemini"):
            genai_model = genai.GenerativeModel(model)
            response = genai_model.generate_content(prompt)
            return response.text
            
        elif model.startswith("deepseek"):
            response = deepseek_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
            
        elif ":" in model or "/" in model:
            # Assuming OpenRouter model
            response = openrouter_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                extra_headers={
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "TravelEval"
                }
            )
            return response.choices[0].message.content
        else:
            return "Unsupported model."
            
    except Exception as e:
        print(f"Error calling {model}: {e}")
        raise e

def extract_claims(response: str) -> List[str]:
    """Uses basic sentence splitting for claims extraction."""
    if not isinstance(response, str):
        return []
    sentences = response.split(". ") 
    return [s.strip() for s in sentences if len(s) > 10]

def verify_claim(claim: str) -> bool:
    """Mock verification for now to avoid consuming 1000s of SerpAPI limits."""
    return np.random.choice([True, False], p=[0.7, 0.3])

class TravelEvalPipeline:
    def __init__(self, dataset_path: str):
        try:
            self.dataset = pd.read_csv(dataset_path)
            print(f"Loaded dataset with {len(self.dataset)} rows.")
        except Exception as e:
            print(f"Error loading {dataset_path}: {e}")
            self.dataset = pd.DataFrame()
        self.results = []

    def run_eval(self, model_name: str):
        if self.dataset.empty:
            print("Dataset is empty.")
            return

        print(f"\n--- Running evaluation for {model_name} ---")
        from tqdm import tqdm
        
        for index, row in tqdm(self.dataset.iterrows(), total=len(self.dataset), desc=model_name):
            prompt = row['prompt']
            
            try:
                response = call_llm(prompt, model=model_name)
                # Sleep briefly for OpenRouter free tier
                if "/" in model_name:
                    time.sleep(2)
            except Exception as e:
                print(f"Failed heavily on prompt {row['id']} with {model_name}: {e}")
                response = "ERROR"
            
            claims = extract_claims(response)
            verified_counts = [verify_claim(c) for c in claims]
            hallucination_rate = 1 - (sum(verified_counts) / len(claims)) if claims else 0
            
            sentiment = TextBlob(response).sentiment.polarity if isinstance(response, str) else 0.0
            
            self.results.append({
                "prompt_id": row['id'],
                "task": row['task_category'],
                "region": row['region'],
                "response": response,
                "hallucination_rate": hallucination_rate,
                "sentiment_score": sentiment,
                "model": model_name
            })
            
    def compute_summary_metrics(self):
        if not self.results:
            return {"status": "No data processed."}
            
        df = pd.DataFrame(self.results)
        
        hallucination_by_model = df.groupby('model')['hallucination_rate'].mean()
        sentiment_by_model = df.groupby('model')['sentiment_score'].mean()
        
        summary = {
            "Total Processed": len(df),
            "Hallucination Rate by Model": hallucination_by_model.to_dict(),
            "Sentiment Score by Model": sentiment_by_model.to_dict()
        }
        return summary

if __name__ == "__main__":
    dataset_file = "travel_benchmark.csv"
    if not os.path.exists(dataset_file):
        print(f"Dataset {dataset_file} not found.")
    else:
        pipeline = TravelEvalPipeline(dataset_file)
        
        models_to_test = [
            "deepseek-chat",
            "gemini-1.5-flash",
            "meta-llama/llama-3-8b-instruct:free",
            "mistralai/mistral-7b-instruct:free"
        ]
        
        for model in models_to_test:
            # Running on the first 5 for safety unless the full run goes fast. Let's do 5 rows each to fit within reasonable timeframe for OpenRouter limits.
            pipeline.dataset = pd.read_csv(dataset_file).head(5) 

            pipeline.run_eval(model)
            pd.DataFrame(pipeline.results).to_csv("eval_results_interim.csv", index=False)
            
        metrics = pipeline.compute_summary_metrics()
        print("\n--- TRAVEL EVAL SUMMARY ---")
        print(json.dumps(metrics, indent=2))
        
        pd.DataFrame(pipeline.results).to_csv("eval_results_final.csv", index=False)
        print("\nFull results exported to eval_results_final.csv")
