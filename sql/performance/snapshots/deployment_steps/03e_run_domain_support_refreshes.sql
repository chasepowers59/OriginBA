PROMPT ============================================================
PROMPT Run domain support refreshes
PROMPT ============================================================
PROMPT CMS views are live; only CMS_SA_SNAPSHOT requires refresh.

PROMPT [1/1] CMS_SA_SNAPSHOT
BEGIN
    cisadm.refresh_cms_sa_snapshot;
END;
/
