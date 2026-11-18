"""Checks that run without Oracle/Trino: code compiles, cases are well-formed,
and the synthetic data contains the rows each trap needs in order to fire."""
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import yaml
from generate_data import generate
from db import results_match

cases = yaml.safe_load((ROOT / "cases" / "cases.yaml").read_text())
ids = [c["id"] for c in cases]
assert len(ids) == len(set(ids)), "duplicate case ids"
for c in cases:
    assert {"oracle_sql", "reference_sql", "kind"} <= c.keys(), c["id"]
    if c["kind"] == "trap":
        assert c.get("buggy_sql") and c.get("trap_keywords"), c["id"]
print(f"cases: {sum(c['kind']=='control' for c in cases)} controls, "
      f"{sum(c['kind']=='trap' for c in cases)} traps")

d = generate()
P, I, C = d["permits"], d["inspections"], d["contacts"]
assert generate() == d, "generator not deterministic"

def month_end(ts):
    return (ts.replace(day=28) + __import__("datetime").timedelta(days=4)).replace(day=1).day == 1 and \
           (ts + __import__("datetime").timedelta(days=1)).day == 1

checks = {
  "concat_null: applicants with NULL middle name":
      sum(c["contact_type"] == "APPLICANT" and c["middle_name"] is None for c in C),
  "integer_division: inspectors with mixed results":
      len({i["inspector_id"] for i in I if i["inspector_id"] and i["result"] == "PASS"}),
  "decode_null: unassigned inspections":
      sum(i["inspector_id"] is None for i in I),
  "outer_join_filter: SIDE_SEWER permits with no FAIL":
      sum(p["permit_type"] == "SIDE_SEWER" and not any(i["permit_id"] == p["permit_id"]
          and i["result"] == "FAIL" for i in I) for p in P),
  "trunc_date_range: Jan 31 applications after midnight":
      sum(p["applied_date"].date() == datetime(2026, 1, 31).date()
          and p["applied_date"].time() != datetime.min.time() for p in P),
  "date_subtraction: issued permits (fractional days)":
      sum(p["issued_date"] is not None for p in P),
  "implicit_numeric: zero-padded refs 1001-1003":
      sum(p["legacy_ref"] in ("001001", "001002", "001003") for p in P),
  "add_months_eom: issued on a 28/30-day month end":
      sum(p["issued_date"] is not None and month_end(p["issued_date"])
          and p["issued_date"].day < 31 for p in P),
  "to_char_mon: any rows (case always differs)": len(P),
  "null_ordering: permits with NULL issued_date":
      sum(p["issued_date"] is None for p in P),
  "substr_zero: parcels (prefix always lost)": len(P),
}
bad = 0
for k, v in checks.items():
    print(f"  {'OK ' if v else 'FAIL'} {v:4d}  {k}")
    bad += not v

# comparator sanity
from decimal import Decimal
assert results_match([(1, Decimal("0.50"))], [(1, 0.5)], ordered=False)
assert results_match([(datetime(2026, 3, 31),)], [(__import__("datetime").date(2026, 3, 31),)], False)
assert not results_match([("JAN-2026", 3)], [("Jan-2026", 3)], False)
assert not results_match([(1,), (2,)], [(2,), (1,)], ordered=True)
assert results_match([(1,), (2,)], [(2,), (1,)], ordered=False)
print("comparator: OK")
sys.exit(1 if bad else 0)
