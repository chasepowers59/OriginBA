-- PL/SQL Throughput Harness: row-by-row vs BULK COLLECT + FORALL
-- Use this when replacing cursor loops in C2M extensions/packages.
-- Run in a non-production schema/session.

SET SERVEROUTPUT ON

--------------------------------------------------------------------------------
-- Test data setup
--------------------------------------------------------------------------------
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE T_BULK_SRC PURGE';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE T_BULK_TGT PURGE';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

CREATE TABLE T_BULK_SRC (
    ID NUMBER PRIMARY KEY,
    AMT NUMBER(12,2),
    STATUS_FLG VARCHAR2(1)
);

CREATE TABLE T_BULK_TGT (
    ID NUMBER PRIMARY KEY,
    AMT NUMBER(12,2),
    STATUS_FLG VARCHAR2(1)
);

INSERT /*+ APPEND */ INTO T_BULK_SRC
SELECT LEVEL, MOD(LEVEL, 1000) + 0.01, CASE WHEN MOD(LEVEL, 2) = 0 THEN 'A' ELSE 'B' END
FROM DUAL
CONNECT BY LEVEL <= 100000;
COMMIT;

--------------------------------------------------------------------------------
-- Baseline 1: Row-by-row
--------------------------------------------------------------------------------
DECLARE
    v_start_ts TIMESTAMP;
    v_end_ts   TIMESTAMP;
BEGIN
    DELETE FROM T_BULK_TGT;
    COMMIT;

    v_start_ts := SYSTIMESTAMP;
    FOR r IN (
        SELECT ID, AMT, STATUS_FLG
        FROM T_BULK_SRC
    ) LOOP
        INSERT INTO T_BULK_TGT (ID, AMT, STATUS_FLG)
        VALUES (r.ID, r.AMT, r.STATUS_FLG);
    END LOOP;
    COMMIT;
    v_end_ts := SYSTIMESTAMP;

    DBMS_OUTPUT.PUT_LINE('ROW_BY_ROW_SECONDS=' || TO_CHAR((v_end_ts - v_start_ts) * 86400));
END;
/

--------------------------------------------------------------------------------
-- Baseline 2: BULK COLLECT + FORALL (with LIMIT)
--------------------------------------------------------------------------------
DECLARE
    TYPE t_id_tab IS TABLE OF T_BULK_SRC.ID%TYPE INDEX BY PLS_INTEGER;
    TYPE t_amt_tab IS TABLE OF T_BULK_SRC.AMT%TYPE INDEX BY PLS_INTEGER;
    TYPE t_status_tab IS TABLE OF T_BULK_SRC.STATUS_FLG%TYPE INDEX BY PLS_INTEGER;

    v_id_tab     t_id_tab;
    v_amt_tab    t_amt_tab;
    v_status_tab t_status_tab;

    CURSOR c_src IS
        SELECT ID, AMT, STATUS_FLG
        FROM T_BULK_SRC;

    v_limit    PLS_INTEGER := 1000;
    v_start_ts TIMESTAMP;
    v_end_ts   TIMESTAMP;
BEGIN
    DELETE FROM T_BULK_TGT;
    COMMIT;

    v_start_ts := SYSTIMESTAMP;

    OPEN c_src;
    LOOP
        FETCH c_src BULK COLLECT INTO v_id_tab, v_amt_tab, v_status_tab LIMIT v_limit;
        EXIT WHEN v_id_tab.COUNT = 0;

        FORALL i IN 1 .. v_id_tab.COUNT SAVE EXCEPTIONS
            INSERT INTO T_BULK_TGT (ID, AMT, STATUS_FLG)
            VALUES (v_id_tab(i), v_amt_tab(i), v_status_tab(i));
    END LOOP;
    CLOSE c_src;

    COMMIT;
    v_end_ts := SYSTIMESTAMP;

    DBMS_OUTPUT.PUT_LINE('BULK_FORALL_SECONDS=' || TO_CHAR((v_end_ts - v_start_ts) * 86400));
END;
/

--------------------------------------------------------------------------------
-- Validation
--------------------------------------------------------------------------------
SELECT COUNT(*) AS SRC_ROWS FROM T_BULK_SRC;
SELECT COUNT(*) AS TGT_ROWS FROM T_BULK_TGT;

-- Notes:
-- 1) Memory tradeoff: larger LIMIT reduces context switches but increases PGA usage.
-- 2) Recommended LIMIT range: 500-5000; tune for your payload width and PGA budget.
-- 3) Use LIMIT for large datasets to avoid loading full result sets into memory at once.
