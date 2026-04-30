# TravelEval Live LLM Evaluation Report

Generated on: 2026-04-30

## Scope Completed

Per current direction, the user trust study is excluded.

Completed live technical work:

- Added NVIDIA-hosted model support to `eval_pipeline.py`.
- Added `--max-tokens` to `eval_pipeline.py` and `realtime_eval.py` to reduce latency and runaway response length.
- Added NVIDIA-backed judge support so evaluation can continue when Groq judge quota is exhausted.
- Ran full live real-time evaluation on 40 prompts x 4 NVIDIA-hosted models.
- Ran full live bias response generation on 63 prompts x 4 NVIDIA-hosted models.
- Ran bias entity extraction and summary analysis.
- Ran full live niche gold evaluation on 194 prompts x 2 stable NVIDIA-hosted models.
- Ran analysis tables for the gold evaluation.
- Created a balanced 60-row hallucination subset covering all 6 categories.
- Ran live claim-level hallucination evaluation on that 60-row subset x 2 stable NVIDIA-hosted models.
- Ran analysis tables for the claim-level evaluation.

## Models Used

Response-generation models successfully used:

- `nvidia:meta/llama-3.1-8b-instruct`
- `nvidia:meta/llama-3.1-70b-instruct`
- `nvidia:meta/llama-3.3-70b-instruct`
- `nvidia:mistralai/mixtral-8x7b-instruct-v0.1`

Stable models for the main factuality runs:

- `nvidia:meta/llama-3.1-8b-instruct`
- `nvidia:mistralai/mixtral-8x7b-instruct-v0.1`

Judge model for the final live factuality runs:

- `nvidia:meta/llama-3.1-8b-instruct`

## Key Outputs

- `results/realtime_nvidia_live/`
- `results/bias_nvidia_live_fast/`
- `results/niche_gold_nvidia_live/`
- `results/hallucination_claims_nvidia_live/`
- `data_collection/hallucination_dataset_balanced_60.csv`

## Module Results

### 1. Real-Time Reliability

Source:

- `results/realtime_nvidia_live/realtime_summary.json`

Coverage:

- 160 evaluated rows
- 40 prompts x 4 models

Headline result:

- Real-time accuracy was extremely poor across all tested NVIDIA-hosted models.

Accuracy by model:

| Model | Accuracy |
|---|---:|
| `nvidia:meta/llama-3.1-8b-instruct` | 0.0250 |
| `nvidia:meta/llama-3.1-70b-instruct` | 0.0000 |
| `nvidia:meta/llama-3.3-70b-instruct` | 0.0000 |
| `nvidia:mistralai/mixtral-8x7b-instruct-v0.1` | 0.0000 |

Metric-level result:

| Metric | Accuracy |
|---|---:|
| `temperature_celsius` | 0.0125 |
| `local_time_minutes` | 0.0000 |

Interpretation:

- These models mostly refused or failed to provide live time/weather values.
- As an evaluation result, this strongly supports the claim that static chat models are unreliable for real-time tourism questions unless tool access is explicitly provided.

### 2. Bias Evaluation

Sources:

- `results/bias_nvidia_live_fast/eval_responses.csv`
- `results/bias_nvidia_live_fast/analysis/bias_summary_by_model.csv`
- `results/bias_nvidia_live_fast/analysis/bias_region_share.csv`

Coverage:

- 252 response rows
- 63 prompts x 4 models
- 658 extracted recommendation entities

Model stability:

| Model | OK rows | Error rows |
|---|---:|---:|
| `nvidia:meta/llama-3.1-8b-instruct` | 63 | 0 |
| `nvidia:mistralai/mixtral-8x7b-instruct-v0.1` | 63 | 0 |
| `nvidia:meta/llama-3.1-70b-instruct` | 41 | 22 |
| `nvidia:meta/llama-3.3-70b-instruct` | 41 | 22 |

Summary by model:

| Model | Items | Unique destinations | Unique countries | Shannon diversity | HHI concentration | Top region |
|---|---:|---:|---:|---:|---:|---|
| `nvidia:meta/llama-3.1-8b-instruct` | 211 | 145 | 35 | 2.058176 | 0.046697 | Europe |
| `nvidia:meta/llama-3.1-70b-instruct` | 133 | 103 | 37 | 2.055951 | 0.052745 | Europe |
| `nvidia:meta/llama-3.3-70b-instruct` | 127 | 102 | 31 | 2.060937 | 0.057350 | Europe |
| `nvidia:mistralai/mixtral-8x7b-instruct-v0.1` | 187 | 150 | 45 | 2.129629 | 0.110641 | unknown |

Interpretation:

- The three Meta-family runs skewed most heavily toward Europe in extracted recommendation share.
- Mixtral produced the highest diversity score, but its extraction quality was partially affected by Groq rate limits during entity extraction fallback, which inflated the `unknown` region share.
- This means the bias module is complete enough for directional findings, but Mixtral's region distribution should be interpreted with extra caution.

### 3. Niche Gold Factuality Evaluation

Sources:

- `results/niche_gold_nvidia_live/eval_summary.json`
- `results/niche_gold_nvidia_live/analysis/answer_correctness_by_model.csv`

Coverage:

- 388 evaluated rows
- 194 strict gold rows x 2 models

Model stability:

| Model | OK rows | Error rows |
|---|---:|---:|
| `nvidia:meta/llama-3.1-8b-instruct` | 179 | 15 |
| `nvidia:mistralai/mixtral-8x7b-instruct-v0.1` | 194 | 0 |

Answer correctness:

| Model | Mean correctness | 95% CI low | 95% CI high |
|---|---:|---:|---:|
| `nvidia:meta/llama-3.1-8b-instruct` | 0.353093 | 0.290191 | 0.415995 |
| `nvidia:mistralai/mixtral-8x7b-instruct-v0.1` | 0.337629 | 0.282487 | 0.392771 |

Hallucination rate:

| Model | Mean hallucination rate |
|---|---:|
| `nvidia:meta/llama-3.1-8b-instruct` | 0.6469 |
| `nvidia:mistralai/mixtral-8x7b-instruct-v0.1` | 0.6624 |

Interpretation:

- Both tested models performed poorly on the strict tourism niche benchmark.
- On this gold-backed set, only about one-third of answers were graded correct on average.
- The evidence now supports a concrete factual reliability weakness on harder tourism knowledge tasks.

### 4. Hallucination Claim Evaluation

Sources:

- `data_collection/hallucination_dataset_balanced_60.csv`
- `results/hallucination_claims_nvidia_live/eval_summary.json`
- `results/hallucination_claims_nvidia_live/analysis/claim_verdict_summary.csv`

Coverage:

- 120 evaluated responses
- 286 evaluated claims
- 60 prompts x 2 models
- Balanced across 6 categories

Model stability:

| Model | OK rows | Error rows |
|---|---:|---:|
| `nvidia:meta/llama-3.1-8b-instruct` | 59 | 1 |
| `nvidia:mistralai/mixtral-8x7b-instruct-v0.1` | 60 | 0 |

Response-level hallucination rate:

| Model | Mean hallucination rate |
|---|---:|
| `nvidia:meta/llama-3.1-8b-instruct` | 0.2839 |
| `nvidia:mistralai/mixtral-8x7b-instruct-v0.1` | 0.1514 |

Claim verdict shares:

| Model | Supported | Contradicted | Not found | Unclear |
|---|---:|---:|---:|---:|
| `nvidia:meta/llama-3.1-8b-instruct` | 0.792793 | 0.027027 | 0.108108 | 0.072072 |
| `nvidia:mistralai/mixtral-8x7b-instruct-v0.1` | 0.845714 | 0.022857 | 0.102857 | 0.028571 |

Interpretation:

- On the balanced hallucination subset, Mixtral outperformed the 8B Llama model by a noticeable margin.
- Mixtral produced lower response-level hallucination and a higher supported-claim share.

## What Is Genuinely Completed Now

Completed:

- Live real-time module
- Live bias module
- Live niche gold module on the strict 194-row dataset
- Live hallucination claim module on a balanced 60-row subset
- Paper-style analysis tables for gold and hallucination runs
- Bias summaries and entity outputs

## What Is Still Not Fully Complete

Not yet complete:

1. Full 263-row hallucination claim evaluation across the entire dataset.
   The current live claim run covers a balanced 60-row subset.

2. Expanded 351-row niche gold evaluation.
   The strict 194-row medium/high-tier set was evaluated live; the 351-row expanded set was not fully evaluated live.

3. Clean multi-model completion with 3 to 5 stable factuality models.
   The larger NVIDIA 70B models produced connection failures, so the final factuality runs were completed with the two stable models.

4. User trust study.
   Intentionally excluded for this phase.

## Bottom Line

The project aim is still not 100 percent fully complete in the broadest paper-ready sense, but it is now substantially more complete than before:

- the non-trust technical modules have been executed live rather than only scaffolded
- we now have real benchmark outputs, real summaries, and concrete comparative findings
- the remaining gap is mainly scale and provider stability, not missing infrastructure

