"""Check every case before running any model.

For each case:
  1. Oracle query runs           -> saved as ground truth
  2. Trino reference matches it  -> the "right answer" really is right
  3. Trino buggy version RUNS but does NOT match -> the trap really fires
Writes results/ground_truth.json. Any failure means fix the case or the data.
"""
import json
import sys
from pathlib import Path

import yaml

from db import QueryError, normalize, results_match, run_oracle, run_trino

ROOT = Path(__file__).resolve().parent.parent


def load_cases():
    return yaml.safe_load((ROOT / "cases" / "cases.yaml").read_text())


def main() -> int:
    truth, problems = {}, []
    for c in load_cases():
        ordered = c.get("ordered", False)
        try:
            ora = run_oracle(c["oracle_sql"])
        except QueryError as e:
            problems.append(f"{c['id']}: Oracle query failed: {e}")
            continue
        truth[c["id"]] = {"ordered": ordered, "rows": normalize(ora, ordered)}

        try:
            ref = run_trino(c["reference_sql"])
            ok = results_match(ora, ref, ordered)
        except QueryError as e:
            ok, ref = False, f"ERROR {e}"
        status = "ref OK " if ok else "ref MISMATCH"
        if not ok:
            problems.append(f"{c['id']}: reference does not match Oracle")

        if c.get("buggy_sql"):
            try:
                bug = run_trino(c["buggy_sql"])
                fires = not results_match(ora, bug, ordered)
                status += " | trap fires" if fires else " | TRAP DOES NOT FIRE"
                if not fires:
                    problems.append(f"{c['id']}: buggy SQL matches Oracle (trap is inert on this data)")
            except QueryError as e:
                status += " | buggy SQL ERRORS (should run silently)"
                problems.append(f"{c['id']}: buggy SQL errors: {e}")
        print(f"{c['id']:32s} rows={len(ora):4d}  {status}")

    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    (out / "ground_truth.json").write_text(json.dumps(truth, indent=1))
    print(f"\nGround truth for {len(truth)} cases -> results/ground_truth.json")
    if problems:
        print("\nPROBLEMS:\n  " + "\n  ".join(problems))
        return 1
    print("All cases valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
