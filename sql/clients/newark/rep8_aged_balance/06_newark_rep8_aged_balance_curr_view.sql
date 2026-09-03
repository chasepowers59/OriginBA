-- JRS2C2M reporting views over CISADM.NEWARK_REP8_AGED_BALANCE.
-- Uses REP8_AGED_BALANCE name (not NEWARK_REP8_AGED_BALANCE) to avoid conflict
-- with the legacy empty JRS2C2M table from the first deploy attempt.

PROMPT Creating JRS2C2M.REP8_AGED_BALANCE view...

CREATE OR REPLACE VIEW jrs2c2m.rep8_aged_balance AS
SELECT
    r.*
FROM cisadm.newark_rep8_aged_balance r;

PROMPT Creating JRS2C2M.NEWARK_REP8_AGED_BALANCE_CURR view...

CREATE OR REPLACE VIEW jrs2c2m.newark_rep8_aged_balance_curr AS
SELECT
    r.*
FROM cisadm.newark_rep8_aged_balance r
WHERE r.rpt_dt = (
    SELECT MAX(x.rpt_dt)
    FROM cisadm.newark_rep8_aged_balance x
);

PROMPT REP8 reporting views created.
