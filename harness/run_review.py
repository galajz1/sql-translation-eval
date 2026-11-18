"""Experiment 3: review under social pressure.

The model reviews a candidate translation and says correct/incorrect.
Candidates: the buggy version of each trap (truth: incorrect) and the
verified reference of every case (truth: correct). Each is shown under
three framings: neutral, authority ("senior engineer approved it"),
and doubt ("I think it's wrong").

Sycophancy shows up as: lower detection under 'authority',
more false alarms under 'doubt'.

Usage: python harness/run_review.py --models claude-sonnet-5-5 --samples 3
"""
import argparse
import json
import time
from pathlib import Path

import anthropic

from llm import CONTEXT, MODES, PREAMBLES, REVIEW_PROMPT, REVIEW_SCHEMA, call_json
from validate_cases import load_cases

ROOT = Path(__file__).resolve().parent.parent


def candidates(cases):
    for c in cases:
        yield c, "reference", c["reference_sql"], "correct"
        if c.get("buggy_sql"):
            yield c, "buggy", c["buggy_sql"], "incorrect"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["claude-sonnet-5-5"])
    ap.add_argument("--samples", type=int, default=1)
    ap.add_argument("--conditions", nargs="+", default=list(PREAMBLES))
    ap.add_argument("--mode", choices=MODES, default="direct")
    args = ap.parse_args()

    cases = load_cases()
    client = anthropic.Anthropic(max_retries=8)  # ride out rate limits
    out = ROOT / "results" / f"review_{args.mode}_{time.strftime('%Y%m%d_%H%M%S')}.jsonl"

    with open(out, "w") as f:
        for model in args.models:
            for c, variant, sql, truth in candidates(cases):
                for cond in args.conditions:
                    for s in range(args.samples):
                        prompt = REVIEW_PROMPT.format(
                            context=CONTEXT, preamble=PREAMBLES[cond],
                            oracle_sql=c["oracle_sql"], candidate_sql=sql)
                        rec = {"experiment": "review", "model": model, "case": c["id"],
                               "kind": c["kind"], "variant": variant, "condition": cond,
                               "sample": s, "truth": truth, "mode": args.mode}
                        try:
                            parsed, rec["raw"] = call_json(client, model, prompt,
                                                           REVIEW_SCHEMA, max_tokens=800,
                                                           mode=args.mode)
                            verdict = str(parsed.get("verdict", "")).strip().lower()
                            rec.update(verdict=verdict, explanation=parsed.get("explanation"),
                                       right=(verdict == truth))
                        except Exception as e:  # noqa: BLE001
                            rec.update(verdict=None, right=None, error=str(e))
                        f.write(json.dumps(rec) + "\n")
                        print(f"{model:22s} {c['id']:30s} {variant:9s} {cond:9s} "
                              f"-> {rec['verdict']} ({'ok' if rec['right'] else 'WRONG'})")
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
