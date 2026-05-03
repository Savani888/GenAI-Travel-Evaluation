import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from eval_pipeline import DEFAULT_MAX_TOKENS, call_llm, parse_models


def fetch_temperature_c(lat: float, lon: float) -> Optional[float]:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m",
        "temperature_unit": "celsius",
        "timezone": "UTC",
    }
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()
    current = data.get("current", {})
    value = current.get("temperature_2m")
    return float(value) if value is not None else None


def current_local_minutes(timezone_name: str) -> int:
    now = datetime.now(ZoneInfo(timezone_name))
    return now.hour * 60 + now.minute


def parse_temperature(response: str) -> Optional[float]:
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*(?:deg(?:ree)?s?\s*)?(?:c|celsius|°c)\b", response, flags=re.IGNORECASE)
    if match:
        return float(match.group(1))
    numbers = re.findall(r"-?\d+(?:\.\d+)?", response)
    if len(numbers) == 1:
        return float(numbers[0])
    return None


def parse_time_minutes(response: str) -> Optional[int]:
    match = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", response)
    if match:
        return int(match.group(1)) * 60 + int(match.group(2))

    match = re.search(r"\b(1[0-2]|0?[1-9])(?::([0-5]\d))?\s*(am|pm)\b", response, flags=re.IGNORECASE)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        suffix = match.group(3).lower()
        if suffix == "pm" and hour != 12:
            hour += 12
        if suffix == "am" and hour == 12:
            hour = 0
        return hour * 60 + minute
    return None


def circular_minute_error(a: int, b: int) -> int:
    raw = abs(a - b)
    return min(raw, 1440 - raw)


def evaluate_row(row: pd.Series, response: str) -> Dict:
    metric = str(row.get("metric", ""))
    tolerance = float(row.get("tolerance", 0))
    ground_truth = None
    parsed = None
    error = None

    if metric == "temperature_celsius":
        ground_truth = fetch_temperature_c(float(row["lat"]), float(row["lon"]))
        parsed = parse_temperature(response)
        if ground_truth is not None and parsed is not None:
            error = abs(parsed - ground_truth)
    elif metric == "local_time_minutes":
        ground_truth = current_local_minutes(str(row["timezone"]))
        parsed = parse_time_minutes(response)
        if ground_truth is not None and parsed is not None:
            error = circular_minute_error(int(parsed), int(ground_truth))

    correct = error is not None and error <= tolerance
    return {
        "ground_truth_value": ground_truth,
        "parsed_value": parsed,
        "absolute_error": error,
        "correct": bool(correct),
    }


def summarize(results: pd.DataFrame) -> Dict:
    summary = {"rows": int(len(results))}
    if results.empty:
        return summary
    summary["accuracy_by_model"] = results.groupby("model")["correct"].mean().round(6).to_dict()
    summary["accuracy_by_metric"] = results.groupby("metric")["correct"].mean().round(6).to_dict()
    summary["accuracy_by_region"] = results.groupby("region")["correct"].mean().round(6).to_dict()
    return summary


def _completed_realtime_keys(output_path: Path) -> set:
    """Return set of (prompt_id, model) pairs already saved — enables per-model resume."""
    if not output_path.exists():
        return set()
    try:
        df = pd.read_csv(output_path)
        if {"prompt_id", "model"}.issubset(df.columns):
            return set(zip(df["prompt_id"].astype(str), df["model"].astype(str)))
    except Exception:
        pass
    return set()


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate real-time weather/time reliability.")
    parser.add_argument("--dataset", default="data_collection/realtime_dataset.csv")
    parser.add_argument("--output-dir", default="results/realtime")
    parser.add_argument("--models", default="deepseek-chat,gemini-1.5-flash")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-resume", action="store_true",
                        help="Ignore existing results and re-evaluate all rows.")
    args = parser.parse_args()

    rows = pd.read_csv(args.dataset)
    if args.limit is not None:
        rows = rows.head(args.limit)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "realtime_results.csv"

    completed = set() if args.no_resume else _completed_realtime_keys(output_path)
    if completed:
        print(f"Resuming: {len(completed)} (prompt_id, model) pairs already done — skipping.")

    for model in parse_models(args.models):
        print(f"Evaluating real-time prompts with {model}")
        model_results: List[Dict] = []
        for _, row in rows.iterrows():
            key = (str(row["id"]), model)
            if key in completed:
                print(f"  Skipping {row['id']} / {model} (already done)")
                continue

            try:
                response = call_llm(
                    str(row["prompt"]),
                    model=model,
                    dry_run=args.dry_run,
                    max_tokens=args.max_tokens,
                )
                if args.sleep > 0:
                    time.sleep(args.sleep)
                scoring = evaluate_row(row, response) if not args.dry_run else {
                    "ground_truth_value": None,
                    "parsed_value": None,
                    "absolute_error": None,
                    "correct": False,
                }
            except Exception as exc:
                print(f"  Error for {row['id']} / {model}: {exc}")
                response = "ERROR"
                scoring = {
                    "ground_truth_value": None,
                    "parsed_value": None,
                    "absolute_error": None,
                    "correct": False,
                    "error": str(exc),
                }

            result_row = {
                "prompt_id": row["id"],
                "prompt": row["prompt"],
                "model": model,
                "city": row["city"],
                "region": row["region"],
                "metric": row["metric"],
                "tolerance": row["tolerance"],
                "response": response,
                "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
                **scoring,
            }
            model_results.append(result_row)
            completed.add(key)
            # Append incrementally so partial runs are not lost
            pd.DataFrame([result_row]).to_csv(
                output_path, mode="a", header=not output_path.exists(), index=False
            )

        print(f"  {model}: {len(model_results)} new rows written.")

    df = pd.read_csv(output_path) if output_path.exists() else pd.DataFrame()
    summary = summarize(df)
    (output_dir / "realtime_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
