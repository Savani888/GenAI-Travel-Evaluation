# GenAI-Travel-Evaluation (TravelEval)

TravelEval is a research framework for auditing tourism-focused large language model (LLM) behavior across four dimensions:

1. factual reliability and hallucination risk
2. geographic and recommendation bias
3. real-time answer reliability (weather and local time)
4. user trust and perceived transparency (study design included)

This repository is designed for reproducible, evidence-backed evaluation rather than informal prompt demos.

## Project Aim

The project aims to generate empirical, statistically analyzable evidence about how AI travel assistants perform and fail in realistic tourism scenarios.

The core research questions are:

1. How often do tourism model responses contain unsupported or incorrect factual claims?
2. Do recommendation patterns over-expose popular or Western destinations and under-expose other regions?
3. How reliable are model answers for dynamic, time-sensitive queries?
4. How does interface style (standard assistant vs explainable assistant) affect user trust?

Supporting methodology and long-form rationale are documented in:

- [Project Aim.md](Project%20Aim.md)
- [system_design.md](system_design.md)
- [practical_guide.md](practical_guide.md)

## What This Repository Contains

### Evaluation Engine

- `eval_pipeline.py`
	- Main evidence-backed benchmark runner for gold-mode and claim-mode evaluation.
	- Produces response-level and claim-level outputs.
	- Supports multiple providers and model naming schemes.

- `analyze_results.py`
	- Produces grouped paper-style summaries, confidence intervals, and non-parametric significance tests.

- `bias_analysis.py`
	- Extracts recommended entities from model responses and computes concentration/diversity metrics.

- `realtime_eval.py`
	- Evaluates real-time prompt reliability against live weather and time ground truth.

### Dataset and Benchmark Construction

- `data_collection/hallucination_queries.py`
	- Generates diverse hallucination-focused tourism prompts by category.

- `data_collection/bias_prompts.py`
	- Generates neutral recommendation prompts across regions for bias probing.

- `data_collection/realtime_queries.py`
	- Generates real-time weather/time prompts with evaluation metadata (coordinates, timezone, tolerance).

- `niche_generator.py`
	- Scales hard-to-know, niche tourism prompt generation using search snippets and LLM extraction.

- `data_collection/build_research_datasets.py`
	- Cleans and filters niche data into a source-quality-audited gold dataset.

- `data_collection/enrich_hallucination_ground_truth.py`
	- Adds source-backed candidate gold answers to hallucination prompts.

### Additional Utilities

- `generate_dataset.py`
	- Creates a small synthetic benchmark for quick local testing.

- `safeguard_evaluation.py`
	- Demonstrates safety and stereotype checking with a policy-style safeguard model.

## High-Level Workflow

Typical research flow:

1. Build or refresh datasets.
2. Run model evaluation in the desired mode (gold, claim, bias, realtime).
3. Generate summary tables and statistical diagnostics.
4. Analyze fairness and reliability patterns by region, task, and model.
5. (Optional) Run user trust experiment based on provided survey design.

## Installation

### 1) Create environment and install dependencies

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Configure secrets

Create a `.env` file in the repository root:

```bash
SERP_API_KEY=...
GROQ_API_KEY=...
GEMINI_API_KEY=...
OPENROUTER_KEY=...
DEEPSEEK_KEY=...
JUDGE_MODEL=llama-3.3-70b-versatile
```

Notes:

- Not all keys are required for every workflow.
- `eval_pipeline.py` can run in `--dry-run` mode without external API calls.
- Claim verification and many judge/extraction paths require Groq and SerpAPI.

## Quick Start

### Smoke test (no paid API calls)

```bash
python eval_pipeline.py --dataset data_collection/research_gold_niche.csv --models deepseek-chat --limit 2 --dry-run --output-dir results/smoke
```

### Analyze smoke results

```bash
python analyze_results.py --responses results/smoke/eval_responses.csv --claims results/smoke/eval_claims.csv --output-dir results/smoke/analysis
```

## Core Evaluation Modes

`eval_pipeline.py` supports four modes:

1. `auto`
2. `gold`
3. `claim`
4. `bias`

### Mode behavior

- `gold`: compares full model answers against provided gold answers.
- `claim`: extracts atomic claims and verifies each claim against retrieved web evidence.
- `bias`: records responses for downstream recommendation bias analysis.
- `auto`: infers mode per row (gold if ground truth exists, bias for neutral recommendation prompts, otherwise claim).

### Example: gold evaluation

```bash
python eval_pipeline.py ^
	--dataset data_collection/research_gold_niche.csv ^
	--models deepseek-chat,gemini-1.5-flash ^
	--mode gold ^
	--output-dir results/niche_gold ^
	--sleep 1
```

### Example: claim verification evaluation

```bash
python eval_pipeline.py ^
	--dataset data_collection/hallucination_dataset.csv ^
	--models deepseek-chat,gemini-1.5-flash ^
	--mode claim ^
	--output-dir results/hallucination_claims ^
	--sleep 1
```

### Example: bias response generation

```bash
python eval_pipeline.py ^
	--dataset data_collection/bias_dataset.csv ^
	--models deepseek-chat,gemini-1.5-flash ^
	--mode bias ^
	--output-dir results/bias_responses
```

## Real-Time Reliability Evaluation

Generate the real-time benchmark dataset:

```bash
python data_collection/realtime_queries.py
```

Run evaluation against live weather/time ground truth:

```bash
python realtime_eval.py ^
	--dataset data_collection/realtime_dataset.csv ^
	--models deepseek-chat,gemini-1.5-flash ^
	--output-dir results/realtime ^
	--sleep 1
```

## Bias Analysis Workflow

1) Generate neutral prompts:

```bash
python data_collection/bias_prompts.py
```

2) Collect model responses in bias mode:

```bash
python eval_pipeline.py --dataset data_collection/bias_dataset.csv --mode bias --output-dir results/bias_responses
```

3) Extract recommendations and compute bias metrics:

```bash
python bias_analysis.py --responses results/bias_responses/eval_responses.csv --output-dir results/bias
```

## Dataset Curation Workflow

### Build source-quality filtered niche gold dataset

```bash
python data_collection/build_research_datasets.py --input travel_benchmark_niche_backup.csv --min-tier medium
```

Outputs:

- `data_collection/research_gold_niche.csv`
- `data_collection/source_quality_audit.csv`

### Enrich hallucination prompts with candidate gold answers

```bash
python data_collection/enrich_hallucination_ground_truth.py --limit 25
```

Output:

- `data_collection/hallucination_gold_candidates.csv`

## Output Files and Their Meaning

### Evaluation outputs

- `eval_responses.csv` (one row per prompt/model response)
	- includes mode, claim counts, hallucination rate, answer correctness (when applicable), and sentiment score.

- `eval_claims.csv` (one row per evaluated claim)
	- includes verdict, score, evidence query, evidence URLs, and rationale.

- `eval_summary.json`
	- headline metrics grouped by model and region.

### Analysis outputs (`analyze_results.py`)

- grouped CSV tables for:
	- hallucination rate
	- answer correctness
	- sentiment score
	- grouped by model, region, task, and evaluation mode (when available)
- `claim_verdict_summary.csv`
- `analysis_summary.json` with diagnostics and statistical test outputs

### Bias outputs (`bias_analysis.py`)

- `bias_entities.csv`
- `bias_region_share.csv`
- `bias_summary_by_model.csv`
- `bias_top_destinations.csv`
- `bias_summary.json`

### Real-time outputs (`realtime_eval.py`)

- `realtime_results.csv`
- `realtime_summary.json`

## Key Metrics Used in This Project

- Hallucination Rate: unsupported claims divided by total claims (or `1 - answer_correctness` in gold mode).
- Answer Correctness: judged against gold answer (`CORRECT`, `PARTIAL`, `INCORRECT`, `NOT_ANSWERED`).
- Claim Verdict Distribution: `SUPPORTED`, `CONTRADICTED`, `NOT_FOUND`, `UNCLEAR`.
- Recommendation Diversity and Concentration:
	- Shannon diversity over regions
	- HHI concentration over countries
- Real-Time Accuracy:
	- temperature absolute error within tolerance
	- local-time minute error (circular) within tolerance

## Reproducibility Notes

To improve reproducibility:

1. Keep model lists, prompt datasets, and CLI parameters fixed across compared runs.
2. Use separate output directories per experiment.
3. Preserve input datasets used for each experiment snapshot.
4. Document API version assumptions and run date for real-time experiments.
5. Use cached evidence and claim-judgment artifacts in `.cache/traveleval` to reduce run-to-run variance and API cost.

## Current Limitations

1. Claim extraction and judging rely on model-based evaluators, which can introduce evaluator noise.
2. Web evidence quality and availability can vary by geography and query wording.
3. Real-time measurements are sensitive to response latency and parseability of generated answers.
4. User trust module currently provides study design; participant data collection is external to this repository.

## Suggested Minimum Paper-Ready Configuration

For strong reporting quality:

1. 250-300 hallucination prompts with claim-level or gold-backed evaluation
2. 300+ niche QA rows with source-quality metadata
3. 60+ neutral bias prompts across multiple regions
4. 40+ real-time prompts evaluated live
5. 3-5 models with identical prompting settings
6. confidence intervals and significance tests in final analysis tables

## Repository Pointers

- Full hands-on commands: [practical_guide.md](practical_guide.md)
- Research objective and modules: [Project Aim.md](Project%20Aim.md)
- Design assumptions and metrics: [system_design.md](system_design.md)
- User trust study instrument: [user_survey/survey_design.md](user_survey/survey_design.md)
