PROMPT ============================================================
PROMPT Seed CM_SNAPSHOT_TYPE_FLG lookups for CMS SA Snapshot Domains
PROMPT ============================================================
PROMPT Required by Standard Offering Ad Hocs that inner-join
PROMPT CI_LOOKUP_VAL_L on CM_SNAPSHOT_TYPE_FLG (e.g. LDAY = Latest).
PROMPT CI_LOOKUP is a view over CI_LOOKUP_VAL + CI_LOOKUP_VAL_L.
PROMPT Idempotent: skips values that already exist.

MERGE INTO cisadm.ci_lookup_val tgt
USING (
    SELECT 'CM_SNAPSHOT_TYPE_FLG' AS field_name, 'ARCH' AS field_value, 'A' AS eff_status,
           1 AS version, 'CM' AS owner_flg, 'archived' AS value_name FROM dual
    UNION ALL
    SELECT 'CM_SNAPSHOT_TYPE_FLG', 'EMON', 'A', 1, 'CM', 'monthsEnds' FROM dual
    UNION ALL
    SELECT 'CM_SNAPSHOT_TYPE_FLG', 'LDAY', 'A', 1, 'CM', 'latestDayExtracted' FROM dual
    UNION ALL
    SELECT 'CM_SNAPSHOT_TYPE_FLG', 'LEMN', 'A', 1, 'CM', 'latestMonthsEnd' FROM dual
) src
ON (
    TRIM(tgt.field_name) = src.field_name
    AND TRIM(tgt.field_value) = src.field_value
)
WHEN NOT MATCHED THEN
    INSERT (field_name, field_value, eff_status, version, owner_flg, value_name)
    VALUES (src.field_name, src.field_value, src.eff_status, src.version, src.owner_flg, src.value_name);

MERGE INTO cisadm.ci_lookup_val_l tgt
USING (
    SELECT 'CM_SNAPSHOT_TYPE_FLG' AS field_name, 'ARCH' AS field_value, 'ENG' AS language_cd,
           1 AS version, 'Archived' AS descr, 'CM' AS owner_flg FROM dual
    UNION ALL
    SELECT 'CM_SNAPSHOT_TYPE_FLG', 'EMON', 'ENG', 1, 'Months'' Ends', 'CM' FROM dual
    UNION ALL
    SELECT 'CM_SNAPSHOT_TYPE_FLG', 'LDAY', 'ENG', 1, 'Latest Day Extracted', 'CM' FROM dual
    UNION ALL
    SELECT 'CM_SNAPSHOT_TYPE_FLG', 'LEMN', 'ENG', 1, 'Latest Month''s End', 'CM' FROM dual
) src
ON (
    TRIM(tgt.field_name) = src.field_name
    AND TRIM(tgt.field_value) = src.field_value
    AND TRIM(tgt.language_cd) = src.language_cd
)
WHEN NOT MATCHED THEN
    INSERT (field_name, field_value, language_cd, version, descr, owner_flg)
    VALUES (src.field_name, src.field_value, src.language_cd, src.version, src.descr, src.owner_flg);

COMMIT;

PROMPT Seeded CM_SNAPSHOT_TYPE_FLG values:
SELECT TRIM(field_value) AS field_value, descr
FROM cisadm.ci_lookup_val_l
WHERE TRIM(field_name) = 'CM_SNAPSHOT_TYPE_FLG'
  AND language_cd = 'ENG'
ORDER BY field_value;
