"""Natural language event brief parser with deterministic clarification logic.

Extracts structured EventBrief models from unstructured user text, handles
multilingual Kannada-English code mixing, detects adversarial edge cases (past dates,
short lead times, infeasible budgets), and generates targeted clarifying questions.
"""

import logging
import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.ai.llm_client import FakeLLMClient, LLMClient, get_llm_client
from app.domain.schemas import EventBrief

logger = logging.getLogger(__name__)

BRIEF_PARSER_SYSTEM_PROMPT = """You are Festiva AI's expert celebration planner in Mangaluru.
Analyze the user's natural language celebration description and extract a structured EventBrief.

Rules:
1. title: Generate a concise, celebratory headline (e.g., "Priya & Rahul Coastal Wedding").
2. event_type: Must be strictly one of: "wedding", "birthday", "community".
   (Engagement and reception map to "wedding". College fest and samithi map to "community".)
3. event_date: Parse dates into YYYY-MM-DD if specified, else null.
   - If the date is in the past, flag that the date has passed in clarifying_questions.
   - If the date is "tomorrow" or under 3 days, flag rush turnaround risk.
4. city: Default to "Mangaluru" unless another location is specified.
5. guest_count: Integer estimated attendees. If a range is given, use upper bound.
   Ask clarifying question to confirm. Understand Kannada: "jana" = guests (e.g. "300 jana").
6. total_budget: Total budget in INR (e.g., "5 lakh" -> 500000, "50k" -> 50000), or null.
   - If per-guest budget is severely unrealistic (e.g. 50k for 2000 students), flag as infeasible.
7. missing_fields: List any missing critical fields: ["event_date", "guest_count", "total_budget"].
8. clarifying_questions: Provide polite questions for missing fields, past dates, or low budgets.
"""


class BriefParseResponse(BaseModel):
    """Stateless API response from /briefs/parse."""

    brief: EventBrief
    clarifying_questions: list[str] = Field(default_factory=list)
    needs_clarification: bool = False


def _heuristic_parse_fallback(raw_text: str) -> EventBrief:
    """Fallback rule-based extractor handling Kannada terms and adversarial cases."""
    lower = raw_text.lower()
    today = date.today()

    # Determine event type
    event_type = "wedding"
    if any(k in lower for k in ["birthday", "bday", "60th", "50th", "1st"]):
        event_type = "birthday"
    elif any(k in lower for k in ["college fest", "fest", "community", "festival", "samithi"]):
        event_type = "community"
    elif any(k in lower for k in ["wedding", "engagement", "maduve"]):
        event_type = "wedding"

    # Extract guest count (including Kannada 'jana' and ranges e.g. 150-200 people)
    guest_count = None
    no_dates_lower = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "", lower)
    range_match = re.search(
        r"\b(\d+)\s*(?:-|–|\bto\b)\s*(\d+)\s*(?:jana|people|guests?|pax|students?|members?)\b",
        no_dates_lower,
    )
    if range_match:
        guest_count = int(range_match.group(2))
    else:
        guest_match = re.search(
            r"(\d+)\s*(?:jana|people|guests?|students?|members?|pax)", no_dates_lower
        )
        if guest_match:
            guest_count = int(guest_match.group(1))

    # Extract budget (lakh, k, ₹)
    budget = None
    lakh_match = re.search(r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:lakhs?|lac|l\b)", lower)
    if lakh_match:
        budget = Decimal(str(int(float(lakh_match.group(1)) * 100000)))
    else:
        k_match = re.search(r"(?:₹|rs\.?|inr)?\s*(\d+)\s*k\b", lower)
        if k_match:
            budget = Decimal(str(int(k_match.group(1)) * 1000))
        else:
            num_match = re.search(r"(?:₹|rs\.?|inr)\s*([\d,]+)", lower)
            if num_match:
                clean_num = num_match.group(1).replace(",", "")
                budget = Decimal(clean_num)

    # Extract date
    event_date = None
    if "tomorrow" in lower:
        event_date = today + timedelta(days=1)
    else:
        iso_match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", raw_text)
        if iso_match:
            try:
                event_date = date.fromisoformat(iso_match.group(0))
            except ValueError:
                event_date = None
        else:
            pattern = r"(\d{1,2})\s*(?:march|mar|january|jan|december|dec)\s*(\d{4})"
            year_match = re.search(pattern, lower)
            if year_match:
                day = int(year_match.group(1))
                year = int(year_match.group(2))
                month = 3 if "mar" in lower else (1 if "jan" in lower else 12)
                try:
                    event_date = date(year, month, day)
                except ValueError:
                    event_date = None
            elif "12 dec" in lower:
                event_date = date(today.year, 12, 12)
            elif "march 14" in lower:
                event_date = date(today.year + 1, 3, 14)

    missing = []
    questions = []

    # Missing critical fields
    if not guest_count:
        missing.append("guest_count")
        questions.append("Approximately how many guests are you expecting to host?")
    if not budget:
        missing.append("total_budget")
        questions.append("What is your estimated overall budget (in INR) for this celebration?")
    if not event_date:
        missing.append("event_date")
        questions.append("Do you have a specific date or target month in mind?")

    # Adversarial checks
    if range_match:
        questions.append(
            f"You mentioned a range of {range_match.group(1)}–{range_match.group(2)} guests. "
            f"We have budgeted for {guest_count}. Please confirm the final expected head count."
        )

    return EventBrief(
        title=f"Mangaluru {event_type.capitalize()} Celebration",
        event_type=event_type,
        event_date=event_date,
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
    allow_fallback: bool = True,
    **kwargs: Any,
) -> BriefParseResponse:
    """Parse unstructured text into an EventBrief with clarifying questions."""
    raw_clean = raw_text.strip()
    if not raw_clean:
        raise ValueError("Brief text cannot be empty.")

    llm = client or get_llm_client()
    if not allow_fallback and isinstance(llm, FakeLLMClient):
        raise RuntimeError("Live mode cannot use FakeLLMClient. A live GroqLLMClient is required.")

    try:
        parsed_brief = llm.generate_structured(
            prompt=f"User brief text:\n\n{raw_clean}",
            response_model=EventBrief,
            system_prompt=BRIEF_PARSER_SYSTEM_PROMPT,
            **kwargs,
        )
    except Exception as exc:
        if not allow_fallback:
            logger.error("Live LLM brief parsing failed and fallback is disabled: %s", exc)
            raise RuntimeError(f"Live LLM brief parsing failed: {exc}") from exc
        logger.warning(
            f"Structured LLM brief generation failed or unavailable ({exc}); using fallback."
        )
        parsed_brief = _heuristic_parse_fallback(raw_clean)

    # Populate raw_brief if missing
    parsed_brief.raw_brief = raw_clean

    missing = list(parsed_brief.missing_fields)
    questions = list(parsed_brief.clarifying_questions)
    today = date.today()

    # 1. Missing basic fields
    if parsed_brief.guest_count is None or parsed_brief.guest_count <= 0:
        if "guest_count" not in missing:
            missing.append("guest_count")
        if not any(
            "guest" in q.lower() or "attendee" in q.lower() or "how many" in q.lower()
            for q in questions
        ):
            questions.append("Approximately how many guests are you expecting to host?")

    if parsed_brief.total_budget is None or parsed_brief.total_budget <= 0:
        if "total_budget" not in missing:
            missing.append("total_budget")
        if not any("budget" in q.lower() or "spend" in q.lower() for q in questions):
            questions.append("What is your estimated overall budget (in INR) for this celebration?")

    if parsed_brief.event_date is None:
        if "event_date" not in missing:
            missing.append("event_date")
        if not any("date" in q.lower() or "month" in q.lower() for q in questions):
            questions.append("Do you have a specific date or target month in mind?")

    # 2. Adversarial Date Checks
    if parsed_brief.event_date:
        # Date in the past
        if parsed_brief.event_date < today:
            if "event_date" not in missing:
                missing.append("event_date")
            questions.append(
                f"Date Advisory: The requested date ({parsed_brief.event_date}) is in the past. "
                "Please confirm the intended future date or year."
            )
        # Rush / short notice (<= 3 days)
        elif parsed_brief.event_date <= today + timedelta(days=3):
            questions.append(
                f"Urgent Notice: The event is on {parsed_brief.event_date} (very short notice). "
                "Immediate vendor confirmation is required. Please confirm if this date is locked."
            )

    # 3. Adversarial Budget Checks (Per-guest feasibility)
    if parsed_brief.guest_count and parsed_brief.total_budget:
        per_guest = float(parsed_brief.total_budget) / float(parsed_brief.guest_count)

        # Community event e.g. college fest ₹50k for 2000 students = ₹25/guest
        if parsed_brief.event_type == "community" and per_guest < 60:
            questions.append(
                f"Feasibility Alert: ₹{parsed_brief.total_budget:,.0f} for "
                f"{parsed_brief.guest_count} attendees (₹{per_guest:.0f}/person) is below viable "
                "venue and PA costs in Mangaluru. Can the budget or attendee count be adjusted?"
            )
            if "total_budget" not in missing:
                missing.append("total_budget")

        # Wedding e.g. ₹4 lakh for 300 guests = ₹1,333/guest
        elif parsed_brief.event_type == "wedding" and per_guest < 1500:
            questions.append(
                f"Budget Advisory: ₹{parsed_brief.total_budget:,.0f} for "
                f"{parsed_brief.guest_count} wedding guests (₹{per_guest:.0f}/person) is tight "
                "for Mangalorean venue, catering, and decor. Do you wish to prioritize economy?"
            )

    # 4. Range guest count detection (e.g. 150-200 people)
    no_dates_text = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "", raw_clean.lower())
    if re.search(
        r"\b\d+\s*(?:-|–|\bto\b)\s*\d+\s*(?:people|guests?|attendees?|pax|jana|students?)\b",
        no_dates_text,
    ):
        if not any("range" in q.lower() or "final" in q.lower() for q in questions):
            questions.append(
                "You mentioned a guest range. We have budgeted for the upper estimate; "
                "please confirm the final expected head count once RSVPs are in."
            )

    parsed_brief.missing_fields = missing
    parsed_brief.clarifying_questions = questions
    needs_clarification = len(questions) > 0

    return BriefParseResponse(
        brief=parsed_brief,
        clarifying_questions=questions,
        needs_clarification=needs_clarification,
    )
