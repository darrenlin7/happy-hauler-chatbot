# Happy Hauler Chatbot

A Python-based recruiting chatbot for **Happy Hauler Trucking Co.** that screens truck driver applicants, answers common job questions, and stores past conversations with pass/fail summaries.

---

## Setup

### 1. Clone / unzip the repo

```bash
git clone <repo-url>
cd happy-hauler-chatbot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Python 3.9+ is supported (uses `from __future__ import annotations` for union type hints).

### 3. Add your Anthropic API key

```bash
cp .env.example .env
# then edit .env and paste your key
```

```
ANTHROPIC_API_KEY=sk-ant-...
```

### 4. Run

```bash
streamlit run app.py
```

Open the URL shown in the terminal (default: `http://localhost:8501`).
Use the **sidebar** to switch between the **Chat** page and **Past Chats**.

---

## Project Structure

```
happy-hauler-chatbot/
├── app.py               # Streamlit entry point — chat UI
├── pages/
│   └── Past_Chats.py    # Streamlit page — view past sessions
├── state_machine.py     # Conversation state & transition logic
├── llm.py               # Anthropic API wrapper
├── database.py          # SQLite read/write operations
├── config.py            # Company constants, FAQ data, State enum
├── requirements.txt
├── .env.example
└── README.md
```

A `chatbot.db` SQLite file is created automatically on first run.

---

## How It Works

### Conversation flow

```
GREETING → ASKING_CDL → ASKING_EXPERIENCE → ASKING_OVERNIGHT → QA_OPEN → ENDED
```

| State | Bot asks | Transition |
|---|---|---|
| `GREETING` | "Can I ask you a few questions?" | Any yes → `ASKING_CDL` |
| `ASKING_CDL` | "Do you have a valid Class A CDL?" | Yes → `ASKING_EXPERIENCE`; No → `ENDED` (fail) |
| `ASKING_EXPERIENCE` | "How many years of experience?" | Clear number → `ASKING_OVERNIGHT`; Vague → follow up (max 2×) |
| `ASKING_OVERNIGHT` | "OK with 2 nights/week on the road?" | Yes → `QA_OPEN`; No → `ENDED` (fail) |
| `QA_OPEN` | "Any questions about the role?" | Questions answered by LLM; "no more" → `ENDED` (pass) |
| `ENDED` | Pass/fail badge + summary shown | Terminal |

### Architecture decisions

**State machine over pure LLM steering**
Python handles all branching and transition logic. The LLM only classifies intent (returning structured JSON) and generates natural-language text. This guarantees the bot never skips a required question and always enforces follow-up logic correctly — even if the model returns unexpected output.

**Two-call LLM pattern per turn**
Each turn makes at most two API calls: one to classify intent (`interpret_response`), one to generate a response when needed (FAQ answers, summary). Screening question prompts are hardcoded strings — no API cost, zero latency, and perfectly consistent phrasing.

**SQLite over an external database**
Zero infrastructure to set up, works out of the box, easy to inspect with any SQLite viewer. More than adequate for this scale.

**Streamlit multipage via `pages/` directory**
Placing `Past_Chats.py` in the `pages/` folder gives automatic sidebar navigation with a single `streamlit run app.py` command — no routing code needed.

**Haiku model**
Fast, cheap, and capable enough for intent classification and short-form text generation in a screening context.

---

## Environment Variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key (required) |
