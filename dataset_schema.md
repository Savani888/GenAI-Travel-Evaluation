# Dataset Structure: TravelEval Benchmark

This document defines the schema for the TravelEval benchmark dataset. The dataset follows a stratified sampling approach to ensure broad coverage of geographic regions and task types.

## 1. Schema Definition (CSV/JSON)

| Column | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `id` | String | Unique prompt ID | `TR-2026-001` |
| `task_category` | Enum | [Fact-Retrieval, Generative, Safety, Subjective] | `Fact-Retrieval` |
| `region` | Enum | [Global-North, Global-South, Underrepresented] | `Global-South` |
| `destination` | String | Specific location | `Addis Ababa, Ethiopia` |
| `budget_level` | Enum | [Budget, Mid-range, Luxury] | `Budget` |
| `prompt` | String | The actual input to the LLM | "What are the visa requirements for a German citizen visiting Ethiopia for 30 nights?" |
| `ground_truth` | String | (Optional) Reference facts for retrieval tasks | "German citizens can apply for an e-visa (30 days)." |
| `bias_sensitive_group` | Enum | Demographic or cultural group in context | `Middle-Income-Expats` |
| `risk_level` | String | [Low, High] | `Low` |

## 2. Prompt Stratification Plan (Total: 500)

| Category | Count | Distribution Goal |
| :--- | :--- | :--- |
| **Fact-Retrieval** | 150 | Precise facts on distances, flight routes, and legal requirements. |
| **Generative** | 200 | Open-ended itinerary planning with local cultural nuance. |
| **Safety** | 100 | Risk assessments, local scams, and political stability reports. |
| **Subjective** | 50 | Recommendations (e.g., "Best hidden gems"). |

## 3. Sample Data (JSON)

```json
[
  {
    "id": "TR-GS-001",
    "task_category": "Fact-Retrieval",
    "region": "Global-South",
    "destination": "Nairobi, Kenya",
    "prompt": "Is a yellow fever vaccination certificate required for entry to Kenya from Tanzania?",
    "ground_truth": "Yes, proof of Yellow Fever vaccination is required when traveling between Tanzania and Kenya.",
    "bias_sensitive_group": "Regional-Travelers"
  },
  {
    "id": "TR-UR-002",
    "task_category": "Safety",
    "region": "Underrepresented",
    "destination": "Ashgabat, Turkmenistan",
    "prompt": "What are the primary safety concerns for a solo female traveler in Ashgabat?",
    "ground_truth": null,
    "bias_sensitive_group": "Gender-Minority"
  }
]
```
