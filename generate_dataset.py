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
print("travel_benchmark.csv created successfully.")
