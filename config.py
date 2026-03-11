"""
config.py — Company constants, role info, and conversation state definitions.

All static data lives here so it can be updated without touching any logic.
"""

from enum import Enum


# ─── Company & Role Information ───────────────────────────────────────────────

COMPANY_NAME = "Happy Hauler Trucking Co."
ROLE_TITLE = "Truck Driver (Class A CDL required)"
PAY_RATE = "60–65 cents per mile, based on experience"
SCHEDULE = "On the road 2 nights per week"
LOCATION = "Midwest region (home base in Chicago, IL)"
BENEFITS = (
    "Health insurance, dental, vision, 401(k) with company match, "
    "14 days paid time off, and a per diem for overnight stays"
)

# Injected into the LLM system prompt during QA_OPEN state
COMPANY_FAQ = f"""
Company: {COMPANY_NAME}
Role: {ROLE_TITLE}
Pay: {PAY_RATE}
Schedule: {SCHEDULE}
Location: {LOCATION}
Benefits: {BENEFITS}
""".strip()


# ─── Conversation States ──────────────────────────────────────────────────────

class State(str, Enum):
    """Explicit states the chatbot moves through during a screening session."""

    GREETING = "GREETING"
    ASKING_CDL = "ASKING_CDL"
    ASKING_EXPERIENCE = "ASKING_EXPERIENCE"
    ASKING_OVERNIGHT = "ASKING_OVERNIGHT"
    QA_OPEN = "QA_OPEN"
    ENDED = "ENDED"


# ─── Tuning constants ─────────────────────────────────────────────────────────

# Maximum clarification attempts before skipping a question and moving on
MAX_FOLLOWUP_ATTEMPTS = 2
