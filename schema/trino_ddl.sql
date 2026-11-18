-- Same schema as loaded into Trino (stand-in for Athena engine v3).
-- Type mapping: Oracle DATE -> TIMESTAMP, NUMBER(10) -> INTEGER,
-- NUMBER(10,2) -> DECIMAL(10,2), VARCHAR2 -> VARCHAR. Values are identical.
CREATE TABLE permits (
  permit_id     INTEGER,
  permit_type   VARCHAR,
  status        VARCHAR,
  neighborhood  VARCHAR,
  parcel_no     VARCHAR,
  legacy_ref    VARCHAR,
  applied_date  TIMESTAMP,
  issued_date   TIMESTAMP,
  fee_amount    DECIMAL(10,2),
  sqft          INTEGER
);

CREATE TABLE inspections (
  inspection_id   INTEGER,
  permit_id       INTEGER,
  inspection_date TIMESTAMP,
  result          VARCHAR,
  inspector_id    INTEGER
);

CREATE TABLE contacts (
  contact_id    INTEGER,
  permit_id     INTEGER,
  contact_type  VARCHAR,
  first_name    VARCHAR,
  middle_name   VARCHAR,
  last_name     VARCHAR,
  phone         VARCHAR,
  email         VARCHAR
);
