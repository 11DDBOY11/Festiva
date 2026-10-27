"""Natural language event brief parser with deterministic clarification logic.

Extracts structured EventBrief models from unstructured user text and identifies
missing critical parameters to prompt the user with clarifying questions.
"""

import logging
import re
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.ai.llm_client import LLMClient, get_llm_client
from app.domain.schemas import EventBrief

logger = logging.getLogger(__name__)

BRIEF_PARSER_SYSTEM_PROMPT = """You are Festiva AI's expert celebration planner.
Analyze the user's natural language celebration description and extract a structured EventBrief.

Rules:
1. title: Generate a concise, celebratory headline (e.g., "Priya & Rahul Coastal Wedding").
2. event_type: Must be strictly one of: "wedding", "birthday", "community".
3. event_date: Parse dates into YYYY-MM-DD if specified, else null.
4. city: Default to "Mangaluru" unless another location is specified.
5. guest_count: Integer estimated attendees, or null if unknown.
6. total_budget: Total budget in INR (e.g., "5 lakhs" -> 500000), or null if unknown.
7. missing_fields: List any missing critical fields: ["event_date", "guest_count", "total_budget"].
8. clarifying_questions: Provide polite, targeted questions for missing critical fields.
"""


class BriefParseResponse(BaseModel):
    """Stateless API response from /briefs/parse."""

    brief: EventBrief
    clarifying_questions: list[str] = Field(default_factory=list)
    needs_clarification: bool = False


def _heuristic_parse_fallback(raw_text: str) -> EventBrief:
    """Fallback rule-based extractor when LLM is in fake/offline mode."""
    lower = raw_text.lower()

    # Determine event type
    event_type = "wedding"
    if "birthday" in lower or "bday" in lower:
        event_type = "birthday"
    elif any(k in lower for k in ["community", "festival", "pooja", "reunion", "samithi"]):
        event_type = "community"

    # Extract guest count
    guest_match = re.search(r"(\d+)\s*(?:guests?|people|pax|members?)", lower)
    guest_count = int(guest_match.group(1)) if guest_match else None

    # Extract budget
    budget = None
    lakh_match = re.search(r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:lakhs?|lac|l)", lower)
    if lakh_match:
        budget = Decimal(str(float(lakh_match.group(1)) * 100000))
    else:
        num_match = re.search(r"(?:₹|rs\.?|inr)\s*([\d,]+)", lower)
        if num_match:
            clean_num = num_match.group(1).replace(",", "")
            budget = Decimal(clean_num)

    # Missing fields check
    missing = []
    questions = []
    if not guest_count:
        missing.append("guest_count")
        questions.append("Approximately how many guests are you expecting to host?")
    if not budget:
        missing.append("total_budget")
        questions.append("What is your estimated overall budget (in INR) for this celebration?")
    missing.append("event_date")
    questions.append("Do you have a specific date or target month in mind?")

    return EventBrief(
        title=f"Mangaluru {event_type.capitalize()} Celebration",
        event_type=event_type,
        event_date=None,
        city="Mangaluru",
        guest_count=guest_count,
        total_budget=budget,
        raw_brief=raw_text,
        missing_fields=missing,
        clarifying_questions=questions,
    )


def parse_brief(
    raw_text: str,
    client: LLMClient | None = None,
    **kwargs: Any,
) -> BriefParseResponse:
    """Parse unstructured text into an EventBrief with clarifying questions."""
    raw_clean = raw_text.strip()
    if not raw_clean:
        raise ValueError("Brief text cannot be empty.")

    llm = client or get_llm_client()

    try:
        parsed_brief = llm.generate_structured(
            prompt=f"User brief text:\n\n{raw_clean}",
            response_model=EventBrief,
            system_prompt=BRIEF_PARSER_SYSTEM_PROMPT,
            **kwargs,
        )
    except Exception as exc:
        logger.warning(
            f"Structured LLM brief generation failed or unavailable ({exc}); using fallback."
        )
        parsed_brief = _heuristic_parse_fallback(raw_clean)

    # Populate raw_brief if missing
    parsed_brief.raw_brief = raw_clean

    # Enforce deterministic post-checks on critical fields
    missing = list(parsed_brief.missing_fields)
    questions = list(parsed_brief.clarifying_questions)

    if parsed_brief.guest_count is None or parsed_brief.guest_count <= 0:
        if "guest_count" not in missing:
            missing.append("guest_count")
        if not any("guest" in q.lower() or "attendee" in q.lower() for q in questions):
            questions.append("Approximately how many guests are you expecting to host?")

    if parsed_brief.total_budget is None or parsed_brief.total_budget <= 0:
        if "total_budget" not in missing:
            missing.append("total_budget")
        if not any("budget" in q.lower() or "spend" in q.lower() for q in questions):
            questions.append(
                "What is your estimated overall budget (in INR) for this celebration?"
            )

    if parsed_brief.event_date is None:
        if "event_date" not in missing:
            missing.append("event_date")
        if not any("date" in q.lower() or "month" in q.lower() for q in questions):
            questions.append("Do you have a specific date or target month in mind?")

    parsed_brief.missing_fields = missing
    parsed_brief.clarifying_questions = questions
    needs_clarification = len(missing) > 0

    return BriefParseResponse(
        brief=parsed_brief,
        clarifying_questions=questions,
        needs_clarification=needs_clarification,
    )
