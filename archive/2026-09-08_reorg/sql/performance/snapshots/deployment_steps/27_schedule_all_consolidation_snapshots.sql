PROMPT ============================================================
PROMPT Create consolidation snapshot scheduler jobs
PROMPT ============================================================
PROMPT Creates recurring jobs, then applies 6-hour stagger (04:00 GMT base).

DECLARE
    PROCEDURE drop_job_if_exists(p_job_name IN VARCHAR2) IS
    BEGIN
        DBMS_SCHEDULER.DROP_JOB(job_name => p_job_name, force => TRUE);
    EXCEPTION
        WHEN OTHERS THEN
            IF SQLCODE != -27475 THEN RAISE; END IF;
    END;

    PROCEDURE create_refresh_job(p_job_name IN VARCHAR2, p_procedure IN VARCHAR2, p_comments IN VARCHAR2) IS
    BEGIN
        drop_job_if_exists(p_job_name);
        DBMS_SCHEDULER.CREATE_JOB(
            job_name        => p_job_name,
            job_type        => 'STORED_PROCEDURE',
            job_action      => p_procedure,
            start_date      => SYSTIMESTAMP,
            repeat_interval => 'FREQ=DAILY;BYHOUR=4,10,16,22;BYMINUTE=0;BYSECOND=0',
            enabled         => TRUE,
            comments        => p_comments
        );
    END;
BEGIN
    create_refresh_job('CISADM.JOB_REFRESH_ACCT_CUSTOMER_RPT_CURR',
        'CISADM.REFRESH_ACCT_CUSTOMER_RPT_CURR',
        'Refresh account-customer consolidation snapshot (6-month rolling)');
    create_refresh_job('CISADM.JOB_REFRESH_CASE_PREM_CONTACT_RPT_CURR',
        'CISADM.REFRESH_CASE_PREM_CONTACT_RPT_CURR',
        'Refresh case-premise-contact consolidation snapshot (6-month rolling)');
    create_refresh_job('CISADM.JOB_REFRESH_NEW_SERVICE_PIPELINE_RPT_CURR',
        'CISADM.REFRESH_NEW_SERVICE_PIPELINE_RPT_CURR',
        'Refresh new-service pipeline consolidation snapshot (6-month rolling)');
    create_refresh_job('CISADM.JOB_REFRESH_FIELD_ACTIVITY_RPT_CURR',
        'CISADM.REFRESH_FIELD_ACTIVITY_RPT_CURR',
        'Refresh field activity consolidation snapshot (6-month rolling)');
    create_refresh_job('CISADM.JOB_REFRESH_CREW_OPS_RPT_CURR',
        'CISADM.REFRESH_CREW_OPS_RPT_CURR',
        'Refresh crew ops consolidation snapshot (6-month rolling)');
    create_refresh_job('CISADM.JOB_REFRESH_DEVICE_SP_RPT_CURR',
        'CISADM.REFRESH_DEVICE_SP_RPT_CURR',
        'Refresh device service-point consolidation snapshot (6-month rolling)');
    create_refresh_job('CISADM.JOB_REFRESH_PAY_EVENT_RPT_CURR',
        'CISADM.REFRESH_PAY_EVENT_RPT_CURR',
        'Refresh pay event consolidation snapshot (6-month rolling)');
    create_refresh_job('CISADM.JOB_REFRESH_BILLABLE_CHARGE_RPT_CURR',
        'CISADM.REFRESH_BILLABLE_CHARGE_RPT_CURR',
        'Refresh billable charge consolidation snapshot (6-month rolling)');
    create_refresh_job('CISADM.JOB_REFRESH_SA_AGED_BAL_RPT_CURR',
        'CISADM.REFRESH_SA_AGED_BAL_RPT_CURR',
        'Refresh SA aged balance consolidation snapshot (6-month rolling)');
    create_refresh_job('CISADM.JOB_REFRESH_WO_PROC_RPT_CURR',
        'CISADM.REFRESH_WO_PROC_RPT_CURR',
        'Refresh write-off process consolidation snapshot (6-month rolling)');
    create_refresh_job('CISADM.JOB_REFRESH_OPS_EXCEPTION_RPT_CURR',
        'CISADM.REFRESH_OPS_EXCEPTION_RPT_CURR',
        'Refresh ops exception consolidation snapshot (6-month rolling)');
    create_refresh_job('CISADM.JOB_REFRESH_WORKFLOW_QUEUE_RPT_CURR',
        'CISADM.REFRESH_WORKFLOW_QUEUE_RPT_CURR',
        'Refresh workflow queue consolidation snapshot (6-month rolling)');
END;
/

PROMPT Apply approved 6-hour staggered cadence (consolidation jobs, 04:00 GMT base)
@@..\apply_6hour_staggered_schedule_consolidation_4am_base.sql
