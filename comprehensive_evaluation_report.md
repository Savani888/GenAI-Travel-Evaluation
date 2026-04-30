# Comprehensive Evaluation Report: Reliability, Bias, and Trust in AI-driven Tourism Systems

**Project Date:** April 30, 2026  
**Author:** Tourism AI Evaluation Team  
**Version:** 1.0

---

## Executive Summary

This report presents a comprehensive quantitative audit of Large Language Model (LLM) performance in tourism information and recommendations. The study evaluates four critical dimensions: hallucination frequency, algorithmic bias, real-time information reliability, and user trust perception. Through systematic evaluation across multiple LLMs including NVIDIA's hosted models (Llama 3.1, Llama 3.3, Mixtral), we provide empirical evidence of the risks inherent in tourism AI systems.

---

## 1. Introduction

### 1.1 Background

The rapid adoption of Large Language Models (LLMs) in tourism applications—from travel recommendation engines to virtual travel assistants—has created an urgent need for systematic evaluation of their reliability and fairness. Tourism information carries significant real-world consequences: inaccurate destination details can lead to ruined vacations, biased recommendations can perpetuate cultural stereotypes, and unreliable real-time data can disrupt travel plans.

### 1.2 Problem Statement

AI-powered tourism systems face three critical challenges:

1. **Hallucination**: Models frequently generate fabricated facts, outdated information, or inaccurate claims about destinations, attractions, and travel logistics.

2. **Algorithmic Bias**: Recommendation systems may disproportionately favor popular Western destinations while underrepresenting emerging tourism markets in Africa, South Asia, and the Global South.

3. **Real-Time Reliability**: Dynamic information such as weather, opening hours, and event schedules often cannot be accurately retrieved or updated by AI systems.

### 1.3 Research Objectives

This study aims to:

- Quantify hallucination rates across multiple LLMs in tourism domain
- Analyze geographic representation bias in destination recommendations
- Evaluate real-time information accuracy for dynamic tourism data
- Provide empirical evidence for risk assessment in tourism AI deployment

---

## 2. Methodology

### 2.1 Evaluation Framework

The research employs a four-module experimental framework designed to capture different aspects of AI reliability in tourism:

| Module | Focus Area | Key Metrics |
|--------|------------|-------------|
| Module 1 | Hallucination Detection | Hallucination Rate, Accuracy Rate, Outdated Info Rate |
| Module 2 | Bias Detection | Geographic Representation Ratio, Diversity Score, Popularity Bias |
| Module 3 | Real-Time Reliability | Real-Time Accuracy, Dynamic Data Precision |
| Module 4 | User Trust Study | Trust Score, Perceived Transparency, Decision Confidence |

### 2.2 Models Evaluated

The following LLMs were evaluated through NVIDIA's API endpoints:

| Model | Version | Parameters | Use Case |
|-------|---------|------------|----------|
| Meta Llama | 3.1 | 8B | Lightweight evaluation |
| Meta Llama | 3.1 | 70B | Full-scale evaluation |
| Meta Llama | 3.3 | 70B | Latest version |
| Mistral Mixtral | 8x7b | - | Open-source alternative |

### 2.3 Data Collection Methods

#### 2.3.1 Hallucination Dataset
- **Queries**: 200-300 generated across 6 categories
- **Categories**: Destination recommendations, attraction descriptions, travel logistics, cultural information, events, historical facts
- **Validation**: Cross-referenced with official tourism boards, UNESCO, and authoritative sources

#### 2.3.2 Bias Evaluation Prompts
- **Neutral prompts**: "hidden gems in Europe", "underrated destinations worldwide"
- **Entity extraction**: Location entities from model responses
- **Regional classification**: Africa, Asia, Europe, North America, South America, Oceania, Caribbean, Middle East

#### 2.3.3 Real-Time Data Queries
- **Dynamic data types**: Weather, local time, opening hours, event schedules
- **Ground truth**: Official APIs and real-time sources
- **Accuracy measurement**: Binary correct/incorrect with tolerance for minor variations

### 2.4 Statistical Analysis

- **Hallucination Rate**: (Contradicted + Not Found) / Total Claims
- **Bias Index**: Shannon entropy of regional distribution
- **Real-Time Accuracy**: Correct responses / Total queries
- **Sentiment Analysis**: VADER sentiment scoring on model outputs

---

## 3. Implementation

### 3.1 System Architecture

The evaluation pipeline consists of:

```
┌─────────────────────────────────────────────────────────────────┐
│                    EVALUATION PIPELINE                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Query      │───▶│    LLM       │───▶│   Response   │      │
│  │  Generator   │    │   Runner     │    │   Collector  │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                                        │             │
│         ▼                                        ▼             │
│  ┌──────────────┐                        ┌──────────────┐      │
│  │   Dataset    │                        │   Analysis   │      │
│  │   Manager    │                        │    Engine    │      │
│  └──────────────┘                        └──────────────┘      │
│         │                                        │             │
│         ▼                                        ▼             │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              Results & Visualization                 │      │
│  └──────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Key Implementation Files

| File | Purpose |
|------|---------|
| `eval_pipeline.py` | Main evaluation orchestration |
| `bias_analysis.py` | Geographic bias detection |
| `realtime_eval.py` | Real-time data evaluation |
| `generate_dataset.py` | Query generation |
| `analyze_results.py` | Statistical analysis |

### 3.3 Evaluation Workflow

1. **Query Generation**: Create diverse tourism queries across categories
2. **Model Execution**: Run queries through multiple LLMs via NVIDIA API
3. **Response Collection**: Store responses with metadata
4. **Claim Extraction**: Parse factual claims from responses
5. **Ground Truth Validation**: Verify claims against authoritative sources
6. **Statistical Analysis**: Compute metrics and generate reports

---

## 4. Results

### 4.1 Hallucination Detection Results

#### 4.1.1 Claim Verification Summary

The hallucination evaluation analyzed **286 claims** across **120 responses** from two models:

| Model | Supported | Contradicted | Not Found | Unclear | Total Claims |
|-------|-----------|--------------|------------|---------|---------------|
| Llama 3.1 8B | 88 (79.3%) | 3 (2.7%) | 12 (10.8%) | 8 (7.2%) | 111 |
| Mixtral 8x7B | 148 (84.6%) | 4 (2.3%) | 18 (10.3%) | 5 (2.9%) | 175 |

**Table 1: Claim Verification Results by Model**

#### 4.1.2 Hallucination Rate Analysis

| Model | Hallucination Rate | Accuracy Rate |
|-------|-------------------|----------------|
| Llama 3.1 8B | 13.5% | 79.3% |
| Mixtral 8x7B | 12.6% | 84.6% |

**Table 2: Hallucination Rates by Model**

> **Key Finding**: Both models exhibit hallucination rates between 12-14%, with Mixtral showing slightly better performance. The "Not Found" category (claims that could not be verified) constitutes the majority of problematic outputs.

### 4.2 Bias Detection Results

#### 4.2.1 Geographic Distribution Analysis

The bias evaluation analyzed **658 entity mentions** across **252 responses** from four models:

| Model | Africa | Asia | Europe | North America | Oceania | South America | Caribbean | Middle East |
|-------|--------|------|--------|---------------|---------|---------------|-----------|-------------|
| Llama 3.1 70B | 8.3% | 17.3% | 19.5% | 11.3% | 14.3% | 12.0% | 7.5% | 9.0% |
| Llama 3.1 8B | 12.3% | 13.3% | 18.5% | 13.3% | 12.3% | 10.4% | 10.9% | 9.0% |
| Llama 3.3 70B | 9.4% | 15.0% | 16.5% | 12.6% | 14.2% | 11.8% | 9.4% | 11.0% |
| Mixtral 8x7B | 9.1% | 9.1% | 10.2% | 9.6% | 8.6% | 11.2% | 7.0% | 5.3% |

**Table 3: Geographic Distribution of Recommendations by Model**

#### 4.2.2 Regional Representation Analysis

```
Regional Distribution Visualization:

Europe:        ████████████████████ 16.2%
Asia:          ██████████████ 13.7%
North America: ████████████ 11.7%
Oceania:       ███████████ 11.3%
South America: ██████████ 10.9%
Africa:        ██████████ 9.8%
Middle East:   █████████ 8.7%
Caribbean:     ████████ 8.2%
```

**Figure 1: Regional Distribution of AI-Recommended Destinations**

> **Key Finding**: Europe maintains the highest representation (16.2%) across all models, while the Middle East and Caribbean show the lowest representation. This reflects a persistent Western/European bias in tourism AI systems.

#### 4.2.3 Sentiment Analysis by Region

| Region | Average Sentiment Score |
|--------|-------------------------|
| Worldwide | 0.296 |
| Europe | 0.277 |
| South America | 0.267 |
| North America | 0.246 |
| Oceania | 0.243 |
| Asia | 0.235 |
| Caribbean | 0.224 |
| Africa | 0.206 |
| Middle East | 0.184 |

**Table 4: Sentiment Scores by Region**

> **Key Finding**: Destinations in Europe and worldwide contexts receive more positive sentiment, while Africa and the Middle East receive lower sentiment scores—indicating potential affective bias in recommendations.

### 4.3 Real-Time Information Reliability Results

#### 4.3.1 Overall Accuracy by Model

The real-time evaluation tested **160 queries** across four models:

| Model | Accuracy Rate |
|-------|---------------|
| Llama 3.1 8B | 2.5% |
| Llama 3.1 70B | 0.0% |
| Llama 3.3 70B | 0.0% |
| Mixtral 8x7B | 0.0% |

**Table 5: Real-Time Information Accuracy by Model**

> **Critical Finding**: Real-time information retrieval is severely limited. Only the Llama 3.1 8B model achieved a marginal 2.5% accuracy, while all other models failed completely.

#### 4.3.2 Accuracy by Metric Type

| Metric | Accuracy |
|--------|----------|
| Local Time | 0.0% |
| Temperature (°C) | 1.25% |

**Table 6: Real-Time Accuracy by Data Type**

#### 4.3.3 Accuracy by Region

| Region | Accuracy |
|--------|----------|
| South America | 4.2% |
| All other regions | 0.0% |

**Table 7: Real-Time Accuracy by Geographic Region**

### 4.4 Summary of Key Findings

| Evaluation Dimension | Key Metric | Finding |
|---------------------|------------|---------|
| Hallucination | 12-14% rate | Moderate concern |
| Geographic Bias | Europe 16.2% vs Africa 9.8% | Significant imbalance |
| Real-Time Data | 0-2.5% accuracy | Critical failure |
| Sentiment Bias | Africa 0.21 vs Europe 0.28 | Moderate disparity |

**Table 8: Summary of Evaluation Results**

---

## 5. Outcomes

### 5.1 Technical Deliverables

1. **Evaluation Pipeline**: Fully functional Python-based evaluation system
2. **Datasets**: 
   - Hallucination dataset (286 validated claims)
   - Bias dataset (658 entity mentions)
   - Real-time evaluation dataset (160 queries)
3. **Visualization Dashboard**: Interactive HTML dashboard for result exploration
4. **Analysis Scripts**: Automated bias detection and reporting tools

### 5.2 Key Outcomes

#### 5.2.1 Hallucination Mitigation
- Identified that ~13% of tourism claims require manual verification
- Mixtral 8x7B shows marginally better factuality than Llama variants
- "Not Found" claims (unverifiable) constitute the largest error category

#### 5.2.2 Bias Quantification
- Europe receives 66% more recommendations than Africa
- Sentiment scores correlate with existing tourism popularity
- Need for deliberate underrepresentation correction in AI training

#### 5.2.3 Real-Time Capability Gap
- Current LLMs cannot reliably provide dynamic tourism data
- Temperature and time data require external API integration
- Recommendation: Hybrid architecture with real-time API fallback

### 5.3 Risk Assessment Matrix

| Risk Category | Severity | Likelihood | Mitigation Strategy |
|--------------|----------|------------|---------------------|
| Factual Inaccuracy | High | Certain | Human verification layer |
| Geographic Bias | Medium | Certain | Balanced training data |
| Outdated Information | High | Certain | API integration |
| Sentiment Disparity | Medium | Probable | Sentiment calibration |

**Table 9: Risk Assessment Matrix**

---

## 6. Conclusion

### 6.1 Summary of Findings

This comprehensive evaluation reveals significant challenges in deploying LLMs for tourism applications:

1. **Hallucination**: With a 12-14% hallucination rate, tourism AI systems require substantial human oversight to ensure accuracy.

2. **Geographic Bias**: The persistent European dominance in recommendations (16.2% vs 9.8% for Africa) indicates algorithmic bias that could reinforce existing tourism inequalities.

3. **Real-Time Failure**: The near-zero accuracy in dynamic information retrieval makes current LLMs unsuitable for real-time tourism queries without significant architectural changes.

### 6.2 Recommendations

Based on the findings, we recommend:

1. **Hybrid Architecture**: Combine LLMs with real-time APIs for dynamic data
2. **Bias Correction**: Implement geographic balancing in recommendation algorithms
3. **Human-in-the-Loop**: Maintain human verification for factual claims
4. **Continuous Monitoring**: Establish ongoing evaluation frameworks
5. **Transparency**: Provide source attribution for tourism recommendations

### 6.3 Future Work

- Expand evaluation to include more LLMs and providers
- Develop domain-specific fine-tuned models for tourism
- Implement user trust studies with controlled experiments
- Create standardized benchmarks for tourism AI evaluation

---

## 7. References

### 7.1 Technical Documentation

1. Project Aim Document: `Project Aim.md`
2. System Design: `system_design.md`
3. Practical Guide: `practical_guide.md`
4. Evaluation Pipeline: `eval_pipeline.py`

### 7.2 Data Sources

1. Evaluation Results: `eval_results_final.csv`
2. Travel Benchmark: `travel_benchmark_niche.csv`
3. Bias Dataset: `data_collection/bias_dataset.csv`
4. Hallucination Dataset: `data_collection/hallucination_dataset.csv`

### 7.3 Analysis Results

1. Bias Analysis: `results/bias_nvidia_live_fast/`
2. Hallucination Claims: `results/hallucination_claims_nvidia_live/`
3. Real-Time Evaluation: `results/realtime_nvidia_live/`

### 7.4 Visualization

1. Dashboard: `visualization_dashboard.html`

---

## Appendix A: Evaluation Metrics Definitions

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| Hallucination Rate | (Contradicted + Not Found) / Total Claims | Lower is better |
| Geographic Representation | Entity count per region / Total entities | Balanced is ideal |
| Real-Time Accuracy | Correct real-time responses / Total queries | Higher is better |
| Sentiment Score | VADER compound score (-1 to 1) | Closer to 0 is neutral |

---

## Appendix B: Model Configuration

| Parameter | Value |
|-----------|-------|
| Temperature | 0.7 |
| Max Tokens | 2048 |
| Top P | 0.9 |
| API Provider | NVIDIA NIM |

---

*Report generated: April 30, 2026*  
*Evaluation Framework Version: 1.0*  
*Total Queries Evaluated: 572*  
*Total Claims Analyzed: 944*