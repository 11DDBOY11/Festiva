"""Domain models and schemas for plan diffing and refinement operations."""

from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class UnsupportedOperationError(ValueError):
    """Raised when a user requests an operation Festiva cannot perform."""

    pass


# ---------------------------------------------------------------------------
# Allowed Operation Schemas (Pydantic)
# ---------------------------------------------------------------------------


class AdjustCategoryOp(BaseModel):
    op: Literal["adjust_category"] = "adjust_category"
    category: str = Field(
        ...,
        description="Target budget category name, e.g. 'Decor', 'Catering', 'Photography', 'Venue'",
    )
    amount_delta: Decimal | None = Field(
        None,
        description="Change in INR (negative for reductions, positive for increases)",
    )
    new_amount: Decimal | None = Field(
        None,
        ge=Decimal("0"),
        le=Decimal("100000000"),
        description="Target absolute allocation amount in INR",
    )


class SetTotalBudgetOp(BaseModel):
    op: Literal["set_total_budget"] = "set_total_budget"
    new_total: Decimal = Field(
        ...,
        ge=Decimal("1000"),
        le=Decimal("100000000"),
        description="New total event budget in INR (min 1,000, max 100,000,000)",
    )


class AddTaskOp(BaseModel):
    op: Literal["add_task"] = "add_task"
    task: str = Field(..., description="Clear title/description of the milestone task to add")
    category: str = Field(
        default="Planning", description="Task category, e.g. 'Venue', 'Decor', 'Entertainment'"
    )
    days_before_event: int = Field(
        default=7, ge=0, description="Days before event date to complete"
    )
    priority: str = Field(default="medium", description="Priority level: high, medium, low")


class RemoveTaskOp(BaseModel):
    op: Literal["remove_task"] = "remove_task"
    task_query: str = Field(
        ..., description="Search phrase or title of the timeline task to remove"
    )


class AddVendorCategoryOp(BaseModel):
    op: Literal["add_vendor_category"] = "add_vendor_category"
    category: str = Field(
        ..., description="Vendor category to add, e.g. 'Weather Protection', 'Kids Entertainment'"
    )
    suggested_vendor: str | None = Field(None, description="Optional vendor name if suggested")


class SetSettingOp(BaseModel):
    op: Literal["set_setting"] = "set_setting"
    key: Literal["weather_safe", "kids_zone", "theme", "dietary_preferences"] = Field(
        ...,
        description="Setting key: weather_safe, kids_zone, theme, or dietary_preferences",
    )
    value: str = Field(
        ..., description="Setting value (e.g. 'true', 'Traditional South Indian & Coastal')"
    )


PlanOp = Annotated[
    AdjustCategoryOp
    | SetTotalBudgetOp
    | AddTaskOp
    | RemoveTaskOp
    | AddVendorCategoryOp
    | SetSettingOp,
    Field(discriminator="op"),
]


class LLMPlanProposal(BaseModel):
    """Structured extraction of modification intent from user prompt."""

    explanation: str = Field(..., description="Brief 1-sentence summary of what is changing")
    operations: list[PlanOp] = Field(
        default_factory=list, description="Validated list of allowed operations to apply"
    )
    unsupported_request: str | None = Field(
        None,
        description="If request is unsupported (e.g. flights/crypto), state reason why",
    )


# ---------------------------------------------------------------------------
# Plan Diff Models
# ---------------------------------------------------------------------------


class CategoryDelta(BaseModel):
    category: str
    old_amount: Decimal
    new_amount: Decimal
    delta: Decimal
    old_share_pct: Decimal | None = None
    new_share_pct: Decimal | None = None


class TimelineDelta(BaseModel):
    task: str
    action: str  # added | modified | removed
    old_date: str | None = None
    new_date: str | None = None
    reason: str | None = None


class PlanDiff(BaseModel):
    prompt: str
    summary: str
    category_changes: list[CategoryDelta] = Field(default_factory=list)
    timeline_changes: list[TimelineDelta] = Field(default_factory=list)
    setting_changes: dict[str, Any] = Field(default_factory=dict)
    vendor_changes: list[str] = Field(default_factory=list)
    old_total_budget: Decimal
    new_total_budget: Decimal
    budget_impact: Decimal  # net change in total budget (e.g. -10000.00)


PROPOSAL_SYSTEM_PROMPT = """You are Festiva AI's plan modification specialist in Mangaluru.
Translate the user's free text modification request into a validated list of allowed operations.

Allowed operations:
1. "adjust_category": modify budget for an existing category (category, amount_delta, new_amount)
2. "set_total_budget": set overall event budget (new_total)
3. "add_task": add a milestone task (task, category, days_before_event, priority)
4. "remove_task": remove a timeline task matching task_query
5. "add_vendor_category": add a vendor requirement (category, suggested_vendor)
6. "set_setting": update plan settings (key: weather_safe/kids_zone/theme, value: string)

Special request mappings:
- "make it weather-safe":
  * set_setting(key="weather_safe", value="true")
  * add_task(task="Arrange water-proof monsoon canopy and backup area", category="Venue")
  * add_vendor_category(category="Weather Protection / Canopy Rentals")
- "add a kids' zone":
  * set_setting(key="kids_zone", value="true")
  * add_task(task="Set up dedicated kids activity and craft play area", category="Entertainment")
  * add_vendor_category(category="Kids Entertainment & Magic Shows")
- "swap to a South Indian theme":
  * set_setting(key="theme", value="Traditional South Indian & Coastal Heritage")
  * add_task(task="Coordinate traditional South Indian floral decor", category="Decor")

Rules:
- For unsupported requests (e.g. flights, crypto, gambling, live animals):
  set unsupported_request to "Can't do that yet: Festiva does not support <reason>".
- Never invent unauthorized categories or arbitrary operations outside the allowed list.
"""
