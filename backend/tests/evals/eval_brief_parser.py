"""Evaluation harness for Phase 3 brief parsing and clarification accuracy.

Supports two modes:
  --replay (default, CI-friendly): Evaluates against recorded LLM responses.
  --live (manual): Calls real configured LLMClient (Groq) and updates recordings.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError

EVALS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = EVALS_DIR.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.ai.brief_parser import parse_brief  # noqa: E402
from app.ai.llm_client import FakeLLMClient, GroqLLMClient, LLMClient  # noqa: E402
from app.domain.schemas import EventBrief  # noqa: E402

DATASET_PATH = EVALS_DIR / "dataset.json"
RECORDINGS_PATH = EVALS_DIR / "recordings" / "brief_responses.json"


class ReplayLLMClient(LLMClient):
    """Replay client reading committed responses for CI determinism."""

    def __init__(self, recordings: dict[str, dict[str, Any]]) -> None:
        self.recordings = recordings
        self.current_id: str | None = None

    def set_current_id(self, brief_id: str) -> None:
        self.current_id = brief_id

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        if self.current_id and self.current_id in self.recordings:
            return json.dumps(self.recordings[self.current_id])
        return "{}"

    def generate_structured(
        self,
        prompt: str,
        response_model: type,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> Any:
        if not self.current_id or self.current_id not in self.recordings:
            raise ValueError(f"No recording found for {self.current_id}")
        data = self.recordings[self.current_id]
        return response_model.model_validate(data)


def run_evals(mode: str = "replay") -> int:
    """Run evaluation benchmark across 10 sample briefs."""
    if not DATASET_PATH.exists():
        print(f"Error: dataset not found at {DATASET_PATH}")
        return 1

    with open(DATASET_PATH, encoding="utf-8") as f:
        dataset = json.load(f)

    recordings = {}
    if RECORDINGS_PATH.exists():
        with open(RECORDINGS_PATH, encoding="utf-8") as f:
            recordings = json.load(f)

    # Configure client based on mode
    client: LLMClient
    if mode == "live":
        try:
            client = GroqLLMClient()
            print("[INFO] Running in LIVE mode with GroqLLMClient.")
        except Exception as exc:
            print(f"[WARN] Live client initialization failed: {exc}. Using Fake.")
            client = FakeLLMClient()
    else:
        print("[INFO] Running in REPLAY mode with committed recordings.")
        client = ReplayLLMClient(recordings=recordings)

    total_valid_schema = 0
    total_no_repair = 0
    total_correct_clarifications = 0
    total_briefs = len(dataset)

    print("\n" + "=" * 88)
    print(
        f"{'ID':<10} {'Brief Name':<26} {'Schema':<8} {'Repair':<8} "
        f"{'Clarification':<14} {'Result'}"
    )
    print("=" * 88)

    for item in dataset:
        brief_id = item["id"]
        raw_text = item["raw_text"]
        expected = item["expected"]

        if isinstance(client, ReplayLLMClient):
            client.set_current_id(brief_id)

        schema_valid = False
        repaired = False
        clarification_correct = False

        try:
            res = parse_brief(raw_text=raw_text, client=client)
            brief = res.brief
            schema_valid = isinstance(brief, EventBrief)

            # Check clarification accuracy
            exp_needs_clarification = expected.get("needs_clarification", False)
            if res.needs_clarification == exp_needs_clarification:
                if "expected_missing" in expected:
                    missing_match = all(
                        m in brief.missing_fields for m in expected["expected_missing"]
                    )
                    clarification_correct = missing_match
                else:
                    clarification_correct = True

            # If running live with real client and recording, save output
            if mode == "live" and schema_valid and not isinstance(client, FakeLLMClient):
                recordings[brief_id] = json.loads(brief.model_dump_json())

        except ValidationError as val_err:
            print(f"Validation error on {brief_id}: {val_err}")
            repaired = True
        except Exception as err:
            print(f"Execution error on {brief_id}: {err}")
            repaired = True

        if schema_valid:
            total_valid_schema += 1
        if schema_valid and not repaired:
            total_no_repair += 1
        if clarification_correct:
            total_correct_clarifications += 1

        status_str = "PASS" if (schema_valid and clarification_correct) else "FAIL"
        print(
            f"{brief_id:<10} {item['name'][:26]:<28} "
            f"{'YES' if schema_valid else 'NO':<8} "
            f"{'NO' if not repaired else 'YES':<8} "
            f"{'ACCURATE' if clarification_correct else 'INEXACT':<14} "
            f"{status_str}"
        )

    # Save live recordings if updated
    if mode == "live" and recordings:
        RECORDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(RECORDINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(recordings, f, indent=2)
        print(f"[INFO] Updated live recordings at {RECORDINGS_PATH}")

    # Summary metrics
    schema_pct = (total_valid_schema / total_briefs) * 100
    repair_free_pct = (total_no_repair / total_briefs) * 100
    clarification_pct = (total_correct_clarifications / total_briefs) * 100

    print("=" * 90)
    print("PHASE 3 EVALUATION SUMMARY METRICS:")
    print(f"  • Total Briefs Tested:         {total_briefs}")
    print(
        f"  • Valid Schema Rate:           {schema_pct:.1f}% "
        f"({total_valid_schema}/{total_briefs})"
    )
    print(
        f"  • Repair-Free Parsing Rate:    {repair_free_pct:.1f}% "
        f"({total_no_repair}/{total_briefs}) [Target: >= 80%]"
    )
    print(
        f"  • Clarification Accuracy Rate: {clarification_pct:.1f}% "
        f"({total_correct_clarifications}/{total_briefs})"
    )
    print("=" * 90)

    if total_no_repair >= 8:
        print("[SUCCESS] Phase 3 Brief Parser exit criteria met (>= 8/10 parsed without repair)!\n")
        return 0
    else:
        print("[FAIL] Less than 8 briefs parsed without repair.\n")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Festiva AI Brief Parser Eval Harness")
    parser.add_argument("--live", action="store_true", help="Run against real live LLM provider")
    parser.add_argument("--replay", action="store_true", help="Run against recorded responses")
    args = parser.parse_args()

    mode = "live" if args.live else "replay"
    exit_code = run_evals(mode=mode)
    sys.exit(exit_code)
