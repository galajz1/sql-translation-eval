"""Deterministic synthetic data for the permits schema.

Random rows plus a few *planted* rows that guarantee each trap actually
changes results (e.g. permits applied late on Jan 31, issued on a month-end,
zero-padded legacy refs). Run directly to write CSVs to data/.
"""
from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 42
N_PERMITS = 400

PERMIT_TYPES = ["WAC", "SIDE_SEWER", "HYDRANT", "STREET_USE"]
STATUSES = ["APPLIED", "IN_REVIEW", "ISSUED", "CLOSED", "WITHDRAWN"]
NEIGHBORHOODS = ["Ballard", "Beacon Hill", "Capitol Hill", "Fremont",
                 "Georgetown", "Rainier Valley", "University District", "West Seattle"]
PARCEL_PREFIXES = ["0420", "1937", "2588", "3301", "5466", "7720"]
FIRST = ["Ana", "Ben", "Chen", "Dana", "Eli", "Fatima", "Gus", "Hana", "Ivan", "Jo",
         "Kofi", "Lena", "Mateo", "Nia", "Omar", "Priya", "Quinn", "Rosa", "Sam", "Tomas"]
MIDDLE = ["Lee", "Marie", "James", "Ann", "Ray", "Kai"]
LAST = ["Alvarez", "Brooks", "Cho", "Diaz", "Evans", "Fujita", "Garcia", "Huang",
        "Ibrahim", "Jensen", "Kim", "Lopez", "Mendez", "Nguyen", "Okafor", "Patel"]

START = datetime(2025, 7, 1)
END = datetime(2026, 6, 30)

# Month-end issue dates where Oracle ADD_MONTHS differs from naive date_add.
MONTH_END_ISSUES = [datetime(2025, 9, 30, 10, 15), datetime(2025, 11, 30, 14, 0),
                    datetime(2026, 2, 28, 9, 30), datetime(2026, 4, 30, 16, 45),
                    datetime(2026, 6, 30, 11, 5)]


def _rand_ts(rng: random.Random, start: datetime, end: datetime) -> datetime:
    span = int((end - start).total_seconds())
    return start + timedelta(seconds=rng.randint(0, span))


def generate(seed: int = SEED) -> dict[str, list[dict]]:
    rng = random.Random(seed)
    permits, inspections, contacts = [], [], []

    for pid in range(1, N_PERMITS + 1):
        applied = _rand_ts(rng, START, END)
        status = rng.choices(STATUSES, weights=[15, 20, 35, 20, 10])[0]
        issued = None
        if status in ("ISSUED", "CLOSED"):
            issued = applied + timedelta(days=rng.randint(2, 120),
                                         seconds=rng.randint(0, 86399))
        ref = str(rng.randint(1000, 9999))
        if rng.random() < 0.1:
            ref = ref.zfill(6)
        permits.append(dict(
            permit_id=pid,
            permit_type=rng.choice(PERMIT_TYPES),
            status=status,
            neighborhood=rng.choice(NEIGHBORHOODS),
            parcel_no=rng.choice(PARCEL_PREFIXES) + f"{rng.randint(0, 999999):06d}",
            legacy_ref=ref,
            applied_date=applied,
            issued_date=issued,
            fee_amount=round(rng.uniform(100, 5000), 2),
            sqft=rng.randint(400, 12000),
        ))

    # --- planted rows -----------------------------------------------------
    # Late-day Jan 31 applications (TRUNC date-range trap).
    for i, hour in enumerate([9, 13, 17, 21]):
        permits[i]["applied_date"] = datetime(2026, 1, 31, hour, 20)
    # Month-end issue dates (ADD_MONTHS trap).
    for i, issued in enumerate(MONTH_END_ISSUES, start=10):
        permits[i].update(status="ISSUED", issued_date=issued,
                          applied_date=issued - timedelta(days=20, hours=3))
    # Legacy refs that only match via Oracle implicit TO_NUMBER.
    for i, ref in zip(range(20, 26), ["1001", "001001", "1002", "001002", "001003", "1003"]):
        permits[i]["legacy_ref"] = ref

    iid = cid = 1
    for p in permits:
        for _ in range(rng.choice([0, 0, 1, 2, 3, 4, 5])):
            inspections.append(dict(
                inspection_id=iid,
                permit_id=p["permit_id"],
                inspection_date=p["applied_date"] + timedelta(days=rng.randint(1, 90),
                                                              seconds=rng.randint(0, 86399)),
                result=rng.choices(["PASS", "FAIL", "PARTIAL"], weights=[55, 30, 15])[0],
                inspector_id=None if rng.random() < 0.1 else rng.randint(1, 8),
            ))
            iid += 1
        for ctype in ["APPLICANT"] + (["OWNER"] if rng.random() < 0.5 else []):
            first, last = rng.choice(FIRST), rng.choice(LAST)
            contacts.append(dict(
                contact_id=cid,
                permit_id=p["permit_id"],
                contact_type=ctype,
                first_name=first,
                middle_name=rng.choice(MIDDLE) if rng.random() < 0.5 else None,
                last_name=last,
                phone=None if rng.random() < 0.2 else f"206-555-{rng.randint(0, 9999):04d}",
                email=None if rng.random() < 0.25 else f"{first}.{last}{cid}@example.com".lower(),
            ))
            cid += 1

    return {"permits": permits, "inspections": inspections, "contacts": contacts}


def write_csvs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for table, rows in generate().items():
        with open(out_dir / f"{table}.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"{table}: {len(rows)} rows")


if __name__ == "__main__":
    write_csvs(Path(__file__).resolve().parent.parent / "data")
