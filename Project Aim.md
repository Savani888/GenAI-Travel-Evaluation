# Project Aim: Reliability, Bias, and Trust in AI-driven Tourism

## 1. Objective
The primary objective of this project is to conduct a quantitative audit of Large Language Model (LLM) performance in tourism information and recommendations. The study aims to produce empirical evidence of the risks inherent in tourism AI systems by focusing on four key areas:
1. **Hallucination Frequency**: Identifying inaccuracies, completely fabricated facts, and outdated information.
2. **Algorithmic Bias**: Evaluating geographic representation, diversity, and popularity bias in destination recommendations.
3. **Real-Time Information Reliability**: Testing the systems' ability to provide accurate dynamic data such as weather, events, and transport.
4. **User Trust Perception**: Understanding how users interact with and trust AI and Explainable AI (XAI) tourism systems.

## 2. Experimental Framework
The research consists of four technical evaluation modules:

### Module 1: Hallucination Detection
- **Task**: Generate 200–300 queries across categories including destination recommendations, attraction descriptions, travel logistics, cultural information, events, and historical facts.
- **Evaluation**: Responses from multiple LLMs are validated against authoritative sources (e.g., official tourism boards, UNESCO).
- **Metrics**: Hallucination Rate, Accuracy Rate, Outdated Info Rate.

### Module 2: Bias Detection
- **Task**: Use neutral prompts to request destinations (e.g., "hidden gems in Europe").
- **Evaluation**: Extract location entities to assess whether models disproportionately recommend popular/Western regions over underrepresented ones.
- **Metrics**: Geographic Representation Ratio, Diversity Score, Popularity Bias.

### Module 3: Real-Time Information Reliability
- **Task**: Query dynamic data like current weather, opening hours, event schedules, and transport delays.
- **Evaluation**: Compare AI responses against ground truth real-time sources (APIs).
- **Metrics**: Real-Time Accuracy.

### Module 4: User Trust Study
- **Task**: Conduct a controlled experiment with 80-150 travelers using either a standard LLM assistant or an explainable tourism system.
- **Metrics**: Trust, Perceived Transparency, Recommendation Reliability, Decision Confidence (analyzed via T-test, ANOVA, and Regression models).

## Expected Outcomes
The final deliverables for this research will include system architecture diagrams, experimental datasets, statistical evaluation results, and detailed visualizations (e.g., bias distribution maps, real-time accuracy charts) backed by a reproducible methodology.
