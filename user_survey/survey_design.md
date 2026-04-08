# Module 4: User Trust Survey Design & UI Plan

## Objective
To conduct a controlled experiment with 80-150 travelers measuring trust, perceived transparency, recommendation reliability, decision confidence, and adoption intention when using AI-driven tourism systems.

## Experimental Setup
Participants will be split into two groups:
- **Group A (Control)**: Uses a standard LLM assistant (e.g., vanilla GPT-4 or Gemini interface) that provides direct answers without citations or explicit reasoning.
- **Group B (Test)**: Uses the proposed "Explainable AI (XAI) Tourism System", which provides citations, confidence scores, and reasons for its recommendations.

## Task for Participants
1. **Scenario**: "You are planning a 4-day trip to a destination you have never visited before. You have a moderate budget and are interested in a mix of cultural and modern attractions."
2. **Action**: Spend 15 minutes interacting with the assigned system to build an itinerary and answer travel logistics questions.
3. **Completion**: Finalize the itinerary and proceed to the post-task survey.

## Survey Instrument (Constructs & Questions)
*Responses recorded on a 5-point Likert scale (1 = Strongly Disagree to 5 = Strongly Agree)*

### 1. Trust
- I felt I could trust the information provided by the system.
- The system felt reliable during the planning process.

### 2. Perceived Transparency (Crucial for Group B vs A)
- I understood how the system arrived at its recommendations.
- The sources of the system's information were clear to me.

### 3. Recommendation Reliability
- The travel recommendations were highly relevant to my needs.
- I found the suggested itineraries to be factually accurate (to the best of my knowledge).

### 4. Decision Confidence
- I feel confident executing the trip based purely on the system's output.
- I do not feel the need to aggressively double-check the recommendations on external websites like TripAdvisor.

### 5. Adoption Intention
- I would use this system again for my next trip.
- I would recommend this tool to other travelers.

## UI Implementation Plan
We will build a Streamlit application to simulate both systems.
- **Frontend**: `streamlit run survey_app.py`
- **Group A UI**: A simple chat window.
- **Group B UI**: A chat window plus a sidebar showing:
  - Discovered Sources (Links to official tourism boards)
  - Fact-Check Status (Green checkmarks for verified claims)
  - Hallucination Risk Score
- **Data Collection**: The app will log all interactions (time spent, prompts entered) and finally embed a Qualtrics or Google Form iframe at the end containing the survey.
