import argparse
import re
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd


COUNTRY_HINTS = [
    "Kyrgyzstan",
    "Tajikistan",
    "Uzbekistan",
    "Turkmenistan",
    "Kazakhstan",
    "Namibia",
    "Botswana",
    "Zambia",
    "Zimbabwe",
    "DR Congo",
    "Democratic Republic of the Congo",
    "Mali",
    "Senegal",
    "Ethiopia",
    "Rwanda",
    "Uganda",
    "Laos",
    "Cambodia",
    "Myanmar",
    "Vietnam",
    "Indonesia",
    "Philippines",
    "Timor-Leste",
    "Bolivia",
    "Paraguay",
    "Ecuador",
    "Guyana",
    "Suriname",
    "Colombia",
    "Peru",
    "Oman",
    "Jordan",
    "Lebanon",
    "Yemen",
    "Iraq",
    "Saudi Arabia",
]


OFFICIAL_MARKERS = [
    ".gov",
    ".gouv",
    ".govt",
    "embassy",
    "usembassy.gov",
    "travel.state.gov",
    "state.gov",
    "gov.uk",
    "canada.ca",
    "smartraveller.gov.au",
    "government.nl",
    "unwto.org",
    "unesco.org",
]

WEAK_MARKERS = [
    "facebook.com",
    "reddit.com",
    "youtube.com",
    "tiktok.com",
    "instagram.com",
    "pinterest.com",
    "quora.com",
]

COMMERCIAL_MARKERS = [
    "tripadvisor",
    "lonelyplanet",
    "nomadic",
    "blog",
    "tour",
    "travel",
    "adventure",
    "booking",
]


def infer_country(prompt: str, existing: str) -> str:
    if existing and existing.lower() != "nan":
        return existing
    for country in COUNTRY_HINTS:
        if re.search(rf"\b{re.escape(country)}\b", prompt, flags=re.IGNORECASE):
            return "DR Congo" if country == "Democratic Republic of the Congo" else country
    return ""


def source_quality(url: str) -> str:
    value = str(url).lower()
    domain = urlparse(value).netloc
    if not value or value == "nan":
        return "missing"
    if any(marker in value for marker in WEAK_MARKERS):
        return "weak_social_or_forum"
    if any(marker in value for marker in OFFICIAL_MARKERS) or domain.endswith(".gov"):
        return "official"
    if "wikipedia.org" in value or "wikivoyage.org" in value or "wikidata.org" in value:
        return "open_knowledge"
    if any(marker in value for marker in COMMERCIAL_MARKERS):
        return "commercial_or_blog"
    return "general_web"


def evidence_tier(quality: str) -> str:
    if quality == "official":
        return "high"
    if quality in {"open_knowledge", "general_web"}:
        return "medium"
    if quality in {"commercial_or_blog", "weak_social_or_forum"}:
        return "low"
    return "missing"


def tier_rank(tier: str) -> int:
    return {"high": 3, "medium": 2, "low": 1, "missing": 0}.get(tier, 0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean TravelEval niche QA into a paper-ready gold dataset.")
    parser.add_argument("--input", default="travel_benchmark_niche_backup.csv")
    parser.add_argument("--output", default="data_collection/research_gold_niche.csv")
    parser.add_argument("--audit-output", default="data_collection/source_quality_audit.csv")
    parser.add_argument("--min-tier", choices=["missing", "low", "medium", "high"], default="medium")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    df = df.drop_duplicates(subset=["prompt"]).copy()

    if "country" not in df.columns:
        df["country"] = ""
    df["country"] = [
        infer_country(str(prompt), str(country))
        for prompt, country in zip(df["prompt"], df["country"])
    ]
    df["source_quality"] = df["source_url"].map(source_quality)
    df["evidence_tier"] = df["source_quality"].map(evidence_tier)
    df["task_category"] = "Niche-Verification"

    ordered_cols = [
        "id",
        "prompt",
        "task_category",
        "region",
        "country",
        "ground_truth",
        "source_url",
        "source_quality",
        "evidence_tier",
    ]
    for col in ordered_cols:
        if col not in df.columns:
            df[col] = ""
    df = df[ordered_cols]

    audit = (
        df.groupby(["source_quality", "evidence_tier"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(["evidence_tier", "source_quality"])
    )

    min_rank = tier_rank(args.min_tier)
    clean = df[df["evidence_tier"].map(tier_rank) >= min_rank].copy()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(output_path, index=False)

    audit_path = Path(args.audit_output)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(audit_path, index=False)

    print(f"Input rows: {len(df)}")
    print(f"Clean rows with tier >= {args.min_tier}: {len(clean)}")
    print(f"Wrote {output_path}")
    print(f"Wrote {audit_path}")


if __name__ == "__main__":
    main()
