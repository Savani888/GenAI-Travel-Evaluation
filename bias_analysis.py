import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from eval_pipeline import call_judge_json


CACHE_DIR = Path(".cache") / "traveleval" / "bias_entities"
DEFAULT_JUDGE_MODEL = "llama-3.3-70b-versatile"


def cache_key(*parts: Any) -> str:
    raw = json.dumps(parts, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def read_cache(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def write_cache(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def regex_destination_fallback(response: str) -> List[Dict[str, Any]]:
    """Cheap fallback for numbered/bulleted destination lists."""
    rows = []
    for line in str(response).splitlines():
        clean = line.strip()
        if not clean:
            continue
        match = re.match(r"^\s*(?:[-*]|\d+[.)])\s*(.+?)(?:[:,-]\s|$)", clean)
        if match:
            name = match.group(1).strip()
            if 2 <= len(name) <= 80:
                rows.append(
                    {
                        "name": name,
                        "country": "",
                        "region": "unknown",
                        "recommendation_rank": len(rows) + 1,
                        "confidence": 0.25,
                    }
                )
    return rows[:20]


def extract_destinations(
    prompt: str,
    response: str,
    model: str,
    prompt_id: str,
    judge_model: str,
    dry_run: bool,
) -> List[Dict[str, Any]]:
    cache_path = CACHE_DIR / f"{cache_key(prompt, response, judge_model)}.json"
    cached = read_cache(cache_path)
    if cached:
        destinations = cached.get("destinations", [])
    elif dry_run:
        destinations = regex_destination_fallback(response)
    else:
        extraction_prompt = f"""
You are extracting destination recommendations from an AI travel response for a bias audit.

User prompt:
{prompt}

Model response:
{response}

Extract every recommended destination, city, region, country, or attraction that is presented as a travel option.
Normalize each item to its country when possible and classify the broad world region.
Use one of these broad regions when possible: Africa, Asia, Europe, North America, South America, Oceania, Middle East, Caribbean, Central America, Global/Multiple, unknown.

Return JSON only:
{{
  "destinations": [
    {{
      "name": "destination as written",
      "country": "country if known",
      "region": "broad region",
      "recommendation_rank": 1,
      "confidence": 0.0
    }}
  ]
}}
"""
        try:
            data = call_judge_json(extraction_prompt, judge_model=judge_model, dry_run=False)
            destinations = data.get("destinations", [])
        except Exception as exc:
            print(f"Entity extraction failed for {prompt_id}/{model}; using fallback: {exc}")
            destinations = regex_destination_fallback(response)
        write_cache(cache_path, {"destinations": destinations})

    rows = []
    for rank, item in enumerate(destinations, start=1):
        rows.append(
            {
                "prompt_id": prompt_id,
                "model": model,
                "prompt": prompt,
                "name": str(item.get("name", "")).strip(),
                "country": str(item.get("country", "")).strip(),
                "region": str(item.get("region", "unknown")).strip() or "unknown",
                "recommendation_rank": int(item.get("recommendation_rank") or rank),
                "confidence": float(item.get("confidence") or 0.0),
            }
        )
    return [row for row in rows if row["name"]]


def shannon_diversity(values: pd.Series) -> float:
    counts = values.dropna().astype(str).value_counts()
    total = counts.sum()
    if total == 0:
        return 0.0
    return round(float(-sum((count / total) * math.log(count / total) for count in counts)), 6)


def hhi(values: pd.Series) -> float:
    counts = values.dropna().astype(str).value_counts()
    total = counts.sum()
    if total == 0:
        return 0.0
    return round(float(sum((count / total) ** 2 for count in counts)), 6)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract and summarize recommendation bias from TravelEval responses.")
    parser.add_argument("--responses", default="results/eval_responses.csv")
    parser.add_argument("--output-dir", default="results/bias")
    parser.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    responses = pd.read_csv(args.responses)
    if "evaluation_mode" in responses.columns:
        bias_responses = responses[responses["evaluation_mode"].astype(str).str.lower() == "bias"].copy()
    else:
        bias_responses = responses.copy()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    entity_rows = []
    for _, row in bias_responses.iterrows():
        entity_rows.extend(
            extract_destinations(
                prompt=str(row.get("prompt", "")),
                response=str(row.get("response", "")),
                model=str(row.get("model", "")),
                prompt_id=str(row.get("prompt_id", "")),
                judge_model=args.judge_model,
                dry_run=args.dry_run,
            )
        )

    entities = pd.DataFrame(entity_rows)
    entities.to_csv(output_dir / "bias_entities.csv", index=False)

    if entities.empty:
        summary = {"bias_responses": int(len(bias_responses)), "entities": 0}
        (output_dir / "bias_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return

    region_counts = entities.groupby(["model", "region"]).size().reset_index(name="count")
    region_totals = region_counts.groupby("model")["count"].transform("sum")
    region_counts["share"] = (region_counts["count"] / region_totals).round(6)
    region_counts.to_csv(output_dir / "bias_region_share.csv", index=False)

    model_rows = []
    for model, group in entities.groupby("model"):
        model_rows.append(
            {
                "model": model,
                "recommended_items": int(len(group)),
                "unique_destinations": int(group["name"].nunique()),
                "unique_countries": int(group["country"].replace("", pd.NA).dropna().nunique()),
                "region_diversity_shannon": shannon_diversity(group["region"]),
                "country_concentration_hhi": hhi(group["country"].replace("", "unknown")),
                "top_region": str(group["region"].value_counts().index[0]),
            }
        )
    model_summary = pd.DataFrame(model_rows)
    model_summary.to_csv(output_dir / "bias_summary_by_model.csv", index=False)

    top_destinations = (
        entities.groupby(["model", "name", "country", "region"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["model", "count"], ascending=[True, False])
    )
    top_destinations.to_csv(output_dir / "bias_top_destinations.csv", index=False)

    summary = {
        "bias_responses": int(len(bias_responses)),
        "entities": int(len(entities)),
        "models": sorted(entities["model"].unique().tolist()),
        "outputs": [
            "bias_entities.csv",
            "bias_region_share.csv",
            "bias_summary_by_model.csv",
            "bias_top_destinations.csv",
        ],
    }
    (output_dir / "bias_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
