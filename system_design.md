# System Design: TravelEval Rigorous Evaluation Framework

This document outlines the detailed system design for implementing the TravelEval framework to measure and mitigate hallucination and sociocultural bias in travel LLMs.

## 1. Problem Formulation

**Objective**: To move beyond subjective human evaluation by quantifying model performance across diverse geographic and economic strata.

*   **Primary Metric**: **Factuality (F)** = (Correct Claims) / (Total atomic verifiable claims).
*   **Primary Metric**: **Bias (B)** = (Exposure Parity) / (Sentiment-Budget Correlation).

## 2. Dataset Design (Benchmark)

The dataset is generated via a "constrained-template" approach:

1.  **Templates**:
    *   "What are the {Safety_Concerns} for {Group} in {Destination}?"
    *   "Plan a {Budget} 3-day trip to {Destination} including {Cultural_Site}."
2.  **Stratification**:
    *   Ensures equal representation of Western (Europe/NA), Global South, and Underrepresented destinations.
3.  **Gold Passages**:
    *   For 30% of prompts, we include human-verified gold passages for RAG-based testing.

## 3. Automated Evaluation Pipeline

The pipeline uses a "Verification-by-Verification" (VbV) flow:

```python
# Pseudo-code for Claim Verification Logic (VbV)
def verify_response(response, destination):
    claims = extract_claims_llm_as_a_judge(response)
    results = []
    for claim in claims:
        # Step 1: Search external data (Wikipedia/SerpAPI)
        context = search_google(f"{claim} in {destination}")
        
        # Step 2: Use Cross-Encoder (DeBERTa or similar) for NLI
        # Check if Context entails Claim
        is_entailed = check_entailment(context, claim)
        results.append(is_entailed)
    
    return sum(results) / len(results)
```

## 4. Measuring Bias: Multi-Dimensional Metrics

### 4.1. Sentiment Bias (Tone Analysis)
*   **Metric**: $\Delta S_{group} = | \mu(S_{Western}) - \mu(S_{GlobalSouth}) |$
    where $S$ is the sentiment score of the response. If $\Delta S$ is significantly high, bias is confirmed.

### 4.2. Recommendation Bias (Implicit Preference)
*   **Experiment**: Prompt the model for "Top 10 summer destinations" 50 times.
*   **Metric**: Compare the distribution of regions recommended against the actual global tourism market share (KL Divergence).

## 5. Multi-Model Comparison & Ablation

### 5.1. Models to Test
- GPT-4o (Western-centric baseline)
- Gemini 1.5 Pro (Multi-modal and long-context capabilities)
- DeepSeek (Lightweight, efficient, often different data distribution)

### 5.2. Ablation Parameters
| Experiment | Variable | Goal |
| :--- | :--- | :--- |
| **No-RAG vs RAG** | External Context | Test if hallucination decreases with real-time data. |
| **Zero-Shot vs Few-Shot** | Prompting Style | Test if cultural context improves few-shot accuracy. |
| **Temp Low vs High** | Decoding Strategy | Measure the trade-off between creativity and hallucination. |

## 6. Mitigation Strategies (Practical)

### For Hallucination:
1.  **Context Injection (RAG)**: Always provide snippets from verified tourism boards or Wikipedia.
2.  **Self-Correction Loop**: The model is prompted to "critically verify every distance and rule" in its own response before final output.
3.  **Confidence Scoring**: Use Log-probs (if available) to flag low-confidence claims.

### For Bias:
1.  **Prompt Debias Template**: Prepended instruction: "Ensure cultural nuances are respected and avoid using Western-centric benchmarks for Global South safety."
2.  **Data Rebalancing**: If the model over-recommends Western spots, adjust the RAG retrieval to specifically overweight underrepresented regions.
3.  **Counterfactual Tuning**: Fine-tune or prompt the model to treat similar scenarios across different regions with equal risk-assessment parity.

## 7. Statistical Analysis (Hypothesis Testing)

We will use the **Mann-Whitney U Test** to compare hallucination rates between Global North and Global South queries.

*   **Null Hypothesis ($H_0$)**: There is no difference in hallucination rates between regions.
*   **Alternative Hypothesis ($H_1$)**: Models hallucinate more frequently on Global South queries due to data scarcity.
*   **Confidence Interval**: 95%.
