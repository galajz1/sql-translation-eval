-- Synthetic permits schema (Oracle). No real agency data or schemas.
CREATE TABLE permits (
  permit_id     NUMBER(10) PRIMARY KEY,
  permit_type   VARCHAR2(20) NOT NULL,   -- WAC, SIDE_SEWER, HYDRANT, STREET_USE
  status        VARCHAR2(20) NOT NULL,   -- APPLIED, IN_REVIEW, ISSUED, CLOSED, WITHDRAWN
  neighborhood  VARCHAR2(40),
  parcel_no     VARCHAR2(10),            -- 10-digit string
  legacy_ref    VARCHAR2(10),            -- numeric string, sometimes zero-padded
  applied_date  DATE NOT NULL,           -- Oracle DATE includes time of day
  issued_date   DATE,
  fee_amount    NUMBER(10,2),
  sqft          NUMBER(10)
);

CREATE TABLE inspections (
  inspection_id   NUMBER(10) PRIMARY KEY,
  permit_id       NUMBER(10) NOT NULL,
  inspection_date DATE NOT NULL,
  result          VARCHAR2(10) NOT NULL, -- PASS, FAIL, PARTIAL
  inspector_id    NUMBER(10)             -- NULL = unassigned
);

CREATE TABLE contacts (
  contact_id    NUMBER(10) PRIMARY KEY,
  permit_id     NUMBER(10) NOT NULL,
  contact_type  VARCHAR2(20) NOT NULL,   -- APPLICANT, OWNER, CONTRACTOR
  first_name    VARCHAR2(40) NOT NULL,
  middle_name   VARCHAR2(40),
  last_name     VARCHAR2(40) NOT NULL,
  phone         VARCHAR2(20),
  email         VARCHAR2(80)
);
