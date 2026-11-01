"""Plan Diff & Refinement subpackage for Festiva AI.

Provides structured proposal generation, deterministic regex extraction,
optimistic diff calculation, and atomic version application with domain validation.
"""

from app.domain.diff.applier import apply_plan_diff
from app.domain.diff.extractor import _find_matching_category, _heuristic_extract_delta
from app.domain.diff.generator import generate_plan_diff
from app.domain.diff.schemas import (
    PROPOSAL_SYSTEM_PROMPT,
    AddTaskOp,
    AddVendorCategoryOp,
    AdjustCategoryOp,
    CategoryDelta,
    LLMPlanProposal,
    PlanDiff,
    PlanOp,
    RemoveTaskOp,
    SetSettingOp,
    SetTotalBudgetOp,
    TimelineDelta,
    UnsupportedOperationError,
)

__all__ = [
    "AddTaskOp",
    "AddVendorCategoryOp",
    "AdjustCategoryOp",
    "CategoryDelta",
    "LLMPlanProposal",
    "PlanDiff",
    "PlanOp",
    "PROPOSAL_SYSTEM_PROMPT",
    "RemoveTaskOp",
    "SetSettingOp",
    "SetTotalBudgetOp",
    "TimelineDelta",
    "UnsupportedOperationError",
    "_find_matching_category",
    "_heuristic_extract_delta",
    "apply_plan_diff",
    "generate_plan_diff",
]
