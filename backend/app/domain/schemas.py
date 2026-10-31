"""Pydantic v2 schemas for Event Brief and Full Event Plan.

These models serve as the single source of truth for AI generation, validation,
and API representation.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Event Brief Schemas
# ---------------------------------------------------------------------------


class EventBrief(BaseModel):
    """Structured representation of a parsed event brief."""

    title: str = Field(..., max_length=100, description="Title or event headline")
    event_type: str = Field(..., pattern=r"^(wedding|birthday|community)$")
    event_date: date | None = Field(None, description="Event date (YYYY-MM-DD)")
    city: str = Field(
        "Mangaluru", max_length=100, description="Target city (defaults to Mangaluru)"
    )
    guest_count: int | None = Field(None, ge=1, le=10000, description="Estimated guest count")
    total_budget: Decimal | None = Field(
        None, ge=Decimal("1000"), le=Decimal("100000000"), description="Total budget amount in INR"
    )
    currency: str = Field("INR", max_length=3, description="Currency code")
    theme: str | None = Field(None, max_length=100, description="Event theme, styling, or vibe")
    dietary_preferences: list[str] = Field(default_factory=list, max_length=20)
    priorities: list[str] = Field(
        default_factory=list, max_length=20, description="Top spending/focus priorities"
    )
    constraints: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Constraints e.g. outdoor, rain contingency",
    )
    raw_brief: str | None = Field(
        None, max_length=5000, description="Original raw natural language text"
    )
    missing_fields: list[str] = Field(
        default_factory=list, max_length=20, description="Critical missing fields"
    )
    clarifying_questions: list[str] = Field(
        default_factory=list, max_length=10, description="Questions to ask user before generation"
    )

    @field_validator("event_type", mode="before")
    @classmethod
    def normalize_event_type(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.lower().strip()
        return v


# ---------------------------------------------------------------------------
# Full Event Plan Schemas (Source of Truth JSON in plan_versions)
# ---------------------------------------------------------------------------


class BudgetCategoryAllocation(BaseModel):
    category: str
    share_pct: Decimal = Field(..., ge=0, le=100)
    allocated_amount: Decimal = Field(..., ge=0)
    per_guest_cost: Decimal | None = None
    notes: str = ""


class BudgetBreakdown(BaseModel):
    total_budget: Decimal = Field(..., gt=0)
    currency: str = "INR"
    categories: list[BudgetCategoryAllocation]

    @property
    def allocated_sum(self) -> Decimal:
        return sum(c.allocated_amount for c in self.categories)


class TimelineItem(BaseModel):
    phase: str  # e.g. "3 months before", "1 week before", "Event Day"
    days_before_event: int = Field(..., ge=0)
    target_date: date | None = None
    task: str
    category: str
    owner: str = "Host"
    priority: str = "medium"  # high | medium | low


class ChecklistQuestion(BaseModel):
    category: str
    item: str
    questions_to_ask_vendor: list[str] = Field(default_factory=list)
    due_phase: str = "Planning"


class RunOfShowSlot(BaseModel):
    time_slot: str  # e.g. "17:00 - 18:00"
    activity: str
    location: str
    lead_person: str
    notes: str = ""


class VendorRecommendation(BaseModel):
    category: str
    vendor_id: str | None = None  # UUID string if grounded from directory
    vendor_name: str
    estimated_price_low: Decimal | None = None
    estimated_price_high: Decimal | None = None
    price_unit: str | None = None
    is_grounded: bool = False
    price_status: str = "confirmed"  # "confirmed" or "to confirm"
    questions_to_ask: list[str] = Field(default_factory=list)
    budget_impact: Decimal = Decimal("0")
    reason: str = Field(..., description="One-line explanation of fit")
    is_sample: bool = False


class PlanSchema(BaseModel):
    """The root plan model stored inside plan_versions.plan JSONB."""

    version: int = 1
    title: str
    event_type: str
    event_date: date | None = None
    guest_count: int | None = None
    total_budget: Decimal
    currency: str = "INR"
    summary: str
    budget: BudgetBreakdown
    timeline: list[TimelineItem] = Field(default_factory=list)
    checklist: list[ChecklistQuestion] = Field(default_factory=list)
    run_of_show: list[RunOfShowSlot] = Field(default_factory=list)
    vendor_shortlist: list[VendorRecommendation] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
