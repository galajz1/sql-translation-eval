"""Connections, data loading, query execution and result comparison."""
from __future__ import annotations

import os
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ORACLE_DSN = os.getenv("ORACLE_DSN", "localhost:1521/FREEPDB1")
ORACLE_USER = os.getenv("ORACLE_USER", "permits")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD", "permits")
TRINO_HOST = os.getenv("TRINO_HOST", "localhost")
TRINO_PORT = int(os.getenv("TRINO_PORT", "8080"))

TABLES = ["permits", "inspections", "contacts"]


# ---------------------------------------------------------------- connections
def oracle_conn():
    import oracledb  # thin mode, no Oracle client install needed
    return oracledb.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN)


def trino_conn():
    import trino
    return trino.dbapi.connect(
        host=TRINO_HOST, port=TRINO_PORT, user="eval",
        catalog="memory", schema="default",
        session_properties={"query_max_execution_time": "60s"},
    )


def _ddl_statements(path: Path) -> list[str]:
    text = re.sub(r"--[^\n]*", "", path.read_text())
    return [s.strip() for s in text.split(";") if s.strip()]


# ---------------------------------------------------------------- loading
def _trino_literal(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, datetime):
        return f"TIMESTAMP '{v:%Y-%m-%d %H:%M:%S}'"
    if isinstance(v, float):
        return f"DECIMAL '{v:.2f}'"
    if isinstance(v, int):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def load_oracle(data: dict[str, list[dict]]) -> None:
    with oracle_conn() as conn:
        cur = conn.cursor()
        for t in reversed(TABLES):
            cur.execute(f"DROP TABLE IF EXISTS {t} PURGE")
        for stmt in _ddl_statements(ROOT / "schema" / "oracle_ddl.sql"):
            cur.execute(stmt)
        for t in TABLES:
            rows = data[t]
            cols = list(rows[0].keys())
            sql = f"INSERT INTO {t} ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)})"
            cur.executemany(sql, rows)
        conn.commit()


def load_trino(data: dict[str, list[dict]], batch: int = 200) -> None:
    conn = trino_conn()
    cur = conn.cursor()
    for t in TABLES:
        cur.execute(f"DROP TABLE IF EXISTS {t}")
        cur.fetchall()
    for stmt in _ddl_statements(ROOT / "schema" / "trino_ddl.sql"):
        cur.execute(stmt)
        cur.fetchall()
    for t in TABLES:
        rows = data[t]
        cols = list(rows[0].keys())
        for i in range(0, len(rows), batch):
            values = ",\n".join(
                "(" + ", ".join(_trino_literal(r[c]) for c in cols) + ")"
                for r in rows[i:i + batch])
            cur.execute(f"INSERT INTO {t} ({', '.join(cols)}) VALUES {values}")
            cur.fetchall()


# ---------------------------------------------------------------- execution
class QueryError(Exception):
    pass


def _single_select(sql: str) -> str:
    """Only allow one read-only statement (model output is untrusted)."""
    sql = sql.strip().rstrip(";").strip()
    if ";" in sql or not re.match(r"(?is)^\s*(select|with)\b", sql):
        raise QueryError("Only a single SELECT/WITH statement is allowed")
    return sql


def run_oracle(sql: str) -> list[tuple]:
    sql = _single_select(sql)
    try:
        with oracle_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            return [tuple(r) for r in cur.fetchall()]
    except Exception as e:  # noqa: BLE001
        raise QueryError(str(e)) from e


def run_trino(sql: str) -> list[tuple]:
    sql = _single_select(sql)
    try:
        cur = trino_conn().cursor()
        cur.execute(sql)
        return [tuple(r) for r in cur.fetchall()]
    except Exception as e:  # noqa: BLE001
        raise QueryError(str(e)) from e


# ---------------------------------------------------------------- comparison
def _norm_value(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float, Decimal)):
        return round(float(v), 6)
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.strftime("%Y-%m-%d") + " 00:00:00"
    return str(v)


def normalize(rows: list[tuple], ordered: bool) -> list[list]:
    out = [[_norm_value(v) for v in r] for r in rows]
    if not ordered:
        out.sort(key=lambda r: [("" if v is None else str(v)) for v in r])
    return out


def results_match(a: list[tuple], b: list[tuple], ordered: bool) -> bool:
    """Values compared positionally; column names are ignored."""
    return normalize(a, ordered) == normalize(b, ordered)
