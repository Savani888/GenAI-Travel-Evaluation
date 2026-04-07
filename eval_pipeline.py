import pandas as pd
import numpy as np
import time
import requests
import json
from typing import List, Dict, Optional
from textblob import TextBlob # Sentiment
from sklearn.metrics.pairwise import cosine_similarity
import re

# Mocking API calls for demonstration
def call_llm(prompt: str, model: str = "gpt-4") -> str:
    """Mock LLM response for demonstration."""
    return f"This is a response about {prompt[:50]}..."

def extract_claims(response: str) -> List[str]:
    """Uses NLTK or an LLM to segment response into atomic claims."""
    # Implementation: Use spacy or another LLM prompt to split into sentences
    sentences = response.split(". ") 
    return [s.strip() for s in sentences if len(s) > 10]

def verify_claim(claim: str) -> bool:
    """Cross-references claim with Google Search or a Knowledge Base."""
    # Implementation: Call serpapi and use a judge LLM to compare search results with claim
    return np.random.choice([True, False], p=[0.7, 0.3]) # Mocked

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
            print("Dataset is empty. Run generate_dataset.py first.")
            return

        print(f"Running evaluation for {model_name}...")
        for index, row in self.dataset.iterrows():
            prompt = row['prompt']
            response = call_llm(prompt, model=model_name)
            
            # Hallucination Evaluation (Mocked for demonstration)
            claims = extract_claims(response)
            verified_counts = [verify_claim(c) for c in claims]
            hallucination_rate = 1 - (sum(verified_counts) / len(claims)) if claims else 0
            
            # Bias Evaluation
            sentiment = TextBlob(response).sentiment.polarity 
            
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
        
        # 1. Hallucination by Region
        hallucination_by_region = df.groupby('region')['hallucination_rate'].mean()
        
        # 2. Sentiment by Region (Exposure Bias)
        sentiment_by_region = df.groupby('region')['sentiment_score'].mean()
        
        # 3. Task Category Variance
        task_hallucination = df.groupby('task')['hallucination_rate'].mean()
        
        summary = {
            "Total Processed": len(df),
            "Hallucination by Region": hallucination_by_region.to_dict(),
            "Sentiment by Region": sentiment_by_region.to_dict(),
            "Task Hallucination Profile": task_hallucination.to_dict()
        }
        return summary

if __name__ == "__main__":
    import os
    
    # 1. Initialize pipeline
    dataset_file = "travel_benchmark.csv"
    if not os.path.exists(dataset_file):
        print(f"Dataset {dataset_file} not found. Ensure generate_dataset.py ran successfully.")
    else:
        pipeline = TravelEvalPipeline(dataset_file)
        
        # 2. Execute Models
        pipeline.run_eval("Model-X-Standard")
        pipeline.run_eval("Model-Y-Enhanced")
        
        # 3. Analyze Results
        metrics = pipeline.compute_summary_metrics()
        print("\n--- TRAVEL EVAL SUMMARY ---")
        print(json.dumps(metrics, indent=2))
        
        # 4. Export results
        pd.DataFrame(pipeline.results).to_csv("eval_results.csv", index=False)
        print("\nFull results exported to eval_results.csv")
