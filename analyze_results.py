import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


def mean_ci(series: pd.Series) -> Dict[str, float]:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return {"n": 0, "mean": float("nan"), "std": float("nan"), "ci95_low": float("nan"), "ci95_high": float("nan")}
    mean = float(values.mean())
    std = float(values.std(ddof=1)) if len(values) > 1 else 0.0
    sem = std / (len(values) ** 0.5) if len(values) > 1 else 0.0
    delta = 1.96 * sem
    return {
        "n": int(len(values)),
        "mean": round(mean, 6),
        "std": round(std, 6),
        "ci95_low": round(mean - delta, 6),
        "ci95_high": round(mean + delta, 6),
    }


def grouped_metric(df: pd.DataFrame, group_cols: List[str], metric: str) -> pd.DataFrame:
    usable = df.dropna(subset=[metric]).copy()
    rows = []
    for keys, group in usable.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = dict(zip(group_cols, keys))
        row.update(mean_ci(group[metric]))
        rows.append(row)
    return pd.DataFrame(rows)


def mann_whitney(df: pd.DataFrame, metric: str, group_col: str, a: str, b: str) -> Optional[Dict[str, float]]:
    try:
        from scipy.stats import mannwhitneyu
    except ImportError:
        return None

    left = pd.to_numeric(df[df[group_col] == a][metric], errors="coerce").dropna()
    right = pd.to_numeric(df[df[group_col] == b][metric], errors="coerce").dropna()
    if len(left) < 2 or len(right) < 2:
        return None
    stat, p_value = mannwhitneyu(left, right, alternative="two-sided")
    return {
        "metric": metric,
        "group_col": group_col,
        "group_a": a,
        "group_b": b,
        "n_a": int(len(left)),
        "n_b": int(len(right)),
        "mean_a": round(float(left.mean()), 6),
        "mean_b": round(float(right.mean()), 6),
        "u_statistic": round(float(stat), 6),
        "p_value": round(float(p_value), 6),
    }


def claim_verdict_summary(claims: pd.DataFrame) -> pd.DataFrame:
    if claims.empty:
        return pd.DataFrame()
    counts = (
        claims.groupby(["model", "verdict"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["model", "verdict"])
    )
    totals = counts.groupby("model")["count"].transform("sum")
    counts["share"] = (counts["count"] / totals).round(6)
    return counts


def write_json(path: Path, data: Dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create paper-ready summaries from TravelEval outputs.")
    parser.add_argument("--responses", default="results/eval_responses.csv")
    parser.add_argument("--claims", default="results/eval_claims.csv")
    parser.add_argument("--output-dir", default="results/analysis")
    args = parser.parse_args()

    response_path = Path(args.responses)
    claim_path = Path(args.claims)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not response_path.exists():
        raise FileNotFoundError(f"Response file not found: {response_path}")

    responses = pd.read_csv(response_path)
    claims = pd.read_csv(claim_path) if claim_path.exists() else pd.DataFrame()

    tables = {}
    for metric in ["hallucination_rate", "answer_correctness", "sentiment_score"]:
        if metric not in responses.columns:
            continue
        metric_df = responses.dropna(subset=[metric])
        if metric_df.empty:
            continue

        for group_cols in [["model"], ["model", "region"], ["model", "task"], ["model", "evaluation_mode"]]:
            valid_cols = [col for col in group_cols if col in responses.columns]
            if not valid_cols:
                continue
            table = grouped_metric(responses, valid_cols, metric)
            name = f"{metric}_by_{'_'.join(valid_cols)}"
            tables[name] = table
            table.to_csv(output_dir / f"{name}.csv", index=False)

    if not claims.empty:
        claim_summary = claim_verdict_summary(claims)
        claim_summary.to_csv(output_dir / "claim_verdict_summary.csv", index=False)
        tables["claim_verdict_summary"] = claim_summary

    tests = []
    if "region" in responses.columns:
        tests_to_try = [
            ("hallucination_rate", "Global-North", "Global-South"),
            ("sentiment_score", "Global-North", "Global-South"),
        ]
        for metric, a, b in tests_to_try:
            if metric in responses.columns:
                result = mann_whitney(responses, metric=metric, group_col="region", a=a, b=b)
                if result:
                    tests.append(result)

    diagnostics = {
        "responses": int(len(responses)),
        "claims": int(len(claims)),
        "models": sorted(responses["model"].dropna().astype(str).unique().tolist()) if "model" in responses else [],
        "tasks": sorted(responses["task"].dropna().astype(str).unique().tolist()) if "task" in responses else [],
        "regions": sorted(responses["region"].dropna().astype(str).unique().tolist()) if "region" in responses else [],
        "statistical_tests": tests,
        "generated_tables": sorted(tables.keys()),
    }
    write_json(output_dir / "analysis_summary.json", diagnostics)

    print(json.dumps(diagnostics, indent=2))


if __name__ == "__main__":
    main()
