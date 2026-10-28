"""Vendor Inquiry Message Drafting Engine.

Generates structured, professional vendor inquiry messages validated by Pydantic.
Enforces strict grounding:
1. Never invents vendor names, fictional prices, or confirmed availability.
2. Formulates explicit quote requests and incorporates checklist questions.
3. Deterministic template fallback if LLM generation or validation fails.
"""

import logging

from pydantic import BaseModel, Field

from app.ai.llm_client import LLMClient, get_llm_client
from app.db.models import Event
from app.domain.schemas import PlanSchema

logger = logging.getLogger(__name__)


class DraftMessageRequest(BaseModel):
    vendor_category: str
    vendor_name: str | None = None
    custom_notes: str | None = None


class VendorInquiryDraft(BaseModel):
    vendor_category: str
    subject: str = Field(..., description="Subject line for email / inquiry")
    greeting: str = Field(..., description="Salutation")
    event_summary: str = Field(..., description="Event context (type, date, guests, city)")
    scope_of_work: str = Field(..., description="Requested deliverables / menu / services")
    specific_questions: list[str] = Field(
        default_factory=list,
        description="Key verification questions from checklist",
    )
    budget_guideline: str | None = Field(
        None, description="Host budget range or ceiling without fictitious quotes"
    )
    call_to_action: str = Field(
        ..., description="Direct request for itemized pricing and availability"
    )
    full_message: str = Field(..., description="Ready-to-send draft message body")
    is_template_fallback: bool = False


def _build_deterministic_fallback(
    event: Event,
    plan: PlanSchema,
    vendor_category: str,
    vendor_name: str | None,
    custom_notes: str | None,
    checklist_questions: list[str],
) -> VendorInquiryDraft:
    """Deterministic fallback inquiry template."""
    clean_category = vendor_category.strip().title()
    date_str = event.event_date.strftime("%d %b %Y") if event.event_date else "Date TBD"
    guest_count = event.guest_count or plan.guest_count or "our guests"

    # Find category budget allocation if available
    cat_alloc = None
    if plan.budget and plan.budget.categories:
        for c in plan.budget.categories:
            if clean_category.lower() in c.category.lower():
                cat_alloc = c.allocated_amount
                break

    budget_text = f"₹{float(cat_alloc):,.0f}" if cat_alloc else "standard market rates"

    # Default questions if none in plan checklist
    default_q = [
        f"Are you available for an event in {event.city or 'Mangaluru'} on {date_str}?",
        "Could you please share your itemized pricing packages and menu / equipment options?",
        "What are your advance deposit and cancellation / date-change terms?",
    ]
    questions_to_use = checklist_questions if checklist_questions else default_q

    salutation = f"Dear {vendor_name}," if vendor_name else f"Dear {clean_category} Team,"
    subject = (
        f"Inquiry: {clean_category} for {event.title} in {event.city or 'Mangaluru'} ({date_str})"
    )

    q_bullet_points = "\n".join(f"- {q}" for q in questions_to_use)
    notes_paragraph = f"\nSpecific requirements: {custom_notes}\n" if custom_notes else ""

    city_name = event.city or "Mangaluru"
    message_body = (
        f"{salutation}\n\n"
        f"We are organizing {event.title} ({event.event_type.capitalize()}) "
        f"scheduled for {date_str} in {city_name} with an expected attendance "
        f"of {guest_count} guests.\n\n"
        f"We are currently shortlisting trusted partners for {clean_category} services "
        f"with a planned budget allocation around {budget_text}.{notes_paragraph}\n\n"
        "Could you kindly confirm your availability and provide guidance on:\n"
        f"{q_bullet_points}\n\n"
        "Please share your standard brochure and itemized quotation.\n\n"
        "Warm regards,\n"
        "Festiva Event Host\n"
        "Contact via Festiva Platform"
    )

    summary_text = (
        f"{event.event_type.capitalize()} on {date_str} for {guest_count} guests in {city_name}"
    )

    return VendorInquiryDraft(
        vendor_category=clean_category,
        subject=subject,
        greeting=salutation,
        event_summary=summary_text,
        scope_of_work=f"{clean_category} package matching {guest_count} guests",
        specific_questions=questions_to_use,
        budget_guideline=f"Target budget ceiling: {budget_text}",
        call_to_action="Please share itemized package quotation and date availability.",
        full_message=message_body.strip(),
        is_template_fallback=True,
    )


def draft_vendor_inquiry(
    event: Event,
    plan: PlanSchema,
    vendor_category: str,
    vendor_name: str | None = None,
    custom_notes: str | None = None,
    client: LLMClient | None = None,
) -> VendorInquiryDraft:
    """Draft a validated vendor inquiry using LLM with deterministic template fallback."""
    llm = client or get_llm_client()
    clean_cat = vendor_category.strip()

    # Collect checklist questions for this category
    relevant_questions: list[str] = []
    if plan.checklist:
        for q in plan.checklist:
            if clean_cat.lower() in q.category.lower() or clean_cat.lower() in q.item.lower():
                relevant_questions.extend(q.questions_to_ask_vendor)

    # Also check vendor shortlist for questions
    if plan.vendor_shortlist:
        for v in plan.vendor_shortlist:
            if clean_cat.lower() in v.category.lower() and getattr(v, "questions_to_ask", None):
                relevant_questions.extend(v.questions_to_ask)

    # Deduplicate questions while preserving order
    deduped_questions = list(dict.fromkeys(relevant_questions))[:4]

    date_str = event.event_date.strftime("%d %b %Y") if event.event_date else "Date TBD"
    guest_count = event.guest_count or plan.guest_count or 80

    prompt = (
        f"Draft a vendor inquiry for the following celebration:\n"
        f"Event Title: {event.title}\n"
        f"Event Type: {event.event_type}\n"
        f"City: {event.city or 'Mangaluru'}\n"
        f"Event Date: {date_str}\n"
        f"Guest Count: {guest_count}\n"
        f"Vendor Category: {clean_cat}\n"
        f"Vendor Name: {vendor_name or 'Unspecified (use polite generic salutation)'}\n"
        f"Custom Notes: {custom_notes or 'None'}\n"
        f"Specific Questions to Include:\n"
        + "\n".join(f"- {q}" for q in deduped_questions)
        + "\n\n"
        "CRITICAL GROUNDING RULES:\n"
        "1. NEVER invent vendor names, mock prices, or confirmed availability.\n"
        "2. Ask directly for quotes, itemized packages, and date availability.\n"
        "3. Make full_message complete, respectful, and ready to send via email/WhatsApp.\n"
    )

    system_prompt = (
        "You are Festiva's Vendor Communication Specialist in Mangaluru.\n"
        "Generate a structured VendorInquiryDraft following the schema.\n"
        "Never hallucinate prices or fake vendor identities. Request itemized proposals honestly."
    )

    try:
        draft = llm.generate_structured(
            prompt=prompt,
            response_model=VendorInquiryDraft,
            system_prompt=system_prompt,
        )
        # Ensure fallback flag is false when LLM succeeded
        draft.is_template_fallback = False
        return draft
    except Exception as exc:
        logger.warning(
            "LLM vendor inquiry draft failed (%s); falling back to deterministic template.",
            exc,
        )
        return _build_deterministic_fallback(
            event=event,
            plan=plan,
            vendor_category=clean_cat,
            vendor_name=vendor_name,
            custom_notes=custom_notes,
            checklist_questions=deduped_questions,
        )
