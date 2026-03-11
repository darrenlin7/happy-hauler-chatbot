# Happy Hauler Chatbot

A Python-based recruiting chatbot for **Happy Hauler Trucking Co.** that screens truck driver applicants, answers common job questions, and stores past conversations with pass/fail summaries.

---

## Local Setup

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
├── app.py               # Streamlit entry point — navigation wrapper
├── chat_page.py         # Chat UI and screening logic
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

### Design and Architecture decisions

**Tech Stack**
First thing I had to decide was which tech stack to use. I've prototyped at home with Ollama and Gradio before, but after exploring different options I settled on a stack using Python and Claude Haiku as the LLM, a Streamlit UI, and SQLite for storing past sessions.

**State machine over pure LLM steering**
Since the chatbot is only meant to ask 3 questions and answer specific questions about the company and role, I opted to add a state machine to control the conversation flow and keep it discrete. The LLM classifies intent and returns structured JSON. This guarantees the bot never skips a required question and always enforces follow-up logic correctly.

**Static Data and System Prompt**
Screening question prompts are hardcoded so have no API cost, zero latency, and consistent phrasing. To answer some of the candidate's questions, I created a config file to store company and state enums that are injected into the LLM and the rest of the app. I assumed a few of the things (location, how many days they can take off, additional benefits)

**Two-call LLM pattern per turn**
Worked with LLM to come up with efficient way to make at most two API calls each answer: one to classify intent (`interpret_response`), one to generate a response when needed (FAQ answers, summary).

**UI**
I elected to keep the UI as simple as possible, with minimal styling and just using Streamlit's default components. Overall this is a blank slate that can be adapted to any brand's UI library.

---

## Environment Variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key (required) |
