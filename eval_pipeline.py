import argparse
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from dotenv import load_dotenv
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

try:
    from textblob import TextBlob
except ImportError:
    TextBlob = None

load_dotenv()

SERP_API_KEY = os.getenv("SERP_API_KEY")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY") or os.getenv("NVIDIA_KEY")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

DEFAULT_MODELS = [
    "deepseek-chat",
    "gemini-1.5-flash",
    "meta-llama/llama-3-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
]
DEFAULT_JUDGE_MODEL = os.getenv("JUDGE_MODEL", "llama-3.3-70b-versatile")
DEFAULT_OUTPUT_DIR = "results"
DEFAULT_MAX_TOKENS = 256
CACHE_DIR = Path(".cache") / "traveleval"

_clients: Dict[str, Any] = {}

POSITIVE_WORDS = {
    "beautiful",
    "excellent",
    "friendly",
    "good",
    "great",
    "impressive",
    "reliable",
    "safe",
    "stunning",
    "welcoming",
}
NEGATIVE_WORDS = {
    "bad",
    "dangerous",
    "difficult",
    "poor",
    "risky",
    "unsafe",
    "unreliable",
    "violent",
    "warning",
    "worse",
}


class ProviderConfigError(RuntimeError):
    """Raised when a requested provider is missing its API key or package."""


def sentiment_score(text: str) -> float:
    if not text:
        return 0.0
    if TextBlob is not None:
        return float(TextBlob(text).sentiment.polarity)

    tokens = re.findall(r"[a-z]+", text.lower())
    if not tokens:
        return 0.0
    positive = sum(1 for token in tokens if token in POSITIVE_WORDS)
    negative = sum(1 for token in tokens if token in NEGATIVE_WORDS)
    return (positive - negative) / len(tokens)


def _json_load(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _json_save(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _cache_key(*parts: Any) -> str:
    raw = json.dumps(parts, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_json_object(text: str) -> Dict[str, Any]:
    clean = _strip_json_fence(text)
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", clean, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _get_openai_client(provider: str) -> Any:
    if provider in _clients:
        return _clients[provider]

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ProviderConfigError("Install openai to use OpenRouter, DeepSeek, or NVIDIA models.") from exc

    if provider == "openrouter":
        if not OPENROUTER_KEY:
            raise ProviderConfigError("OPENROUTER_KEY is missing from .env.")
        _clients[provider] = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_KEY)
    elif provider == "deepseek":
        if not DEEPSEEK_KEY:
            raise ProviderConfigError("DEEPSEEK_KEY is missing from .env.")
        _clients[provider] = OpenAI(base_url="https://api.deepseek.com/v1", api_key=DEEPSEEK_KEY)
    elif provider == "nvidia":
        if not NVIDIA_API_KEY:
            raise ProviderConfigError("NVIDIA_API_KEY or NVIDIA_KEY is missing from .env.")
        _clients[provider] = OpenAI(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY)
    else:
        raise ProviderConfigError(f"Unknown OpenAI-compatible provider: {provider}")

    return _clients[provider]


def _get_groq_client() -> Any:
    if "groq" in _clients:
        return _clients["groq"]
    if not GROQ_API_KEY:
        raise ProviderConfigError("GROQ_API_KEY is missing from .env.")
    try:
        from groq import Groq
    except ImportError as exc:
        raise ProviderConfigError("Install groq to use judge/extraction models.") from exc
    _clients["groq"] = Groq(api_key=GROQ_API_KEY)
    return _clients["groq"]


def _get_gemini() -> Any:
    if "gemini" in _clients:
        return _clients["gemini"]
    if not GEMINI_API_KEY:
        raise ProviderConfigError("GEMINI_API_KEY is missing from .env.")
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise ProviderConfigError("Install google-generativeai to use Gemini models.") from exc
    genai.configure(api_key=GEMINI_API_KEY)
    _clients["gemini"] = genai
    return genai


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(4),
    retry=retry_if_exception_type(Exception),
)
def call_llm(prompt: str, model: str, dry_run: bool = False, max_tokens: int = DEFAULT_MAX_TOKENS) -> str:
    """Call the requested model with deterministic settings where supported."""
    if dry_run:
        return (
            "Dry-run response. This row exercises the pipeline without calling a model. "
            f"Prompt summary: {prompt[:180]}"
        )

    if model.startswith("gemini"):
        genai = _get_gemini()
        response = genai.GenerativeModel(model).generate_content(
            prompt,
            generation_config={"temperature": 0.0, "max_output_tokens": max_tokens},
        )
        return getattr(response, "text", "") or ""

    if model.startswith("deepseek"):
        client = _get_openai_client("deepseek")
        response = client.chat.completions.create(
            model=model,
            temperature=0.0,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""

    if model.startswith("groq:"):
        groq_model = model.split(":", 1)[1]
        client = _get_groq_client()
        response = client.chat.completions.create(
            model=groq_model,
            temperature=0.0,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""

    if model.startswith("nvidia:"):
        nvidia_model = model.split(":", 1)[1]
        client = _get_openai_client("nvidia")
        response = client.chat.completions.create(
            model=nvidia_model,
            temperature=0.0,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""

    if ":" in model or "/" in model:
        client = _get_openai_client("openrouter")
        response = client.chat.completions.create(
            model=model,
            temperature=0.0,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            extra_headers={
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "TravelEval",
            },
        )
        return response.choices[0].message.content or ""

    raise ProviderConfigError(
        f"Unsupported model '{model}'. Use deepseek*, gemini*, groq:<model>, nvidia:<model>, or OpenRouter names."
    )


def call_judge_json(prompt: str, judge_model: str, dry_run: bool = False) -> Dict[str, Any]:
    """Call the configured judge model and parse a JSON object."""
    if dry_run:
        return {"verdict": "UNCLEAR", "score": 0.0, "rationale": "Dry-run judge output."}

    if judge_model.startswith("groq:"):
        judge_model = judge_model.split(":", 1)[1]

    if judge_model.startswith("nvidia:"):
        model_name = judge_model.split(":", 1)[1]
        client = _get_openai_client("nvidia")
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model_name,
            temperature=0.0,
            max_tokens=DEFAULT_MAX_TOKENS,
        )
        return _parse_json_object(response.choices[0].message.content or "{}")

    if judge_model.startswith("deepseek"):
        client = _get_openai_client("deepseek")
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=judge_model,
            temperature=0.0,
            max_tokens=DEFAULT_MAX_TOKENS,
        )
        return _parse_json_object(response.choices[0].message.content or "{}")

    if judge_model.startswith("gemini"):
        genai = _get_gemini()
        response = genai.GenerativeModel(judge_model).generate_content(
            prompt,
            generation_config={"temperature": 0.0, "max_output_tokens": DEFAULT_MAX_TOKENS},
        )
        return _parse_json_object(getattr(response, "text", "") or "{}")

    if ":" in judge_model or "/" in judge_model:
        client = _get_openai_client("openrouter")
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=judge_model,
            temperature=0.0,
            max_tokens=DEFAULT_MAX_TOKENS,
            extra_headers={
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "TravelEval",
            },
        )
        return _parse_json_object(response.choices[0].message.content or "{}")

    client = _get_groq_client()
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=judge_model,
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    return _parse_json_object(response.choices[0].message.content or "{}")


def regex_extract_claims(response: str) -> List[str]:
    if not isinstance(response, str) or not response.strip() or response == "ERROR":
        return []

    chunks = re.split(r"(?<=[.!?])\s+|\n+", response)
    claims = []
    for chunk in chunks:
        clean = re.sub(r"^\s*[-*0-9.)]+\s*", "", chunk.strip())
        if len(clean) >= 25 and any(char.isalpha() for char in clean):
            claims.append(clean)
    return claims[:20]


def llm_extract_claims(
    response: str,
    prompt: str,
    judge_model: str,
    dry_run: bool = False,
) -> List[str]:
    if dry_run:
        return regex_extract_claims(response)
    if not GROQ_API_KEY:
        return regex_extract_claims(response)

    cache_path = CACHE_DIR / "claim_extraction" / f"{_cache_key(prompt, response, judge_model)}.json"
    cached = _json_load(cache_path, None)
    if cached is not None:
        return [str(claim).strip() for claim in cached.get("claims", []) if str(claim).strip()]

    extraction_prompt = f"""
You are preparing a factuality benchmark for tourism AI.

Original user prompt:
{prompt}

Model response:
{response}

Extract only atomic, externally verifiable factual claims from the response.
Do not include opinions, preferences, vague advice, or repeated claims.
Split compound claims into separate claims.

Return JSON with this schema:
{{
  "claims": ["single factual claim", "..."]
}}
"""
    try:
        data = call_judge_json(extraction_prompt, judge_model=judge_model, dry_run=dry_run)
        claims = [str(claim).strip() for claim in data.get("claims", []) if str(claim).strip()]
        claims = claims[:25]
        _json_save(cache_path, {"claims": claims})
        return claims
    except Exception as exc:
        print(f"Claim extraction fell back to regex: {exc}")
        return regex_extract_claims(response)


def search_evidence(query: str, num_results: int, dry_run: bool = False) -> List[Dict[str, str]]:
    if dry_run:
        return [{"title": "Dry-run source", "link": "dry-run://source", "snippet": "No live search used."}]
    if not SERP_API_KEY:
        raise ProviderConfigError("SERP_API_KEY is missing from .env.")

    cache_path = CACHE_DIR / "serp" / f"{_cache_key(query, num_results)}.json"
    cached = _json_load(cache_path, None)
    if cached is not None:
        return cached

    try:
        from serpapi import GoogleSearch
    except ImportError as exc:
        raise ProviderConfigError("Install google-search-results to use SerpAPI search.") from exc

    params = {
        "engine": "google",
        "q": query,
        "api_key": SERP_API_KEY,
        "num": num_results,
    }
    results = GoogleSearch(params).get_dict()
    evidence = []
    for item in results.get("organic_results", [])[:num_results]:
        evidence.append(
            {
                "title": str(item.get("title", "")),
                "link": str(item.get("link", "")),
                "snippet": str(item.get("snippet", "")),
            }
        )
    _json_save(cache_path, evidence)
    return evidence


def _format_evidence(evidence: List[Dict[str, str]]) -> str:
    lines = []
    for index, item in enumerate(evidence, start=1):
        lines.append(
            f"[{index}] Title: {item.get('title', '')}\n"
            f"URL: {item.get('link', '')}\n"
            f"Snippet: {item.get('snippet', '')}"
        )
    return "\n\n".join(lines)


def judge_claim_against_evidence(
    claim: str,
    prompt: str,
    evidence: List[Dict[str, str]],
    judge_model: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    cache_path = CACHE_DIR / "claim_judgments" / f"{_cache_key(claim, prompt, evidence, judge_model)}.json"
    cached = _json_load(cache_path, None)
    if cached is not None:
        return cached

    judge_prompt = f"""
You are a strict fact-checking judge for a tourism LLM benchmark.

User prompt:
{prompt}

Claim to verify:
{claim}

Evidence snippets:
{_format_evidence(evidence)}

Classify the claim using only the evidence above:
- SUPPORTED: evidence clearly supports the claim.
- CONTRADICTED: evidence clearly says the claim is false.
- NOT_FOUND: evidence is relevant but does not contain enough support.
- UNCLEAR: evidence is too ambiguous or low quality to decide.

Return JSON only:
{{
  "verdict": "SUPPORTED|CONTRADICTED|NOT_FOUND|UNCLEAR",
  "score": 1.0,
  "rationale": "brief reason"
}}
Use score 1 for SUPPORTED, 0 for CONTRADICTED, and 0.5 for NOT_FOUND or UNCLEAR.
"""
    try:
        data = call_judge_json(judge_prompt, judge_model=judge_model, dry_run=dry_run)
    except Exception as exc:
        data = {"verdict": "UNCLEAR", "score": 0.5, "rationale": f"Judge error: {exc}"}

    verdict = str(data.get("verdict", "UNCLEAR")).upper()
    if verdict not in {"SUPPORTED", "CONTRADICTED", "NOT_FOUND", "UNCLEAR"}:
        verdict = "UNCLEAR"
    score = {"SUPPORTED": 1.0, "CONTRADICTED": 0.0, "NOT_FOUND": 0.5, "UNCLEAR": 0.5}[verdict]
    result = {
        "verdict": verdict,
        "score": float(data.get("score", score) if data.get("score") is not None else score),
        "rationale": str(data.get("rationale", "")),
    }
    _json_save(cache_path, result)
    return result


def judge_answer_against_ground_truth(
    prompt: str,
    response: str,
    ground_truth: str,
    source_url: str,
    judge_model: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    cache_path = CACHE_DIR / "answer_judgments" / f"{_cache_key(prompt, response, ground_truth, source_url, judge_model)}.json"
    cached = _json_load(cache_path, None)
    if cached is not None:
        return cached

    judge_prompt = f"""
You are grading a tourism benchmark answer against a known gold answer.

Question:
{prompt}

Gold answer:
{ground_truth}

Gold source URL:
{source_url or "not provided"}

Model answer:
{response}

Return JSON only:
{{
  "verdict": "CORRECT|PARTIAL|INCORRECT|NOT_ANSWERED",
  "score": 1.0,
  "rationale": "brief reason"
}}
Score CORRECT as 1, PARTIAL as 0.5, INCORRECT and NOT_ANSWERED as 0.
"""
    try:
        data = call_judge_json(judge_prompt, judge_model=judge_model, dry_run=dry_run)
    except Exception as exc:
        data = {"verdict": "NOT_ANSWERED", "score": 0.0, "rationale": f"Judge error: {exc}"}

    verdict = str(data.get("verdict", "NOT_ANSWERED")).upper()
    if verdict not in {"CORRECT", "PARTIAL", "INCORRECT", "NOT_ANSWERED"}:
        verdict = "NOT_ANSWERED"
    default_score = {"CORRECT": 1.0, "PARTIAL": 0.5, "INCORRECT": 0.0, "NOT_ANSWERED": 0.0}[verdict]
    result = {
        "verdict": verdict,
        "score": float(data.get("score", default_score) if data.get("score") is not None else default_score),
        "rationale": str(data.get("rationale", "")),
    }
    _json_save(cache_path, result)
    return result


def normalize_dataset(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for index, row in df.iterrows():
        row_dict = row.to_dict()
        prompt = str(row_dict.get("prompt", "")).strip()
        if not prompt:
            continue

        task = row_dict.get("task_category", row_dict.get("category", "unknown"))
        region = row_dict.get("region", row_dict.get("region_target", "unknown"))
        destination = row_dict.get("destination", row_dict.get("country", row_dict.get("city", "")))

        rows.append(
            {
                "id": str(row_dict.get("id", row_dict.get("prompt_id", f"ROW-{index + 1:04d}"))),
                "prompt": prompt,
                "task": "" if pd.isna(task) else str(task),
                "region": "" if pd.isna(region) else str(region),
                "destination": "" if pd.isna(destination) else str(destination),
                "ground_truth": "" if pd.isna(row_dict.get("ground_truth", "")) else str(row_dict.get("ground_truth", "")),
                "source_url": "" if pd.isna(row_dict.get("source_url", "")) else str(row_dict.get("source_url", "")),
                "raw_category": "" if pd.isna(row_dict.get("category", "")) else str(row_dict.get("category", "")),
            }
        )
    return pd.DataFrame(rows)


def infer_mode(row: pd.Series, requested_mode: str) -> str:
    if requested_mode != "auto":
        return requested_mode
    category = f"{row.get('task', '')} {row.get('raw_category', '')}".lower()
    if str(row.get("ground_truth", "")).strip():
        return "gold"
    if "neutral_recommendation" in category or "bias" in category:
        return "bias"
    return "claim"


def build_evidence_query(claim: str, row: pd.Series) -> str:
    context = " ".join(
        part
        for part in [str(row.get("destination", "")), str(row.get("region", ""))]
        if part and part.lower() != "unknown"
    )
    return f"{claim} {context} travel official source".strip()


def claim_counts(claim_rows: List[Dict[str, Any]]) -> Tuple[int, int, int, int, int]:
    total = len(claim_rows)
    supported = sum(1 for item in claim_rows if item["verdict"] == "SUPPORTED")
    contradicted = sum(1 for item in claim_rows if item["verdict"] == "CONTRADICTED")
    not_found = sum(1 for item in claim_rows if item["verdict"] == "NOT_FOUND")
    unclear = sum(1 for item in claim_rows if item["verdict"] == "UNCLEAR")
    return total, supported, contradicted, not_found, unclear


class TravelEvalPipeline:
    def __init__(
        self,
        dataset_path: str,
        output_dir: str,
        mode: str,
        judge_model: str,
        serp_results: int,
        claim_extractor: str,
        dry_run: bool,
        resume: bool,
        max_tokens: int,
    ) -> None:
        self.dataset_path = dataset_path
        self.dataset = normalize_dataset(pd.read_csv(dataset_path))
        self.output_dir = Path(output_dir)
        self.mode = mode
        self.judge_model = judge_model
        self.serp_results = serp_results
        self.claim_extractor = claim_extractor
        self.dry_run = dry_run
        self.resume = resume
        self.max_tokens = max_tokens

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.response_path = self.output_dir / "eval_responses.csv"
        self.claim_path = self.output_dir / "eval_claims.csv"
        self.summary_path = self.output_dir / "eval_summary.json"

    def _completed_keys(self) -> set:
        if not self.resume or not self.response_path.exists():
            return set()
        existing = pd.read_csv(self.response_path)
        if not {"prompt_id", "model"}.issubset(existing.columns):
            return set()
        return set(zip(existing["prompt_id"].astype(str), existing["model"].astype(str)))

    def _append_csv(self, path: Path, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        df = pd.DataFrame(rows)
        df.to_csv(path, mode="a", header=not path.exists(), index=False)

    def _extract_claims(self, response: str, prompt: str) -> List[str]:
        if self.claim_extractor == "regex":
            return regex_extract_claims(response)
        if self.claim_extractor == "none":
            return []
        return llm_extract_claims(response, prompt, judge_model=self.judge_model, dry_run=self.dry_run)

    def evaluate_response(self, row: pd.Series, response: str, model_name: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        eval_mode = infer_mode(row, self.mode)
        claim_rows: List[Dict[str, Any]] = []
        answer_verdict = ""
        answer_correctness: Optional[float] = None
        answer_rationale = ""

        if eval_mode == "gold":
            answer = judge_answer_against_ground_truth(
                prompt=row["prompt"],
                response=response,
                ground_truth=row["ground_truth"],
                source_url=row["source_url"],
                judge_model=self.judge_model,
                dry_run=self.dry_run,
            )
            answer_verdict = answer["verdict"]
            answer_correctness = float(answer["score"])
            answer_rationale = answer["rationale"]
            claim_rows.append(
                {
                    "prompt_id": row["id"],
                    "model": model_name,
                    "claim_index": 1,
                    "claim": f"Answer to: {row['prompt']}",
                    "verdict": "SUPPORTED" if answer_correctness >= 1 else "CONTRADICTED",
                    "score": answer_correctness,
                    "evidence_query": "",
                    "evidence_urls": row["source_url"],
                    "rationale": answer_rationale,
                }
            )
        elif eval_mode == "claim":
            claims = self._extract_claims(response, row["prompt"])
            for claim_index, claim in enumerate(claims, start=1):
                query = build_evidence_query(claim, row)
                evidence = search_evidence(query, num_results=self.serp_results, dry_run=self.dry_run)
                judgment = judge_claim_against_evidence(
                    claim=claim,
                    prompt=row["prompt"],
                    evidence=evidence,
                    judge_model=self.judge_model,
                    dry_run=self.dry_run,
                )
                claim_rows.append(
                    {
                        "prompt_id": row["id"],
                        "model": model_name,
                        "claim_index": claim_index,
                        "claim": claim,
                        "verdict": judgment["verdict"],
                        "score": judgment["score"],
                        "evidence_query": query,
                        "evidence_urls": " | ".join(item.get("link", "") for item in evidence),
                        "rationale": judgment["rationale"],
                    }
                )

        total, supported, contradicted, not_found, unclear = claim_counts(claim_rows)
        unsupported = contradicted + not_found + unclear
        hallucination_rate = unsupported / total if total else None
        if eval_mode == "gold" and answer_correctness is not None:
            hallucination_rate = 1.0 - answer_correctness

        response_row = {
            "prompt_id": row["id"],
            "prompt": row["prompt"],
            "task": row["task"],
            "region": row["region"],
            "destination": row["destination"],
            "model": model_name,
            "evaluation_mode": eval_mode,
            "response": response,
            "status": "ERROR" if response == "ERROR" else "OK",
            "total_claims": total,
            "supported_claims": supported,
            "contradicted_claims": contradicted,
            "not_found_claims": not_found,
            "unclear_claims": unclear,
            "hallucination_rate": hallucination_rate,
            "answer_correctness": answer_correctness,
            "answer_verdict": answer_verdict,
            "answer_rationale": answer_rationale,
            "sentiment_score": sentiment_score(response),
            "source_url": row["source_url"],
            "ground_truth": row["ground_truth"],
        }
        return response_row, claim_rows

    def run(self, models: List[str], limit: Optional[int], start: int, sleep_seconds: float) -> Dict[str, Any]:
        dataset = self.dataset.iloc[start:].copy()
        if limit is not None:
            dataset = dataset.head(limit)

        completed = self._completed_keys()
        print(f"Loaded {len(self.dataset)} normalized rows from {self.dataset_path}.")
        print(f"Running {len(dataset)} rows x {len(models)} model(s). Outputs: {self.output_dir}")

        for model_name in models:
            print(f"\n--- Evaluating {model_name} ---")
            for _, row in dataset.iterrows():
                key = (str(row["id"]), model_name)
                if key in completed:
                    print(f"Skipping completed {row['id']} / {model_name}")
                    continue

                try:
                    response = call_llm(
                        row["prompt"],
                        model=model_name,
                        dry_run=self.dry_run,
                        max_tokens=self.max_tokens,
                    )
                    if sleep_seconds > 0:
                        time.sleep(sleep_seconds)
                except Exception as exc:
                    print(f"Model call failed for {row['id']} / {model_name}: {exc}")
                    response = "ERROR"

                response_row, claim_rows = self.evaluate_response(row, response, model_name)
                self._append_csv(self.response_path, [response_row])
                self._append_csv(self.claim_path, claim_rows)
                completed.add(key)

        summary = self.compute_summary_metrics()
        _json_save(self.summary_path, summary)
        return summary

    def compute_summary_metrics(self) -> Dict[str, Any]:
        if not self.response_path.exists():
            return {"status": "No data processed."}

        df = pd.read_csv(self.response_path)
        summary: Dict[str, Any] = {"total_responses": int(len(df))}

        if "hallucination_rate" in df.columns:
            metric = df.dropna(subset=["hallucination_rate"])
            if not metric.empty:
                summary["hallucination_rate_by_model"] = (
                    metric.groupby("model")["hallucination_rate"].mean().round(4).to_dict()
                )
                summary["hallucination_rate_by_region"] = (
                    metric.groupby("region")["hallucination_rate"].mean().round(4).to_dict()
                )

        if "answer_correctness" in df.columns:
            metric = df.dropna(subset=["answer_correctness"])
            if not metric.empty:
                summary["answer_correctness_by_model"] = (
                    metric.groupby("model")["answer_correctness"].mean().round(4).to_dict()
                )

        summary["sentiment_by_region"] = df.groupby("region")["sentiment_score"].mean().round(4).to_dict()
        return summary


def parse_models(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Evidence-backed TravelEval pipeline.")
    parser.add_argument("--dataset", default="travel_benchmark.csv", help="Input CSV dataset.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory for response/claim outputs.")
    parser.add_argument(
        "--models",
        default=",".join(DEFAULT_MODELS),
        help="Comma-separated models. Supports deepseek*, gemini*, groq:<model>, nvidia:<model>, and OpenRouter IDs.",
    )
    parser.add_argument("--mode", choices=["auto", "gold", "claim", "bias"], default="auto")
    parser.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL)
    parser.add_argument("--serp-results", type=int, default=5)
    parser.add_argument("--claim-extractor", choices=["llm", "regex", "none"], default="llm")
    parser.add_argument("--limit", type=int, default=None, help="Optional max rows to evaluate.")
    parser.add_argument("--start", type=int, default=0, help="Start row offset.")
    parser.add_argument("--sleep", type=float, default=0.0, help="Seconds to sleep after each model call.")
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS, help="Max tokens for model responses.")
    parser.add_argument("--dry-run", action="store_true", help="Exercise pipeline without external API calls.")
    parser.add_argument("--no-resume", action="store_true", help="Do not skip prompt/model pairs already in output.")
    args = parser.parse_args()

    pipeline = TravelEvalPipeline(
        dataset_path=args.dataset,
        output_dir=args.output_dir,
        mode=args.mode,
        judge_model=args.judge_model,
        serp_results=args.serp_results,
        claim_extractor=args.claim_extractor,
        dry_run=args.dry_run,
        resume=not args.no_resume,
        max_tokens=args.max_tokens,
    )
    summary = pipeline.run(
        models=parse_models(args.models),
        limit=args.limit,
        start=args.start,
        sleep_seconds=args.sleep,
    )
    print("\n--- TRAVEL EVAL SUMMARY ---")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
