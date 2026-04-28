# Practical Implementation Guide: TravelEval

This guide describes the current research workflow for evaluating reliability, bias, real-time accuracy, and trust in AI-driven tourism systems.

## 1. Environment Setup

Create and activate a virtual environment, then install the project dependencies:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Your `.env` should contain these keys:

```bash
SERP_API_KEY=...
GROQ_API_KEY=...
GEMINI_API_KEY=...
OPENROUTER_KEY=...
DEEPSEEK_KEY=...
```

The file is ignored by git, so do not commit secrets.

## 2. Prepare Research Datasets

Generate or refresh the prompt datasets:

```bash
python data_collection/hallucination_queries.py
python data_collection/bias_prompts.py
python data_collection/realtime_queries.py
```

Clean the 351-row niche backup into a source-audited gold dataset:

```bash
python data_collection/build_research_datasets.py --input travel_benchmark_niche_backup.csv --min-tier medium
```

This writes:

- `data_collection/research_gold_niche.csv`
- `data_collection/source_quality_audit.csv`

To create candidate gold answers for the hallucination prompt set:

```bash
python data_collection/enrich_hallucination_ground_truth.py --limit 25
```

Remove `--limit` only when you are ready to spend SerpAPI and Groq calls across the full set.

## 3. Run Evidence-Backed Model Evaluation

Smoke test without external API calls:

```bash
python eval_pipeline.py --dataset data_collection/research_gold_niche.csv --models deepseek-chat --limit 2 --dry-run --output-dir results/smoke
```

Run gold-answer evaluation on the cleaned niche dataset:

```bash
python eval_pipeline.py ^
  --dataset data_collection/research_gold_niche.csv ^
  --models deepseek-chat,gemini-1.5-flash,meta-llama/llama-3-8b-instruct:free,mistralai/mistral-7b-instruct:free ^
  --mode gold ^
  --output-dir results/niche_gold ^
  --sleep 1
```

Run claim-level hallucination evaluation on prompts without gold answers:

```bash
python eval_pipeline.py ^
  --dataset data_collection/hallucination_dataset.csv ^
  --models deepseek-chat,gemini-1.5-flash ^
  --mode claim ^
  --output-dir results/hallucination_claims ^
  --sleep 1
```

The pipeline writes:

- `eval_responses.csv`: one row per prompt/model answer
- `eval_claims.csv`: one row per verified claim
- `eval_summary.json`: grouped headline metrics

Verification is cached under `.cache/traveleval/` to reduce repeat API usage.

## 4. Run Bias Evaluation

First collect model responses to neutral recommendation prompts:

```bash
python eval_pipeline.py ^
  --dataset data_collection/bias_dataset.csv ^
  --models deepseek-chat,gemini-1.5-flash,meta-llama/llama-3-8b-instruct:free,mistralai/mistral-7b-instruct:free ^
  --mode bias ^
  --output-dir results/bias_responses ^
  --sleep 1
```

Then extract recommended destinations and compute diversity/concentration metrics:

```bash
python bias_analysis.py --responses results/bias_responses/eval_responses.csv --output-dir results/bias
```

This writes:

- `bias_entities.csv`
- `bias_region_share.csv`
- `bias_summary_by_model.csv`
- `bias_top_destinations.csv`

## 5. Run Real-Time Reliability Evaluation

Real-time weather and local-time ground truth is fetched at evaluation time:

```bash
python realtime_eval.py ^
  --dataset data_collection/realtime_dataset.csv ^
  --models deepseek-chat,gemini-1.5-flash ^
  --output-dir results/realtime ^
  --sleep 1
```

This writes `realtime_results.csv` and `realtime_summary.json`.

## 6. Generate Paper Tables

For any evaluation output directory:

```bash
python analyze_results.py --responses results/niche_gold/eval_responses.csv --claims results/niche_gold/eval_claims.csv --output-dir results/niche_gold/analysis
```

The analysis includes grouped means, 95 percent confidence intervals, claim verdict summaries, and Mann-Whitney U tests when enough Global North and Global South rows exist.

## 7. User Trust Study

The repository currently contains the survey design in `user_survey/survey_design.md`, but the project aim is not complete until responses from 80 to 150 participants are collected.

For paper reporting, keep these files:

- anonymized participant responses
- group assignment: standard LLM vs explainable system
- trust, transparency, reliability, confidence, and adoption scores
- statistical tests: t-test or Mann-Whitney U for two groups, ANOVA/regression if adding covariates

## 8. Minimum Paper-Ready Result Set

For a solid research paper, aim for at least:

- 250 to 300 hallucination prompts with gold answers or claim-level evidence
- 300 or more niche QA rows with source-quality labels
- 60 or more neutral bias prompts across global regions
- 40 or more real-time prompts evaluated live
- 3 to 5 models with identical prompts and temperature settings
- response-level and claim-level CSVs
- confidence intervals and significance tests
- documented source-quality filtering
