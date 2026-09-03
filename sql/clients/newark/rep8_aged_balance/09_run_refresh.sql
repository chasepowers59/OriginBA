-- Run Newark REP8 staging refresh (as-of today).
-- CMS_SA_SNAPSHOT must be current for the same date (governed FIFO aging source).

PROMPT Running CISADM.REFRESH_CMS_SA_SNAPSHOT...

BEGIN
    cisadm.refresh_cms_sa_snapshot;
END;
/

PROMPT Running CISADM.REFRESH_NEWARK_REP8_AGED_BALANCE for TRUNC(SYSDATE)...

BEGIN
    cisadm.refresh_newark_rep8_aged_balance(TRUNC(SYSDATE));
END;
/

PROMPT Refresh complete.
