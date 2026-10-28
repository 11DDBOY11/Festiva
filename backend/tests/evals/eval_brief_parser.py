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
from app.ai.llm_client import GroqLLMClient, LLMClient  # noqa: E402
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

    def stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs: Any,
    ):
        yield self.generate(prompt, system_prompt, **kwargs)


def run_evals(mode: str = "replay") -> int:
    """Run evaluation benchmark across briefs with honest scoring and loud live failures."""
    if not DATASET_PATH.exists():
        print(f"Error: dataset not found at {DATASET_PATH}")
        return 1

    with open(DATASET_PATH, encoding="utf-8") as f:
        dataset = json.load(f)

    recordings = {}
    if RECORDINGS_PATH.exists():
        with open(RECORDINGS_PATH, encoding="utf-8") as f:
            recordings = json.load(f)

    # Configure client based on mode - NO silent fallback in live mode
    client: LLMClient
    if mode == "live":
        try:
            client = GroqLLMClient()
            print("[INFO] Running in LIVE mode with GroqLLMClient.")
        except Exception as exc:
            print(f"\n[FATAL] Live client initialization failed: {exc}")
            print(
                "Live mode requires a valid GROQ_API_KEY. "
                "Refusing silent fallback to FakeLLMClient."
            )
            return 1
    else:
        print("[INFO] Running in REPLAY mode with committed recordings.")
        client = ReplayLLMClient(recordings=recordings)

    # Metrics tracking (headline excludes synthetic fixtures)
    headline_valid_schema = 0
    headline_no_repair = 0
    headline_correct_clarifications = 0
    headline_passed = 0
    headline_count = 0

    synthetic_count = 0
    total_briefs = len(dataset)

    results_table = []

    for item in dataset:
        brief_id = item["id"]
        raw_text = item["raw_text"]
        expected = item["expected"]

        is_synthetic = False
        if mode == "replay":
            rec_entry = recordings.get(brief_id, {})
            is_synthetic = bool(rec_entry.get("synthetic", False))

        if isinstance(client, ReplayLLMClient):
            client.set_current_id(brief_id)

        schema_valid = False
        repaired = False
        clarification_correct = False
        notes = []

        try:
            res = parse_brief(raw_text=raw_text, client=client, allow_fallback=(mode != "live"))
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
                    if not missing_match:
                        notes.append(
                            f"missing mismatch: got {brief.missing_fields}, "
                            f"expected {expected['expected_missing']}"
                        )
                else:
                    clarification_correct = True
            else:
                clarification_correct = False
                notes.append(
                    f"needs_clarification got {res.needs_clarification}, "
                    f"expected {exp_needs_clarification}"
                )

            # Check expected event_type if specified
            if "event_type" in expected and brief.event_type != expected["event_type"]:
                notes.append(
                    f"event_type got {brief.event_type}, expected {expected['event_type']}"
                )

            # Save live response without synthetic flag
            if mode == "live" and schema_valid:
                dumped = json.loads(brief.model_dump_json())
                dumped["synthetic"] = False
                recordings[brief_id] = dumped

        except ValidationError as val_err:
            notes.append(f"Validation error: {val_err}")
            repaired = True
        except RuntimeError as rt_err:
            if mode == "live":
                print(f"\n[FATAL] Live LLM call failed loudly on {brief_id}: {rt_err}")
                print("No silent fallback permitted in live mode.")
                return 1
            notes.append(f"Runtime error: {rt_err}")
            repaired = True
        except Exception as err:
            if mode == "live":
                print(f"\n[FATAL] Unexpected live error on {brief_id}: {err}")
                return 1
            notes.append(f"Execution error: {err}")
            repaired = True

        passed = schema_valid and clarification_correct

        if is_synthetic:
            synthetic_count += 1
        else:
            headline_count += 1
            if schema_valid:
                headline_valid_schema += 1
            if schema_valid and not repaired:
                headline_no_repair += 1
            if clarification_correct:
                headline_correct_clarifications += 1
            if passed:
                headline_passed += 1

        status_str = "PASS" if passed else "FAIL"
        type_str = "[SYNTHETIC]" if is_synthetic else "[LIVE/REAL]"
        results_table.append(
            (
                brief_id,
                item["name"],
                schema_valid,
                not repaired,
                clarification_correct,
                status_str,
                type_str,
                notes,
            )
        )

    # Save live recordings if updated
    if mode == "live" and recordings:
        RECORDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(RECORDINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(recordings, f, indent=2)
        print(
            f"[INFO] Successfully captured {len(recordings)} live recordings to {RECORDINGS_PATH}\n"
        )

    # Output detailed report
    print("\n" + "=" * 94)
    print(
        f"{'ID':<10} {'Brief Name':<28} {'Type':<12} {'Schema':<8} "
        f"{'Repair-Free':<12} {'Clarification':<14} {'Result'}"
    )
    print("=" * 94)
    for b_id, name, s_valid, r_free, c_corr, res_str, t_str, notes in results_table:
        print(
            f"{b_id:<10} {name[:26]:<28} {t_str:<12} "
            f"{'YES' if s_valid else 'NO':<8} "
            f"{'YES' if r_free else 'NO':<12} "
            f"{'ACCURATE' if c_corr else 'INEXACT':<14} "
            f"{res_str}"
        )
        if notes:
            for note in notes:
                print(f"   |-> Note: {note}")

    print("=" * 94)
    print("EVALUATION METRICS REPORT:")
    print(f"  - Total Briefs Tested:         {total_briefs}")
    print(
        f"  - Headline Evaluated Briefs:   {headline_count} "
        f"(synthetic fixtures excluded: {synthetic_count})"
    )
    if headline_count > 0:
        schema_pct = (headline_valid_schema / headline_count) * 100
        repair_pct = (headline_no_repair / headline_count) * 100
        clarif_pct = (headline_correct_clarifications / headline_count) * 100
        pass_pct = (headline_passed / headline_count) * 100
        print(
            f"  - Headline Valid Schema Rate:  {schema_pct:.1f}% "
            f"({headline_valid_schema}/{headline_count})"
        )
        print(
            f"  - Headline Repair-Free Rate:   {repair_pct:.1f}% "
            f"({headline_no_repair}/{headline_count})"
        )
        print(
            f"  - Headline Clarification Acc:  {clarif_pct:.1f}% "
            f"({headline_correct_clarifications}/{headline_count})"
        )
        print(
            f"  - Headline Overall Pass Rate:  {pass_pct:.1f}% ({headline_passed}/{headline_count})"
        )
    print("=" * 94 + "\n")

    if headline_no_repair >= min(8, headline_count):
        print(
            f"[SUCCESS] Brief Parser criteria met "
            f"({headline_no_repair}/{headline_count} parsed without repair)!\n"
        )
        return 0
    else:
        print(f"[FAIL] Less than {min(8, headline_count)} briefs parsed without repair.\n")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Festiva AI Brief Parser Eval Harness")
    parser.add_argument("--live", action="store_true", help="Run against real live LLM provider")
    parser.add_argument("--replay", action="store_true", help="Run against recorded responses")
    args = parser.parse_args()

    mode = "live" if args.live else "replay"
    exit_code = run_evals(mode=mode)
    sys.exit(exit_code)
