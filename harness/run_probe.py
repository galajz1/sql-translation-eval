"""Knowledge probe: does the model know the fact each trap depends on?

Asks each yes/no question from cases/probes.yaml in isolation. score.py then
joins these with translate results to find "knows but doesn't apply":
the model answers the fact correctly here, yet its translation is silently wrong.

Usage: python harness/run_probe.py --models claude-haiku-5-5 --samples 3
"""
import argparse
import json
import time
from pathlib import Path

import anthropic
import yaml

from llm import MODES, PROBE_PROMPT, PROBE_SCHEMA, call_json
from validate_cases import load_cases

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["claude-sonnet-5-5"])
    ap.add_argument("--samples", type=int, default=1)
    ap.add_argument("--cases", nargs="*", help="limit to these case ids")
    ap.add_argument("--mode", choices=MODES, default="direct")
    args = ap.parse_args()

    probes = yaml.safe_load((ROOT / "cases" / "probes.yaml").read_text())
    kinds = {c["id"]: c["kind"] for c in load_cases()}
    ids = [i for i in probes if not args.cases or i in args.cases]
    client = anthropic.Anthropic(max_retries=8)  # ride out rate limits
    (ROOT / "results").mkdir(exist_ok=True)
    out = ROOT / "results" / f"probe_{args.mode}_{time.strftime('%Y%m%d_%H%M%S')}.jsonl"

    with open(out, "w") as f:
        for model in args.models:
            for cid in ids:
                p = probes[cid]
                for s in range(args.samples):
                    rec = {"experiment": "probe", "model": model, "case": cid,
                           "kind": kinds.get(cid), "sample": s, "truth": p["answer"],
                           "mode": args.mode}
                    try:
                        parsed, rec["raw"] = call_json(
                            client, model, PROBE_PROMPT.format(question=p["question"]),
                            PROBE_SCHEMA, max_tokens=400, mode=args.mode)
                        ans = str(parsed.get("answer", "")).strip().lower()
                        rec.update(answer=ans, explanation=parsed.get("explanation"),
                                   right=(ans == p["answer"]))
                    except Exception as e:  # noqa: BLE001
                        rec.update(answer=None, right=None, error=str(e))
                    f.write(json.dumps(rec) + "\n")
                    print(f"{model:22s} {cid:30s} s{s} answer={rec['answer']} "
                          f"({'ok' if rec['right'] else 'WRONG'})")
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
