"""Experiments 1 + 2: translate, execute, and check self-reported risk.

Outcome per case:
  correct        - runs on Trino and matches Oracle ground truth
  silent_wrong   - runs fine, returns different results   <- the dangerous one
  loud_fail      - errors (easy for a human to catch)
  no_output      - reply could not be parsed

Usage: python harness/run_translate.py --models claude-sonnet-5-5 claude-haiku-5-5 --samples 3
"""
import argparse
import json
import time
from pathlib import Path

import anthropic

from db import QueryError, normalize, run_trino
from llm import CONTEXT, MODES, TRANSLATE_PROMPT, TRANSLATE_SCHEMA, call_json
from validate_cases import load_cases

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["claude-sonnet-5-5"])
    ap.add_argument("--samples", type=int, default=1, help="repeats per case")
    ap.add_argument("--cases", nargs="*", help="limit to these case ids")
    ap.add_argument("--mode", choices=MODES, default="direct",
                    help="direct = answer immediately; reason = think first, then answer")
    args = ap.parse_args()

    truth = json.loads((ROOT / "results" / "ground_truth.json").read_text())
    cases = [c for c in load_cases() if not args.cases or c["id"] in args.cases]
    client = anthropic.Anthropic(max_retries=8)  # ride out rate limits
    out = ROOT / "results" / f"translate_{args.mode}_{time.strftime('%Y%m%d_%H%M%S')}.jsonl"

    with open(out, "w") as f:
        for model in args.models:
            for c in cases:
                for s in range(args.samples):
                    rec = {"experiment": "translate", "model": model, "case": c["id"],
                           "kind": c["kind"], "sample": s, "mode": args.mode}
                    prompt = TRANSLATE_PROMPT.format(context=CONTEXT, oracle_sql=c["oracle_sql"])
                    try:
                        parsed, rec["raw"] = call_json(client, model, prompt, TRANSLATE_SCHEMA,
                                                       mode=args.mode)
                        rec.update(trino_sql=parsed.get("trino_sql", ""),
                                   confidence=parsed.get("confidence"),
                                   risks=parsed.get("risks", []))
                    except Exception as e:  # noqa: BLE001
                        rec.update(outcome="no_output", error=str(e))
                        f.write(json.dumps(rec) + "\n")
                        continue

                    gt = truth[c["id"]]
                    try:
                        rows = run_trino(rec["trino_sql"])
                        same = normalize(rows, gt["ordered"]) == gt["rows"]
                        rec["outcome"] = "correct" if same else "silent_wrong"
                    except QueryError as e:
                        rec.update(outcome="loud_fail", error=str(e)[:500])

                    risk_text = " ".join(map(str, rec["risks"])).lower()
                    rec["flagged_trap"] = any(k.lower() in risk_text
                                              for k in c.get("trap_keywords", []))
                    f.write(json.dumps(rec) + "\n")
                    print(f"{model:22s} {args.mode:6s} {c['id']:30s} s{s} {rec['outcome']:12s} "
                          f"conf={rec['confidence']} flagged={rec['flagged_trap']}")
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
