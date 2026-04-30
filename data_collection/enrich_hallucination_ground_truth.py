import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval_pipeline import call_judge_json, search_evidence


DEFAULT_JUDGE_MODEL = "llama-3.3-70b-versatile"


def choose_gold_answer(prompt: str, category: str, evidence: List[Dict[str, str]], judge_model: str, dry_run: bool) -> Dict:
    evidence_text = "\n\n".join(
        f"[{index}] {item.get('title', '')}\nURL: {item.get('link', '')}\nSnippet: {item.get('snippet', '')}"
        for index, item in enumerate(evidence, start=1)
    )
    judge_prompt = f"""
You are building a gold-answer tourism benchmark.

Question:
{prompt}

Category:
{category}

Search evidence:
{evidence_text}

Using only the evidence above, produce a concise gold answer if the evidence is sufficient.
If the snippets do not contain enough evidence, mark the row as UNVERIFIED.
Prefer official, institutional, or open-knowledge sources over blogs and social media.

Return JSON only:
{{
  "status": "VERIFIED|UNVERIFIED",
  "ground_truth": "concise answer, or empty if unverifiable",
  "source_url": "single best supporting URL, or empty",
  "source_quality": "official|open_knowledge|general_web|weak",
  "rationale": "brief explanation"
}}
"""
    if dry_run:
        return {
            "status": "UNVERIFIED",
            "ground_truth": "",
            "source_url": evidence[0]["link"] if evidence else "",
            "source_quality": "general_web",
            "rationale": "Dry-run only.",
        }
    return call_judge_json(judge_prompt, judge_model=judge_model, dry_run=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Add source-backed gold answers to hallucination prompts.")
    parser.add_argument("--input", default="data_collection/hallucination_dataset.csv")
    parser.add_argument("--output", default="data_collection/hallucination_gold_candidates.csv")
    parser.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL)
    parser.add_argument("--serp-results", type=int, default=5)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sleep", type=float, default=0.0, help="Seconds to pause after each completed row.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    if args.limit is not None:
        df = df.head(args.limit)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    existing = pd.read_csv(output_path) if output_path.exists() else pd.DataFrame()
    completed = set(existing["id"].astype(str)) if not existing.empty and "id" in existing.columns else set()
    rows = existing.to_dict("records") if not existing.empty else []

    for _, row in df.iterrows():
        row_id = str(row["id"])
        if row_id in completed:
            continue
        prompt = str(row["prompt"])
        category = str(row.get("category", ""))
        query = f"{prompt} tourism official source"
        evidence = search_evidence(query, num_results=args.serp_results, dry_run=args.dry_run)
        try:
            gold = choose_gold_answer(prompt, category, evidence, judge_model=args.judge_model, dry_run=args.dry_run)
        except Exception as exc:
            print(f"{row_id}: ERROR ({exc})")
            gold = {
                "status": "ERROR",
                "ground_truth": "",
                "source_url": evidence[0]["link"] if evidence else "",
                "source_quality": "",
                "rationale": str(exc),
            }
        rows.append(
            {
                "id": row_id,
                "prompt": prompt,
                "task_category": category,
                "region": "",
                "country": "",
                "ground_truth": gold.get("ground_truth", ""),
                "source_url": gold.get("source_url", ""),
                "verification_status": gold.get("status", "UNVERIFIED"),
                "source_quality": gold.get("source_quality", ""),
                "rationale": gold.get("rationale", ""),
            }
        )
        pd.DataFrame(rows).to_csv(output_path, index=False)
        print(f"{row_id}: {gold.get('status', 'UNVERIFIED')}")
        if args.sleep > 0:
            time.sleep(args.sleep)

    summary = pd.DataFrame(rows)["verification_status"].value_counts(dropna=False).to_dict() if rows else {}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
