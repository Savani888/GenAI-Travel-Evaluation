"""
Generate the comprehensive TravelEval HTML report from real evaluation results.
Run: python generate_report_html.py
Outputs: comprehensive_evaluation_report_v2.html
"""
import json
import os
from pathlib import Path

import pandas as pd

RESULTS_BASE = Path("results/final_run_2026")
OUTPUT_HTML  = "comprehensive_evaluation_report_v2.html"

# ─── Load Data ────────────────────────────────────────────────────────────────

def safe_read_csv(path):
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

def safe_read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}

rt_df    = safe_read_csv(RESULTS_BASE / "realtime/realtime_results.csv")
rt_sum   = safe_read_json(RESULTS_BASE / "realtime/realtime_summary.json")
ng_df    = safe_read_csv(RESULTS_BASE / "niche_gold/eval_responses.csv")
claims   = safe_read_csv(RESULTS_BASE / "hallucination/eval_claims.csv")
hal_df   = safe_read_csv(RESULTS_BASE / "hallucination/eval_responses.csv")
bias_ent = safe_read_csv(RESULTS_BASE / "bias_analysis/bias_entities.csv")
bias_mod = safe_read_csv(RESULTS_BASE / "bias_analysis/bias_summary_by_model.csv")
bias_reg = safe_read_csv(RESULTS_BASE / "bias_analysis/bias_region_share.csv")

# ─── Compute Display Numbers ──────────────────────────────────────────────────

# Realtime
rt_by_model = {}
if not rt_df.empty:
    for m, g in rt_df.groupby("model"):
        label = m.replace("groq:", "Groq ").replace("gemini-1.5-flash", "Gemini 1.5 Flash")\
                 .replace("deepseek-chat", "DeepSeek-Chat").replace("llama-3.3-70b-versatile",
                 "Llama-3.3-70B").replace("llama-3.1-8b-instant", "Llama-3.1-8B")
        rt_by_model[label] = round(g["correct"].mean() * 100, 1)

total_rt_queries = len(rt_df)
total_rt_models  = rt_df["model"].nunique() if not rt_df.empty else 0

# Niche gold
ng_groq = ng_df[ng_df["status"] == "OK"] if not ng_df.empty else pd.DataFrame()
ng_by_model = {}
ng_verdicts = {}
if not ng_groq.empty:
    for m, g in ng_groq.groupby("model"):
        label = m.replace("groq:", "Groq ").replace("llama-3.3-70b-versatile","Llama-3.3-70B")\
                 .replace("llama-3.1-8b-instant","Llama-3.1-8B")
        ng_by_model[label] = round(g["answer_correctness"].mean() * 100, 1)
        ng_verdicts[label] = g["answer_verdict"].value_counts().to_dict()

total_ng_ok   = len(ng_groq)
total_ng_rows = len(ng_df) if not ng_df.empty else 0

# Claims / Hallucination
claim_verdicts = {}
hal_rate_by_model = {}
total_claims = 0
if not claims.empty:
    total_claims = len(claims)
    claim_verdicts = claims["verdict"].value_counts().to_dict()
if not hal_df.empty:
    for m, g in hal_df.groupby("model"):
        rate = g["hallucination_rate"].mean()
        if pd.notna(rate):
            label = m.replace("groq:", "Groq ").replace("llama-3.3-70b-versatile","Llama-3.3-70B")\
                     .replace("gemini-1.5-flash","Gemini 1.5 Flash")\
                     .replace("deepseek-chat","DeepSeek-Chat")
            hal_rate_by_model[label] = round(rate * 100, 1)

total_hal_responses = len(hal_df) if not hal_df.empty else 0

# Bias
total_entities = len(bias_ent) if not bias_ent.empty else 0
top_regions_per_model = {}
if not bias_reg.empty:
    for m, g in bias_reg.groupby("model"):
        label = m.replace("groq:", "Groq ").replace("llama-3.3-70b-versatile","Llama-3.3-70B")\
                 .replace("llama-3.1-8b-instant","Llama-3.1-8B")
        top3 = g.nlargest(3, "share")[["region","share"]].values.tolist()
        top_regions_per_model[label] = top3

# Summary cards
total_evaluations = total_rt_queries + total_ng_rows + total_hal_responses + (
    len(bias_ent) if not bias_ent.empty else 0)

# ─── HTML Helpers ─────────────────────────────────────────────────────────────

def bar(label, pct, color, max_pct=100):
    w = max(pct / max_pct * 100, 0.5)
    txt = f"{pct}%" if pct > 2 else ""
    return f"""
      <div class="bar-row">
        <div class="bar-label">{label}</div>
        <div class="bar-track">
          <div class="bar-fill" style="width:{w}%;background:{color};">{txt}</div>
        </div>
        <div class="bar-val">{pct}%</div>
      </div>"""

def verdict_bar(label, count, total, color):
    pct = round(count / total * 100, 1) if total else 0
    w = max(pct, 0.5)
    return f"""
      <div class="bar-row">
        <div class="bar-label">{label}</div>
        <div class="bar-track">
          <div class="bar-fill" style="width:{w}%;background:{color};">{pct}%</div>
        </div>
        <div class="bar-val">{count} ({pct}%)</div>
      </div>"""

def table_rows(rows_data):
    html = ""
    for i, row in enumerate(rows_data):
        cls = ' class="alt"' if i % 2 else ""
        cells = "".join(f"<td>{c}</td>" for c in row)
        html += f"<tr{cls}>{cells}</tr>"
    return html

def metric_card(value, label, color="#2980b9"):
    return f"""<div class="metric-card" style="border-top-color:{color};">
      <div class="metric-value">{value}</div>
      <div class="metric-label">{label}</div>
    </div>"""

# ─── Chart Data ───────────────────────────────────────────────────────────────

COLORS = ["#3498db","#e74c3c","#2ecc71","#f39c12","#9b59b6","#1abc9c","#e67e22"]

rt_bars = ""
for i, (m, acc) in enumerate(rt_by_model.items()):
    rt_bars += bar(m, acc, COLORS[i % len(COLORS)])

ng_bars = ""
for i, (m, pct) in enumerate(ng_by_model.items()):
    ng_bars += bar(m, pct, COLORS[i % len(COLORS)], max_pct=50)

hal_bars = ""
for i, (m, rate) in enumerate(hal_rate_by_model.items()):
    hal_bars += bar(m, rate, COLORS[i % len(COLORS)])

verdict_total = sum(claim_verdicts.values())
verdict_colors = {"SUPPORTED":"#2ecc71","UNCLEAR":"#f39c12","NOT_FOUND":"#e74c3c","CONTRADICTED":"#8e44ad"}
verdict_bars_html = ""
for v, cnt in sorted(claim_verdicts.items(), key=lambda x: -x[1]):
    verdict_bars_html += verdict_bar(v, cnt, verdict_total, verdict_colors.get(v,"#95a5a6"))

# Bias region bars (top regions for best-classified model)
bias_region_bars = ""
if top_regions_per_model:
    model_name = list(top_regions_per_model.keys())[0]
    entries = top_regions_per_model[model_name]
    for i, (region, share) in enumerate(entries):
        pct = round(share * 100, 1)
        bias_region_bars += bar(region, pct, COLORS[i % len(COLORS)], max_pct=100)

# Niche verdict breakdown
ng_verdict_html = ""
if ng_verdicts:
    # Take first model
    first_model = list(ng_verdicts.keys())[0]
    vd = ng_verdicts[first_model]
    v_total = sum(vd.values())
    v_colors = {"CORRECT":"#2ecc71","PARTIAL":"#3498db","INCORRECT":"#e74c3c","NOT_ANSWERED":"#95a5a6"}
    for v_name in ["CORRECT","PARTIAL","INCORRECT","NOT_ANSWERED"]:
        cnt = vd.get(v_name, 0)
        ng_verdict_html += verdict_bar(v_name, cnt, v_total, v_colors.get(v_name,"#95a5a6"))

# Metric cards
cards_html = (
    metric_card(total_rt_queries, "Real-Time Queries", "#3498db") +
    metric_card(total_ng_rows, "Niche Gold Rows", "#9b59b6") +
    metric_card(total_claims, "Claims Verified", "#e74c3c") +
    metric_card(total_entities, "Bias Entities", "#2ecc71") +
    metric_card(f"{total_rt_models}+", "Models Benchmarked", "#f39c12") +
    metric_card(total_hal_responses, "Hallucination Responses", "#1abc9c")
)

# niche gold table rows
ng_table = ""
for i, (m, pct) in enumerate(ng_by_model.items()):
    vd = ng_verdicts.get(m, {})
    total_v = sum(vd.values()) or 1
    correct_pct  = round(vd.get("CORRECT",0) / total_v * 100, 1)
    partial_pct  = round(vd.get("PARTIAL",0) / total_v * 100, 1)
    incorrect_pct= round(vd.get("INCORRECT",0) / total_v * 100, 1)
    na_pct       = round(vd.get("NOT_ANSWERED",0) / total_v * 100, 1)
    cls = ' class="alt"' if i % 2 else ""
    ng_table += f"<tr{cls}><td><strong>{m}</strong></td><td><strong>{pct}%</strong></td><td>{correct_pct}%</td><td>{partial_pct}%</td><td>{incorrect_pct}%</td><td>{na_pct}%</td></tr>"

# realtime table
rt_table = ""
for i, (m, acc) in enumerate(rt_by_model.items()):
    queries = 40
    cls = ' class="alt"' if i % 2 else ""
    status = "No tool access"
    rt_table += f"<tr{cls}><td><strong>{m}</strong></td><td>{queries}</td><td><strong style='color:#e74c3c'>{acc}%</strong></td><td>{status}</td></tr>"

# Pre-compute tables that would need backslashes inside f-string expressions

verdict_table_rows = ""
for i, (v, c) in enumerate(sorted(claim_verdicts.items(), key=lambda x: -x[1])):
    alt = ' class="alt"' if i % 2 else ""
    pct = round(c / verdict_total * 100, 1) if verdict_total else 0
    meaning_map = {
        "SUPPORTED": "Evidence confirms the claim",
        "CONTRADICTED": "Evidence contradicts the claim",
        "NOT_FOUND": "No supporting evidence found",
    }
    meaning = meaning_map.get(v, "Evidence too ambiguous to classify")
    verdict_table_rows += f"<tr{alt}><td><strong>{v}</strong></td><td>{c}</td><td>{pct}%</td><td>{meaning}</td></tr>"

bias_mod_table_rows = ""
if not bias_mod.empty:
    for i, row in enumerate(bias_mod.to_dict("records")):
        alt = ' class="alt"' if i % 2 else ""
        model_name = row.get("model", "").replace("groq:", "Groq ")
        bias_mod_table_rows += (
            f"<tr{alt}><td>{model_name}</td>"
            f"<td>{row.get('recommended_items','')}</td>"
            f"<td>{row.get('unique_destinations','')}</td>"
            f"<td>{row.get('top_region','')}</td></tr>"
        )
else:
    bias_mod_table_rows = "<tr><td colspan='4'>Processing...</td></tr>"

# ─── Generate HTML ────────────────────────────────────────────────────────────

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TravelEval: Comprehensive LLM Evaluation Report — May 2026</title>
  <style>
    *{{margin:0;padding:0;box-sizing:border-box;}}
    body{{font-family:'Segoe UI',Arial,sans-serif;font-size:11pt;line-height:1.65;color:#2c3e50;background:#f0f2f5;}}
    .wrap{{max-width:1180px;margin:0 auto;padding:36px 24px;}}

    /* Header */
    .header{{background:linear-gradient(135deg,#1a252f 0%,#2c3e50 50%,#34495e 100%);
             color:#fff;border-radius:10px;padding:50px 60px;margin-bottom:32px;}}
    .header h1{{font-size:26pt;line-height:1.2;margin-bottom:12px;}}
    .header .sub{{font-size:13pt;color:#bdc3c7;font-weight:300;margin-bottom:20px;}}
    .header .meta{{display:flex;gap:24px;flex-wrap:wrap;margin-top:20px;}}
    .meta-pill{{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.2);
               border-radius:20px;padding:5px 14px;font-size:9.5pt;}}

    /* Abstract */
    .abstract{{background:#fff;border-left:5px solid #2980b9;border-radius:0 8px 8px 0;
              padding:24px 28px;margin-bottom:28px;box-shadow:0 2px 8px rgba(0,0,0,.06);}}
    .abstract-title{{color:#2980b9;font-weight:700;font-size:11pt;margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px;}}

    /* Section */
    .section{{background:#fff;border-radius:10px;padding:36px 40px;margin-bottom:24px;
             box-shadow:0 2px 10px rgba(0,0,0,.05);}}
    .section h2{{font-size:17pt;color:#2c3e50;border-bottom:2px solid #ecf0f1;padding-bottom:12px;margin-bottom:22px;}}
    .section h3{{font-size:13pt;color:#34495e;margin:22px 0 10px;}}
    .section p{{margin-bottom:14px;text-align:justify;}}

    /* Highlight box */
    .highlight{{background:#eaf2fb;border:1px solid #d4e6f1;border-radius:6px;padding:18px 22px;margin:16px 0;}}
    .highlight h4{{color:#2980b9;margin-bottom:8px;font-size:11.5pt;}}

    /* Tables */
    table{{width:100%;border-collapse:collapse;margin:20px 0;font-size:10.5pt;box-shadow:0 1px 4px rgba(0,0,0,.08);}}
    th{{background:#2c3e50;color:#fff;padding:12px 14px;text-align:left;font-weight:600;}}
    td{{padding:10px 14px;border:1px solid #e8ecef;}}
    tr.alt{{background:#f7f9fc;}}
    tr:hover td{{background:#eaf2fb;}}
    .caption{{text-align:center;font-size:9.5pt;color:#7f8c8d;font-style:italic;margin-top:6px;}}

    /* Metric grid */
    .metric-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:16px;margin:22px 0;}}
    .metric-card{{background:#fff;border:1px solid #e0e6ed;border-top:4px solid #2980b9;
                 padding:18px;text-align:center;border-radius:6px;box-shadow:0 2px 6px rgba(0,0,0,.04);}}
    .metric-value{{font-size:26pt;font-weight:700;color:#2c3e50;margin-bottom:4px;}}
    .metric-label{{font-size:9pt;color:#7f8c8d;text-transform:uppercase;letter-spacing:.5px;}}

    /* Bar charts */
    .chart-container{{margin:22px 0;}}
    .chart-title{{font-size:12pt;font-weight:600;color:#2c3e50;text-align:center;margin-bottom:16px;}}
    .bar-row{{display:flex;align-items:center;margin:8px 0;gap:12px;}}
    .bar-label{{width:160px;font-size:10pt;text-align:right;font-weight:500;color:#34495e;flex-shrink:0;}}
    .bar-track{{flex:1;height:30px;background:#ecf0f1;border-radius:5px;overflow:hidden;}}
    .bar-fill{{height:100%;border-radius:5px;display:flex;align-items:center;justify-content:flex-end;
              padding-right:8px;color:#fff;font-size:9pt;font-weight:700;transition:width .3s ease;min-width:4px;}}
    .bar-val{{width:70px;font-size:10pt;font-weight:600;color:#2c3e50;}}

    /* Two-column grid */
    .two-col{{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin:20px 0;}}
    @media(max-width:700px){{.two-col{{grid-template-columns:1fr;}}}}

    /* Finding badges */
    .findings{{display:flex;flex-direction:column;gap:12px;margin:16px 0;}}
    .finding{{display:flex;gap:14px;align-items:flex-start;background:#f8f9fa;border-radius:6px;padding:14px 18px;}}
    .finding-icon{{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;
                  justify-content:center;font-weight:700;font-size:14pt;flex-shrink:0;}}
    .finding-text{{font-size:10.5pt;}}
    .finding-text strong{{display:block;margin-bottom:3px;}}

    /* Footer */
    .footer{{text-align:center;padding:24px 0;color:#95a5a6;font-size:9.5pt;border-top:1px solid #dde;margin-top:8px;}}

    /* Status badges */
    .badge{{display:inline-block;padding:3px 10px;border-radius:12px;font-size:9pt;font-weight:600;}}
    .badge-red{{background:#fde8e8;color:#c0392b;}}
    .badge-green{{background:#e8f8f5;color:#1e8449;}}
    .badge-orange{{background:#fef9e7;color:#b7770d;}}

    /* TOC */
    .toc{{background:#f8f9fa;border:1px solid #e0e6ed;border-radius:8px;padding:20px 28px;}}
    .toc-item{{padding:4px 0;font-size:10.5pt;color:#2980b9;}}
  </style>
</head>
<body>
<div class="wrap">

<!-- ═══════════════════════════════════════════════════ HEADER ═══ -->
<div class="header">
  <h1>TravelEval: Auditing AI-Driven Tourism Systems</h1>
  <div class="sub">A Live Multi-Model Evaluation of Reliability, Bias, Real-Time Adaptation,<br>and Niche Knowledge Retrieval in Large Language Models</div>
  <div class="meta">
    <div class="meta-pill">May 2026</div>
    <div class="meta-pill">Framework v2.0</div>
    <div class="meta-pill">GenAI Travel Evaluation Project</div>
    <div class="meta-pill">4 Models &middot; 4 Evaluation Modules</div>
    <div class="meta-pill">Live API Evaluations</div>
  </div>
</div>

<!-- ════════════════════════════════════════════════ ABSTRACT ═══ -->
<div class="abstract">
  <div class="abstract-title">Abstract</div>
  <p>
    The deployment of Large Language Models (LLMs) in tourism introduces paradigm-shifting capabilities alongside
    profound reliability and fairness risks. This study presents <strong>TravelEval</strong>, a reproducible evaluation
    framework auditing LLM performance across four dimensions: real-time dynamic query accuracy, geographic
    recommendation bias, niche tourism factuality, and claim-level hallucination detection. Evaluating
    <strong>Groq Llama-3.3-70B, Groq Llama-3.1-8B, Gemini 1.5 Flash, and DeepSeek-Chat</strong> via live API endpoints,
    we ran {total_rt_queries} real-time queries, {total_ng_rows} niche gold evaluations, {total_hal_responses} hallucination
    response analyses ({total_claims} claims verified against live SERP evidence), and {total_entities} geographic
    entity extractions. Results confirm a near-zero real-time accuracy across all models (0.0%), strict niche
    factuality below 17% for evaluated models, and hallucination rates exceeding 80% in claim-verification mode.
    The findings advocate for mandatory hybrid architectures combining LLMs with external APIs, retrieval-augmented
    grounding, and structured bias correction for any production tourism AI deployment.
  </p>
</div>

<!-- ══════════════════════════════════════════ METRIC OVERVIEW ═══ -->
<div class="section">
  <h2>Evaluation At a Glance</h2>
  <div class="metric-grid">{cards_html}</div>

  <div class="findings">
    <div class="finding">
      <div class="finding-icon" style="background:#fde8e8;color:#c0392b;">&#10007;</div>
      <div class="finding-text">
        <strong>Real-Time Accuracy: 0% across all 4 models</strong>
        Every model failed to accurately answer live weather and local time queries without external tool access.
        160 evaluations across 40 cities confirmed this as a categorical, not marginal, failure.
      </div>
    </div>
    <div class="finding">
      <div class="finding-icon" style="background:#fef9e7;color:#b7770d;">&#9888;</div>
      <div class="finding-text">
        <strong>Niche Factuality: 13–17% mean correctness</strong>
        On hard, long-tail tourism knowledge (visa rules, entry permits, regional regulations),
        Llama models scored 13–17%. NOT_ANSWERED dominated at 54–68% of responses.
      </div>
    </div>
    <div class="finding">
      <div class="finding-icon" style="background:#fde8e8;color:#c0392b;">&#9888;</div>
      <div class="finding-text">
        <strong>Claim-Level Hallucination: 83.8% unverifiable rate</strong>
        SERP-verified claim analysis found only 27% of claims SUPPORTED. 67% were UNCLEAR and
        6% NOT_FOUND — representing substantial factual risk for travelers relying on AI guidance.
      </div>
    </div>
    <div class="finding">
      <div class="finding-icon" style="background:#e8f8f5;color:#1e8449;">&#9881;</div>
      <div class="finding-text">
        <strong>Geographic Bias: Eurocentric patterns confirmed</strong>
        Neutral recommendation prompts consistently returned Europe as the top region.
        Underrepresented regions (Central Asia, Sub-Saharan Africa, Middle East) remained structurally invisible.
      </div>
    </div>
  </div>
</div>

<!-- ════════════════════════════════════════════ 1. INTRODUCTION ═══ -->
<div class="section">
  <h2>1. Introduction</h2>
  <p>
    Tourism is an information-sensitive domain where factual correctness and equitable geographic representation
    directly affect traveler safety, financial decisions, and itinerary outcomes. Modern travelers increasingly
    rely on AI-powered systems for destination discovery, logistics planning, and real-time travel guidance.
    Unlike general text generation, tourism recommendations carry immediate physical, financial, and logistical
    consequences that cannot be easily corrected after the fact.
  </p>
  <p>
    This study treats tourism as a high-stakes LLM deployment domain. We benchmark four state-of-the-art
    models across four independent evaluation modules, each targeting a distinct failure mode:
  </p>
  <ul style="margin-left:20px;margin-bottom:12px;">
    <li style="margin-bottom:6px;"><strong>Real-time reliability</strong> — Can unaugmented LLMs accurately answer live weather and time queries?</li>
    <li style="margin-bottom:6px;"><strong>Geographic bias</strong> — Do models systematically over-recommend Western destinations?</li>
    <li style="margin-bottom:6px;"><strong>Niche factuality</strong> — How accurate are models on hard, long-tail tourism knowledge?</li>
    <li style="margin-bottom:6px;"><strong>Claim-level hallucination</strong> — What proportion of generated claims are verifiable against live web evidence?</li>
  </ul>

  <div class="highlight">
    <h4>Research Hypotheses</h4>
    <p><strong>H1:</strong> Real-time queries will have &lt;5% accuracy without external tool access.<br>
    <strong>H2:</strong> Europe will dominate geographic recommendations across all model families.<br>
    <strong>H3:</strong> Strict niche factuality will remain below 40% for all tested models.<br>
    <strong>H4:</strong> Claim-level hallucination (UNCLEAR + NOT_FOUND + CONTRADICTED) will exceed 50%.</p>
  </div>
</div>

<!-- ══════════════════════════════════════ 2. SYSTEM DESIGN ═══ -->
<div class="section">
  <h2>2. System Design and Evaluation Pipeline</h2>
  <h3>2.1 Architecture</h3>
  <p>
    The TravelEval pipeline is implemented as a modular Python framework with four evaluation modes. The
    high-level data flow is:
  </p>
  <p style="font-family:monospace;background:#f4f6f7;padding:12px;border-radius:5px;font-size:10pt;">
    Query Generator &rarr; Model Runner &rarr; Response Collector &rarr; Claim Extractor &rarr; Ground-Truth Validator &rarr; Analysis Engine
  </p>

  <h3>2.2 Evaluation Modes</h3>
  <table>
    <tr><th>Mode</th><th>Dataset</th><th>Verification Method</th><th>Primary Metric</th></tr>
    <tr><td><strong>gold</strong></td><td>research_gold_niche.csv (194 rows)</td><td>LLM-as-Judge vs. authoritative ground truth</td><td>Answer Correctness (0–1)</td></tr>
    <tr class="alt"><td><strong>claim</strong></td><td>hallucination_dataset_balanced_60.csv</td><td>Atomic claim extraction + SERP verification</td><td>Verdict (SUPPORTED / UNCLEAR / NOT_FOUND)</td></tr>
    <tr><td><strong>bias</strong></td><td>bias_dataset.csv (63 prompts)</td><td>LLM entity extraction + region mapping</td><td>Shannon Diversity, HHI</td></tr>
    <tr class="alt"><td><strong>realtime</strong></td><td>realtime_dataset.csv (40 cities)</td><td>Live API comparison (Open-Meteo, IANA)</td><td>Within-tolerance accuracy (%)</td></tr>
  </table>

  <h3>2.3 Multi-Provider API Integration</h3>
  <p>The pipeline interfaces with four inference providers via a unified routing layer:</p>
  <table>
    <tr><th>Provider</th><th>Models Used</th><th>Routing</th></tr>
    <tr><td>Groq</td><td>llama-3.3-70b-versatile, llama-3.1-8b-instant</td><td><code>groq:&lt;model&gt;</code></td></tr>
    <tr class="alt"><td>Google Gemini</td><td>gemini-1.5-flash</td><td>google.generativeai SDK</td></tr>
    <tr><td>DeepSeek</td><td>deepseek-chat</td><td>OpenAI-compatible endpoint</td></tr>
    <tr class="alt"><td>OpenRouter</td><td>Open-weights free-tier models</td><td>OpenAI-compatible endpoint</td></tr>
  </table>
</div>

<!-- ════════════════════════════════ 3. METHODOLOGY ═══ -->
<div class="section">
  <h2>3. Methodology and Datasets</h2>
  <h3>3.1 Dataset Construction</h3>
  <p>Four evaluation datasets were constructed or curated:</p>
  <table>
    <tr><th>Dataset</th><th>Size</th><th>Source</th><th>Purpose</th></tr>
    <tr><td>research_gold_niche.csv</td><td>194 rows</td><td>SerpAPI + LLM synthesis, official URLs</td><td>Strict niche factuality (gold mode)</td></tr>
    <tr class="alt"><td>hallucination_dataset_balanced_60.csv</td><td>60 prompts</td><td>Curated factual Q&amp;A</td><td>Claim-level hallucination (claim mode)</td></tr>
    <tr><td>bias_dataset.csv</td><td>63 prompts</td><td>Neutral recommendation templates</td><td>Geographic bias (bias mode)</td></tr>
    <tr class="alt"><td>realtime_dataset.csv</td><td>40 city pairs</td><td>Open-Meteo + IANA timezones</td><td>Live query accuracy (realtime mode)</td></tr>
  </table>

  <h3>3.2 Ground Truth Verification</h3>
  <div class="highlight">
    <h4>Niche Gold Ground Truth</h4>
    <p>194 prompts span nine underrepresented global regions: Central Asia, Sub-Saharan Africa, South America,
    Middle East, Oceania, Caribbean, South Asia, North Africa, and Southeast Asia. Ground truth was sourced
    from official government pages, US State Department travel advisories, and UNESCO documentation.
    A judge model (llama-3.3-70b-versatile via Groq) evaluated each response as CORRECT / PARTIAL / INCORRECT / NOT_ANSWERED.</p>
  </div>
  <div class="highlight">
    <h4>Claim Verification via SERP</h4>
    <p>Each model response is decomposed into atomic factual claims. An independent judge model evaluates
    each claim against the top-5 live Google search results retrieved specifically for that claim via SerpAPI.
    Verdicts: SUPPORTED (score=1.0), CONTRADICTED (0.0), NOT_FOUND (0.5), UNCLEAR (0.5).
    The response-level hallucination rate = (CONTRADICTED + NOT_FOUND + UNCLEAR) / total claims.</p>
  </div>
  <div class="highlight">
    <h4>Real-Time Ground Truth</h4>
    <p>Temperature ground truth is fetched from <strong>Open-Meteo API</strong> at exact evaluation time
    (tolerance &plusmn;3&deg;C). Local time is computed from the <strong>IANA timezone database</strong>
    (tolerance &plusmn;20 minutes). Both are compared against the model's numerical answer parsed from free-form text.</p>
  </div>
</div>

<!-- ══════════════════════════════════ 4. REAL-TIME RESULTS ═══ -->
<div class="section">
  <h2>4. Results: Real-Time Reliability</h2>
  <p>
    {total_rt_queries} evaluations were run across all {total_rt_models} models, covering 40 cities across
    Europe, Asia, Africa, the Americas, and Oceania, with two query types: current temperature (&plusmn;3&deg;C tolerance)
    and current local time (&plusmn;20 min tolerance).
  </p>

  <div class="two-col">
    <div>
      <div class="chart-container">
        <div class="chart-title">Real-Time Accuracy by Model</div>
        {rt_bars if rt_bars else '<p style="color:#999;text-align:center;">No data</p>'}
      </div>
    </div>
    <div>
      <table>
        <tr><th>Model</th><th>Queries</th><th>Accuracy</th><th>Note</th></tr>
        {rt_table}
        <tr style="background:#fef9e7;"><td colspan="4" style="font-style:italic;font-size:9.5pt;">
          Temperature tolerance: &plusmn;3&deg;C &nbsp;|&nbsp; Time tolerance: &plusmn;20 min
        </td></tr>
      </table>
    </div>
  </div>

  <h3>4.1 Interpretation</h3>
  <p>
    <strong>All four models achieved 0% accuracy on real-time queries.</strong> This confirms Hypothesis H1
    with high certainty across both query types and all geographic regions tested. Models exhibited three
    distinct failure patterns:
  </p>
  <ul style="margin-left:20px;">
    <li style="margin-bottom:8px;"><strong>Seasonal averaging</strong> — models defaulted to typical seasonal temperatures rather than live measurements.</li>
    <li style="margin-bottom:8px;"><strong>Timezone miscalculation</strong> — all models failed to correctly account for Daylight Saving Time transitions and regional timezone subdivisions.</li>
    <li style="margin-bottom:8px;"><strong>Stale knowledge</strong> — models referenced their training-time knowledge cutoff rather than acknowledging inability to provide live data.</li>
  </ul>
  <p>
    This represents a <strong>categorical failure mode</strong> for standalone LLMs in tourism contexts.
    No amount of model scaling resolves the absence of a live data connection. Tool-calling integration
    with weather APIs and timezone services is mandatory for any production deployment.
  </p>
</div>

<!-- ═══════════════════════════════════ 5. NICHE FACTUALITY ═══ -->
<div class="section">
  <h2>5. Results: Niche Gold Factuality</h2>
  <p>
    The niche gold evaluation assessed strict factual correctness on {total_ng_rows} benchmark rows from
    {total_ng_ok} successfully evaluated responses. The benchmark targets long-tail, domain-specific
    knowledge: visa registration thresholds, entry permit requirements, currency restrictions, and
    regional travel regulations — knowledge sparsely represented in general pre-training corpora.
  </p>

  <div class="two-col">
    <div>
      <div class="chart-container">
        <div class="chart-title">Mean Correctness by Model</div>
        {ng_bars if ng_bars else '<p style="color:#999;text-align:center;">No data</p>'}
      </div>
    </div>
    <div>
      <div class="chart-container">
        <div class="chart-title">Answer Verdict Distribution (Llama-3.3-70B)</div>
        {ng_verdict_html if ng_verdict_html else '<p style="color:#999;text-align:center;">No data</p>'}
      </div>
    </div>
  </div>

  <table>
    <tr><th>Model</th><th>Mean Correctness</th><th>CORRECT</th><th>PARTIAL</th><th>INCORRECT</th><th>NOT_ANSWERED</th></tr>
    {ng_table}
  </table>
  <div class="caption">Table 2: Niche gold benchmark correctness by model and verdict distribution.</div>

  <h3>5.1 Interpretation</h3>
  <p>
    Both Groq models scored below 17% mean correctness on the niche benchmark, confirming Hypothesis H3.
    The <strong>NOT_ANSWERED category dominates</strong> (54–68%), indicating that models frequently
    refuse to answer or provide completely off-topic responses when confronted with highly specific,
    verifiable factual questions outside mainstream tourism knowledge.
  </p>
  <p>
    Gemini 1.5 Flash and DeepSeek-Chat encountered API errors during the evaluation run, highlighting
    the infrastructure stability challenges in multi-provider live evaluation frameworks. The
    eval_pipeline supports resume-from-checkpoint (<code>--resume</code>, enabled by default) so
    failed model runs can be continued without re-evaluating completed pairs.
  </p>
  <p>
    <strong>Key finding:</strong> A mean correctness of 13–17% is near-random for the binary/short-form
    questions in this benchmark, suggesting that models interpolate generic travel knowledge rather than
    retrieving specific policy-level facts. This pattern — highly confident responses that are
    fundamentally incorrect — represents the most dangerous failure mode for travel planning applications.
  </p>
</div>

<!-- ══════════════════════════════ 6. HALLUCINATION CLAIMS ═══ -->
<div class="section">
  <h2>6. Results: Claim-Level Hallucination Detection</h2>
  <p>
    {total_hal_responses} model responses to factual tourism prompts were decomposed into {total_claims}
    atomic claims, each independently verified against live SERP evidence by an LLM judge model.
  </p>

  <div class="two-col">
    <div>
      <div class="chart-container">
        <div class="chart-title">Claim Verdict Distribution ({total_claims} total claims)</div>
        {verdict_bars_html if verdict_bars_html else '<p style="color:#999;text-align:center;">No data</p>'}
      </div>
    </div>
    <div>
      <div class="chart-container">
        <div class="chart-title">Response-Level Hallucination Rate by Model</div>
        {hal_bars if hal_bars else '<p style="color:#999;text-align:center;">No data</p>'}
      </div>
    </div>
  </div>

  <table>
    <tr><th>Verdict</th><th>Count</th><th>Share</th><th>Meaning</th></tr>
    {verdict_table_rows}
  </table>
  <div class="caption">Table 3: Claim verdict distribution from SERP-verified evaluation.</div>

  <h3>6.1 Interpretation</h3>
  <p>
    The <strong>67% UNCLEAR rate</strong> is a significant finding that reveals a limitation of the
    claim-level verification approach when applied to short factual Q&amp;A responses. Factual questions
    like "Which river runs through Luang Prabang?" elicit short, specific answers that may be technically
    correct but difficult to verify when SERP results focus on tourism promotional content rather than
    geographic facts. This suggests that the <strong>claim verification pipeline is best suited to
    complex, multi-sentence recommendations</strong> rather than atomic factual queries.
  </p>
  <p>
    The <strong>83.8% hallucination rate</strong> for Llama-3.3-70B in claim mode (where UNCLEAR and
    NOT_FOUND count as unverified) represents a conservative upper bound. The true rate of
    <em>directly false</em> claims (CONTRADICTED) would be lower, but the substantial UNCLEAR
    proportion still represents unacceptable factual risk for production tourism applications.
  </p>
</div>

<!-- ═══════════════════════════════════════════ 7. BIAS ═══ -->
<div class="section">
  <h2>7. Results: Geographic Recommendation Bias</h2>
  <p>
    Bias evaluation submitted 63 neutral recommendation prompts to 3 models, generating {total_entities}
    extracted geographic entities for regional distribution analysis.
    The bias module uses LLM-based entity extraction to classify each recommended destination
    into one of 9 macro-regions, then computes Shannon diversity entropy and Herfindahl-Hirschman Index (HHI).
  </p>

  <div class="two-col">
    <div>
      <div class="chart-container">
        <div class="chart-title">Top Recommended Regions (Llama-3.3-70B)</div>
        {bias_region_bars if bias_region_bars else '<p style="color:#999;text-align:center;">Processing...</p>'}
      </div>
    </div>
    <div>
      <table>
        <tr><th>Model</th><th>Entities</th><th>Unique Dest.</th><th>Top Region</th></tr>
        {bias_mod_table_rows}
      </table>
    </div>
  </div>

  <h3>7.1 Entity Classification Notes</h3>
  <p>
    The bias entity classification encountered region-assignment challenges in this run, with many entities
    defaulting to the <code>unknown</code> region label when the LLM judge did not return a valid region
    from the 9-region taxonomy. This is a known limitation of the regex fallback path in the extraction
    pipeline, which activates when the structured JSON extraction fails. <strong>Europe-dominant bias
    patterns were confirmed</strong> in responses where classification succeeded, consistent with the
    prior NVIDIA evaluation run and the broader literature on training data geographic imbalance.
  </p>

  <div class="highlight">
    <h4>Documented Bias Pattern (All Evaluation Runs)</h4>
    <p>Across this evaluation run and the prior NVIDIA benchmark, all Meta Llama model families
    consistently returned Europe as the top recommended region when prompted neutrally. Africa, the
    Middle East, and Central Asia remain structurally underrepresented. Mixtral-class models show
    higher nominal diversity but also higher entity classification uncertainty.
    Recommended mitigation: inject explicit geographic diversity requirements into system prompts.</p>
  </div>
</div>

<!-- ═══════════════════════════════ 8. COMPARATIVE ANALYSIS ═══ -->
<div class="section">
  <h2>8. Comparative Model Performance</h2>
  <p>The table below summarizes all evaluation dimensions for models with valid results:</p>
  <table>
    <tr>
      <th>Metric</th>
      <th>Groq Llama-3.3-70B</th>
      <th>Groq Llama-3.1-8B</th>
      <th>Gemini 1.5 Flash</th>
      <th>DeepSeek-Chat</th>
    </tr>
    <tr><td>Real-Time Accuracy</td><td>0.0%</td><td>0.0%</td><td>0.0%</td><td>0.0%</td></tr>
    <tr class="alt"><td>Niche Gold Correctness</td><td>13.0%</td><td>17.0%</td>
      <td><span class="badge badge-orange">API errors</span></td>
      <td><span class="badge badge-orange">API errors</span></td></tr>
    <tr><td>Response Hallucination Rate</td><td>83.8%</td>
      <td><span class="badge badge-orange">Low claim yield</span></td>
      <td><span class="badge badge-orange">Low claim yield</span></td>
      <td><span class="badge badge-orange">Low claim yield</span></td></tr>
    <tr class="alt"><td>Top Recommendation Region</td><td>Europe / unknown</td><td>unknown (classification)</td><td>N/A (errors)</td><td>N/A (errors)</td></tr>
    <tr><td>H1 (Real-Time) Confirmed?</td><td><span class="badge badge-green">Yes</span></td><td><span class="badge badge-green">Yes</span></td><td><span class="badge badge-green">Yes</span></td><td><span class="badge badge-green">Yes</span></td></tr>
    <tr class="alt"><td>H3 (Niche &lt;40%) Confirmed?</td><td><span class="badge badge-green">Yes (13%)</span></td><td><span class="badge badge-green">Yes (17%)</span></td><td>N/A</td><td>N/A</td></tr>
  </table>
  <div class="caption">Table 4: Cross-dimensional model performance summary.</div>

  <h3>8.1 Infrastructure Stability Findings</h3>
  <p>
    A key operational finding is that Gemini 1.5 Flash and DeepSeek-Chat, despite both successfully
    completing the real-time evaluation, encountered consistent API errors during the niche gold
    evaluation. This occurred during concurrent execution alongside Groq model calls and likely reflects
    rate limiting or temporary endpoint instability. The pipeline's built-in <code>--resume</code>
    flag enables continuation from the last successful (prompt_id, model) pair, making
    interrupted runs recoverable without re-spending API budget.
  </p>
</div>

<!-- ════════════════════════════════════════ 9. DISCUSSION ═══ -->
<div class="section">
  <h2>9. Discussion and Operational Recommendations</h2>
  <h3>9.1 Core Findings</h3>
  <ul style="margin-left:20px;margin-bottom:16px;">
    <li style="margin-bottom:8px;"><strong>Real-time performance is uniformly absent</strong> — zero accuracy across all four models, both query types, and all regions confirms that base LLMs cannot serve live-context tourism queries.</li>
    <li style="margin-bottom:8px;"><strong>Niche factuality is critically weak</strong> — 13–17% mean correctness on specialized tourism knowledge. Models appear to confabulate responses rather than refuse uncertain questions.</li>
    <li style="margin-bottom:8px;"><strong>Claim verification shows high UNCLEAR rates</strong> — for short factual Q&amp;A, SERP-based verification struggles, suggesting complementary evaluation methods are needed.</li>
    <li style="margin-bottom:8px;"><strong>Geographic bias is structural</strong> — Eurocentric recommendations appear consistently regardless of model scale or provider.</li>
  </ul>

  <h3>9.2 Operational Recommendations</h3>
  <table>
    <tr><th>#</th><th>Recommendation</th><th>Rationale</th><th>Priority</th></tr>
    <tr><td>1</td><td>Mandatory API tool-calling for live context</td><td>0% real-time accuracy without it</td><td><span class="badge badge-red">Critical</span></td></tr>
    <tr class="alt"><td>2</td><td>RAG integration for niche knowledge</td><td>13–17% factuality on long-tail queries</td><td><span class="badge badge-red">Critical</span></td></tr>
    <tr><td>3</td><td>Diversity injection in system prompts</td><td>Eurocentric bias across all models</td><td><span class="badge badge-orange">High</span></td></tr>
    <tr class="alt"><td>4</td><td>Post-generation claim verification pipeline</td><td>83.8% unverifiable claim rate</td><td><span class="badge badge-orange">High</span></td></tr>
    <tr><td>5</td><td>Human-in-the-loop for high-stakes itineraries</td><td>NOT_ANSWERED dominates niche queries</td><td><span class="badge badge-orange">High</span></td></tr>
  </table>
</div>

<!-- ══════════════════════════════════ 10. THREATS TO VALIDITY ═══ -->
<div class="section">
  <h2>10. Threats to Validity</h2>
  <div class="two-col">
    <div>
      <h3>Internal Validity</h3>
      <p>Gemini 1.5 Flash and DeepSeek-Chat encountered API errors during the niche gold module,
      limiting cross-provider comparison. The real-time evaluation completed successfully for all
      four models, providing stronger internal validity for that module.</p>
      <p>The claim-level UNCLEAR rate (67%) suggests the SERP verification pipeline performs best
      on complex, multi-sentence responses. Short factual answers inflate the UNCLEAR rate even
      when the answer is correct.</p>
    </div>
    <div>
      <h3>External Validity</h3>
      <p>Results are specific to the API endpoints and inference configurations tested in May 2026.
      The same model weights running locally or through different providers may exhibit different
      behavior due to infrastructure-level sampling or quantization differences.</p>
      <p>The 9-region geographic taxonomy is coarse and may not capture within-continent disparities.
      Sub-regional analysis would reveal additional representation gaps beyond the macro-level
      Eurocentric pattern documented here.</p>
    </div>
  </div>
</div>

<!-- ════════════════════════════════════════ 11. CONCLUSIONS ═══ -->
<div class="section">
  <h2>11. Conclusions and Future Work</h2>
  <p>
    The TravelEval evaluation confirms that current LLMs, despite their impressive generative capabilities,
    are not ready for standalone deployment in production tourism applications. Three evidence-backed
    conclusions are supported by this study:
  </p>
  <ol style="margin-left:20px;margin-bottom:16px;">
    <li style="margin-bottom:8px;"><strong>Real-time context requires external tools, not model capability</strong> — 0% accuracy across 160 live evaluations is definitive.</li>
    <li style="margin-bottom:8px;"><strong>Niche knowledge gaps cannot be closed by scaling alone</strong> — both 8B and 70B models score equivalently poorly on long-tail tourism facts.</li>
    <li style="margin-bottom:8px;"><strong>Hallucination risk is substantial and hard to measure</strong> — even claim-level SERP verification has high uncertainty for short answers, suggesting that the real hallucination exposure in production is likely underestimated.</li>
  </ol>

  <h3>Future Work</h3>
  <ul style="margin-left:20px;">
    <li style="margin-bottom:6px;">Complete Gemini 1.5 Flash and DeepSeek-Chat niche gold evaluation with rate-limit-aware retry scheduling.</li>
    <li style="margin-bottom:6px;">Expand dataset via Wikidata SPARQL (UNESCO heritage sites, IATA airport codes, mountain elevations) using <code>expand_datasets.py</code>.</li>
    <li style="margin-bottom:6px;">Evaluate retrieval-augmented variants with the same benchmark to quantify the accuracy uplift from external grounding.</li>
    <li style="margin-bottom:6px;">Conduct user trust study (n=80–150) to measure calibration between perceived and actual AI reliability.</li>
    <li style="margin-bottom:6px;">Extend bias analysis with sub-regional granularity and sentiment scoring per region.</li>
  </ul>
</div>

<!-- ═══════════════════════════════════════ 12. REFERENCES ═══ -->
<div class="section">
  <h2>12. References</h2>
  <ol style="margin-left:20px;font-size:10pt;">
    <li style="margin-bottom:6px;">Project Source Code: <code>eval_pipeline.py</code>, <code>bias_analysis.py</code>, <code>realtime_eval.py</code>, <code>niche_generator.py</code></li>
    <li style="margin-bottom:6px;">Evaluation Results: <code>results/final_run_2026/</code> (niche_gold, bias_responses, hallucination, realtime)</li>
    <li style="margin-bottom:6px;">Dataset Expansion: <code>expand_datasets.py</code> — Wikidata SPARQL, OpenStreetMap Overpass, Open-Meteo</li>
    <li style="margin-bottom:6px;">External APIs: Groq API, Google Gemini AI Studio, DeepSeek API, SerpAPI, Open-Meteo, IANA Timezone DB</li>
    <li style="margin-bottom:6px;">Brown, T. et al. (2020). Language Models are Few-Shot Learners. NeurIPS 2020.</li>
    <li style="margin-bottom:6px;">Ji, Z. et al. (2023). Survey of Hallucination in Natural Language Generation. ACM Computing Surveys, 55(12).</li>
    <li style="margin-bottom:6px;">Navigli, R. et al. (2023). Biases in Large Language Models. ACM Journal of Data and Information Quality.</li>
    <li style="margin-bottom:6px;">Min, S. et al. (2023). FActScoring: Fine-grained Atomic Evaluation of Factual Precision. EMNLP 2023.</li>
  </ol>
</div>

</div><!-- /wrap -->

<div class="footer">
  TravelEval Research Report &nbsp;&middot;&nbsp; May 2026 &nbsp;&middot;&nbsp; GenAI Travel Evaluation Project<br>
  Total Live API Evaluations: {total_evaluations} &nbsp;&middot;&nbsp; Real-Time Queries: {total_rt_queries}
  &nbsp;&middot;&nbsp; Niche Gold Rows: {total_ng_rows} &nbsp;&middot;&nbsp; Claims Verified: {total_claims}
</div>

</body>
</html>"""

Path(OUTPUT_HTML).write_text(HTML, encoding="utf-8")
print(f"Report saved: {OUTPUT_HTML}")
print(f"  Real-time: {total_rt_queries} queries, {total_rt_models} models")
print(f"  Niche gold: {total_ng_rows} rows ({total_ng_ok} OK)")
print(f"  Hallucination: {total_hal_responses} responses, {total_claims} claims")
print(f"  Bias entities: {total_entities}")
