# Implementation Plan: 500 Niche Travel Prompts (v2)

This plan details the strategy for generating a high-quality, research-validated dataset of 500 niche travel prompts to rigorously evaluate LLM factuality and bias.

## Goal Description
Build a "Stress-Test" dataset that targets specific LLM weaknesses in underrepresented regions and complex travel regulations.

## User Review Required
> [!IMPORTANT]
> **API Costs**: 500 SerpAPI queries will consume significant credits if not batched efficiently. I will prioritize "snippet" results to minimize overhead.
> **Niche Depth**: Niche topics include:
> - **Transit**: Currency restrictions for specific buses/trains in Central Asia.
> - **Legal**: Obscure local bans (e.g., specific drone laws in Namibia).
> - **Visa**: Dual-passport quirks or e-visa delays for specific land-border crossings.

## Proposed Changes

### [NEW] [niche_generator.py](file:///d:/tourism/niche_generator.py)
A specialized script that:
1.  **Researches**: Uses SerpAPI with regional keywords (e.g., "Bhutan visa recent changes 2026").
2.  **Extracts Facts**: Uses Groq (Llama-3-70b/8b) to parse "niche facts" from search results.
3.  **Generates Prompts**: Turns facts into user-like queries.
4.  **Validates**: Cross-verifies the "ground truth" to ensure absolute accuracy.

### [NEW] [travel_benchmark_niche.csv](file:///d:/tourism/travel_benchmark_niche.csv)
The final 500-prompt dataset with columns for:
- `id`, `category`, `region`, `prompt`, `ground_truth`, `source_url`.

## Verification Plan

### Automated Verification
- **Batch Validation**: Run the generator in batches of 50. Skip entries if verification confidence < 0.9.
- **Deduplication**: Ensure no redundant prompts across categories.
- **Reference Check**: Ensure every `ground_truth` has a valid `source_url`.

### Manual Spot Check
- User review of 10 random "Niche" samples to confirm the difficulty level is sufficient.

## Open Questions
- Do you have a preference for which model on Groq (Llama-3-70b, Mixtral, etc.) to use for fact extraction? I'll assume Llama-3-70b for maximum reasoning quality.
- Should we prioritize specific regions (e.g., Sub-Saharan Africa or Central Asia) for the "Niche" portion?
