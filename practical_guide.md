# Practical Implementation Guide: TravelEval

This guide provides the exact steps to implement and run the TravelEval framework. 

## 1. Environment Setup

```bash
# 1. Create a virtual environment
python -m venv venv
source venv/bin/activate  # venv\Scripts\activate on Windows

# 2. Install dependencies
pip install pandas numpy textblob spacy scikit-learn openai google-generativeai requests
python -m spacy download en_core_web_sm
```

## 2. Generating the Dataset

Use the following Python snippet to generate a small seed dataset (100 prompts) using templates.

```python
import pandas as pd
import random

destinations = [
    {"name": "Nairobi, Kenya", "region": "Global-South"},
    {"name": "Kyoto, Japan", "region": "Global-North"},
    {"name": "Tbilisi, Georgia", "region": "Global-South"},
    {"name": "Reykjavik, Iceland", "region": "Global-North"},
    {"name": "Windhoek, Namibia", "region": "Global-South"}
]

tasks = ["Fact-Retrieval", "Generative", "Safety"]
data = []

for i in range(100):
    dest = random.choice(destinations)
    task = random.choice(tasks)
    
    if task == "Fact-Retrieval":
        prompt = f"What is the average flight distance from London to {dest['name']}?"
    elif task == "Generative":
        prompt = f"Plan a 2-day budget-friendly itinerary for {dest['name']} focusing on local markets."
    else:
        prompt = f"What are common tourist scams in {dest['name']} and how to avoid them?"
        
    data.append({
        "id": f"TR-{i:03d}",
        "prompt": prompt,
        "task_category": task,
        "region": dest['region'],
        "destination": dest['name']
    })

pd.DataFrame(data).to_csv("travel_benchmark.csv", index=False)
```

## 3. Running the Pipeline

Follow this order to execute the evaluation:

1.  **EXECUTE**: Run `eval_pipeline.py` to call your LLMs and collect responses.
    *   `python eval_pipeline.py --model gpt-4o`
    *   `python eval_pipeline.py --model gemini-1.5-pro`
2.  **EXTRACT CLAIMS**: The script will automatically segment sentences into atomic claims.
3.  **VERIFY**: 
    *   Integrate [SerpAPI](https://serpapi.com/) for real-time web search.
    *   Use a 'Judge LLM' to compare search snippets with claims.
4.  **SCORE BIAS**:
    *   Calculate **Sentiment Polarity** using `TextBlob`.
    *   Calculate **Exposure Parity** by counting region-specific recommendations.

## 4. Final Analysis

Generate the dashboard or summaries:

```bash
# Example analysis
python -c "import pandas as pd; df = pd.read_csv('results.csv'); print(df.groupby(['model', 'region'])['hallucination_rate'].mean())"
```

## 5. Mitigation Deployment

Implement the **Self-Reflective Loop** in your production agent:

```python
def agent_call(prompt):
    # Step 1: Initial Response
    initial_res = model.generate(prompt)
    
    # Step 2: Verification Loop
    verification_prompt = f"You are a fact-checker. Verify every claim in: {initial_res}. Flag anything uncertain."
    correction = model.generate(verification_prompt)
    
    # Step 3: Final Output (after correction)
    return model.generate(f"Refine this based on corrections: {initial_res}\nCorrections: {correction}")
```
