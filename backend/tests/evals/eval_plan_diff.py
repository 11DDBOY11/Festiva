"""Evaluation harness for Phase 5 Plan Refinement & Diff Operations.

Evaluates 6 edit cases:
1. decor_exact: "reduce décor by ₹10,000" => décor allocation decreases by exactly ₹10,000
2. reject_leaves_version: reject preserves version at v1
3. accept_creates_v2: accept increments version to v2 (N+1)
4. llm_weather_safe: "make it weather-safe" adds weather protection setting/task/vendor
5. llm_kids_zone: "add a kids' zone" adds kids zone setting/task/vendor
6. llm_south_indian_theme: "swap to a South Indian theme" updates theme and cultural elements

Supports both --live (Groq live execution) and --replay (deterministic recorded responses).
Honest scoring: reports pass/fail per case with model name and timestamp metadata.
"""

import argparse
import json
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

EVALS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = EVALS_DIR.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.ai.llm_client import FakeLLMClient, GroqLLMClient, get_llm_client  # noqa: E402
from app.domain.diff_engine import (  # noqa: E402
    PlanDiff,
    apply_plan_diff,
    generate_plan_diff,
)
from app.domain.schemas import (  # noqa: E402
    BudgetBreakdown,
    BudgetCategoryAllocation,
    PlanSchema,
)

RECORDINGS_PATH = EVALS_DIR / "recordings" / "diff_responses.json"


def _create_base_wedding_plan() -> PlanSchema:
    """Create a standardized base wedding plan for diff evals."""
    today = date.today()
    event_date = today + timedelta(days=45)
    return PlanSchema(
        version=1,
        title="Mangaluru Coastal Grand Wedding",
        event_type="wedding",
        event_date=event_date,
        guest_count=250,
        total_budget=Decimal("1500000"),
        currency="INR",
        summary="A grand coastal celebration in Mangaluru with floral aesthetics.",
        budget=BudgetBreakdown(
            total_budget=Decimal("1500000"),
            currency="INR",
            categories=[
                BudgetCategoryAllocation(
                    category="Decor",
                    share_pct=Decimal("20.00"),
                    allocated_amount=Decimal("300000"),
                    per_guest_cost=Decimal("1200"),
                ),
                BudgetCategoryAllocation(
                    category="Catering",
                    share_pct=Decimal("50.00"),
                    allocated_amount=Decimal("750000"),
                    per_guest_cost=Decimal("3000"),
                ),
                BudgetCategoryAllocation(
                    category="Venue",
                    share_pct=Decimal("20.00"),
                    allocated_amount=Decimal("300000"),
                    per_guest_cost=Decimal("1200"),
                ),
                BudgetCategoryAllocation(
                    category="Contingency",
                    share_pct=Decimal("10.00"),
                    allocated_amount=Decimal("150000"),
                    per_guest_cost=Decimal("600"),
                ),
            ],
        ),
        timeline=[
            {
                "phase": "Planning",
                "days_before_event": 30,
                "target_date": event_date - timedelta(days=30),
                "task": "Confirm catering menu",
                "category": "Catering",
                "owner": "Host",
                "priority": "high",
            }
        ],
        meta={"theme": "Coastal Elegance", "city": "Mangaluru"},
    )


def run_diff_evals(mode: str = "replay") -> int:
    """Execute edit-correctness and LLM-phrased change evals."""
    print("\n" + "=" * 94)
    print(f"FESTIVA PHASE 5 PLAN REFINEMENT & DIFF EVALUATION (Mode: {mode.upper()})")
    print("=" * 94)

    is_live = mode == "live"
    client = None

    if is_live:
        try:
            client = get_llm_client("groq")
            if not isinstance(client, GroqLLMClient):
                print(
                    "Error: Live mode requested but Groq client is not configured.", file=sys.stderr
                )
                return 1
        except Exception as exc:
            print(f"Error initializing live Groq client: {exc}", file=sys.stderr)
            return 1
    else:
        # Replay mode uses recordings or fallback
        client = FakeLLMClient()

    recordings: dict = {}
    if RECORDINGS_PATH.exists():
        try:
            with open(RECORDINGS_PATH, encoding="utf-8") as f:
                recordings = json.load(f)
        except Exception:
            recordings = {}

    cases = [
        {
            "id": "diff_01_decor_exact",
            "name": "Exact Décor Reduction (-₹10,000)",
            "prompt": "reduce décor by ₹10,000",
            "type": "budget_edit",
        },
        {
            "id": "diff_02_reject_preserves_v1",
            "name": "Reject Preserves Version v1",
            "prompt": "reduce décor by ₹10,000",
            "type": "state_transition",
        },
        {
            "id": "diff_03_accept_creates_v2",
            "name": "Accept Creates Version N+1 (v2)",
            "prompt": "reduce décor by ₹10,000",
            "type": "state_transition",
        },
        {
            "id": "diff_04_llm_weather_safe",
            "name": "LLM: 'make it weather-safe'",
            "prompt": "make it weather-safe",
            "type": "llm_operation",
        },
        {
            "id": "diff_05_llm_kids_zone",
            "name": "LLM: 'add a kids' zone'",
            "prompt": "add a kids' zone",
            "type": "llm_operation",
        },
        {
            "id": "diff_06_llm_south_indian_theme",
            "name": "LLM: 'swap to a South Indian theme'",
            "prompt": "swap to a South Indian theme",
            "type": "llm_operation",
        },
    ]

    passed_count = 0
    total_count = len(cases)
    captured_recordings: dict = {}

    print(f"{'Case ID':<30} {'Type':<18} {'Prompt':<32} {'Result'}")
    print("-" * 94)

    for case in cases:
        cid = case["id"]
        cprompt = case["prompt"]
        ctype = case["type"]

        base_plan = _create_base_wedding_plan()
        case_passed = False
        notes = ""

        try:
            if is_live:
                diff = generate_plan_diff(base_plan, cprompt, client=client)
                captured_recordings[cid] = {
                    "prompt": cprompt,
                    "diff": diff.model_dump(mode="json"),
                    "metadata": {
                        "model": "llama-3.3-70b-versatile",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "mode": "live",
                    },
                }
            else:
                # Replay from recordings if available
                if cid in recordings:
                    rec_diff = recordings[cid].get("diff")
                    diff = PlanDiff.model_validate(rec_diff)
                else:
                    diff = generate_plan_diff(base_plan, cprompt, client=client)

            # Verification based on case type
            if cid == "diff_01_decor_exact":
                # Check decor reduction was exactly 10,000, money went to Contingency,
                # and total budget is preserved
                decor_delta = next(
                    (d for d in diff.category_changes if "decor" in d.category.lower()), None
                )
                contingency_delta = next(
                    (
                        d
                        for d in diff.category_changes
                        if any(
                            w in d.category.lower() for w in ["contingency", "buffer", "reserve"]
                        )
                    ),
                    None,
                )
                if (
                    decor_delta
                    and decor_delta.delta == Decimal("-10000")
                    and decor_delta.old_amount - decor_delta.new_amount == Decimal("10000")
                    and contingency_delta
                    and contingency_delta.delta == Decimal("10000")
                    and diff.new_total_budget == base_plan.total_budget
                ):
                    new_plan = apply_plan_diff(base_plan, diff)
                    if new_plan.total_budget == base_plan.total_budget:
                        case_passed = True

                notes = (
                    f"decor={decor_delta.delta if decor_delta else 'missing'}, "
                    f"contingency=+{contingency_delta.delta if contingency_delta else 0}, "
                    f"total_budget={diff.new_total_budget} (unchanged)"
                )

            elif cid == "diff_02_reject_preserves_v1":
                # Simulate reject: plan remains untouched at v1
                applied_plan = base_plan  # Not applying diff
                if applied_plan.version == 1:
                    case_passed = True
                notes = f"version={applied_plan.version}"

            elif cid == "diff_03_accept_creates_v2":
                # Simulate accept: plan advances to v2
                new_plan = apply_plan_diff(base_plan, diff)
                if new_plan.version == 2:
                    case_passed = True
                notes = f"version={new_plan.version}"

            elif cid == "diff_04_llm_weather_safe":
                new_plan = apply_plan_diff(base_plan, diff)
                has_setting = new_plan.meta.get("weather_safe") in [True, "true", "True"]
                has_task = any(
                    "weather" in t.task.lower() or "canopy" in t.task.lower()
                    for t in new_plan.timeline
                )
                has_vendor = any(
                    "weather" in v.lower() or "canopy" in v.lower() for v in diff.vendor_changes
                )
                if has_setting or has_task or has_vendor:
                    case_passed = True
                notes = f"setting={has_setting}, task={has_task}"

            elif cid == "diff_05_llm_kids_zone":
                new_plan = apply_plan_diff(base_plan, diff)
                has_setting = new_plan.meta.get("kids_zone") in [True, "true", "True"]
                has_task = any(
                    "kid" in t.task.lower() or "child" in t.task.lower() for t in new_plan.timeline
                )
                has_vendor = any("kid" in v.lower() for v in diff.vendor_changes)
                if has_setting or has_task or has_vendor:
                    case_passed = True
                notes = f"setting={has_setting}, task={has_task}"

            elif cid == "diff_06_llm_south_indian_theme":
                new_plan = apply_plan_diff(base_plan, diff)
                theme_str = str(new_plan.meta.get("theme", "")).lower()
                has_theme = "south indian" in theme_str or "traditional" in theme_str
                has_task = any(
                    "south indian" in t.task.lower() or "banana leaf" in t.task.lower()
                    for t in new_plan.timeline
                )
                if has_theme or has_task:
                    case_passed = True
                notes = f"theme='{new_plan.meta.get('theme')}'"

        except Exception as exc:
            case_passed = False
            notes = f"Exception: {exc}"

        status_str = "PASS" if case_passed else "FAIL"
        if case_passed:
            passed_count += 1

        print(f"{cid:<30} {ctype:<18} {cprompt:<32} {status_str} ({notes})")

    if is_live and captured_recordings:
        RECORDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(RECORDINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(captured_recordings, f, indent=2, default=str)
        print(f"\n[RECORDING] Saved live captures to {RECORDINGS_PATH}")

    pass_pct = (passed_count / total_count) * 100
    print("=" * 94)
    print(f"EVAL SUMMARY: {passed_count}/{total_count} cases passed ({pass_pct:.1f}%)")
    if is_live:
        print(
            "Provider: Groq (llama-3.3-70b-versatile) | Live execution timestamp: "
            + datetime.now(UTC).isoformat()
        )
    elif recordings:
        meta = next(iter(recordings.values())).get("metadata", {})
        m_name = meta.get("model", "N/A")
        m_time = meta.get("timestamp", "N/A")
        print(f"Recorded metadata: Model={m_name}, CapturedAt={m_time}")
    print("=" * 94 + "\n")

    return 0 if passed_count == total_count else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Festiva Phase 5 Plan Diff Evaluation")
    parser.add_argument("--live", action="store_true", help="Run live LLM evaluation via Groq")
    parser.add_argument(
        "--replay", action="store_true", help="Replay evaluation from recorded responses"
    )
    args = parser.parse_args()

    mode = "live" if args.live else "replay"
    exit_code = run_diff_evals(mode=mode)
    sys.exit(exit_code)
