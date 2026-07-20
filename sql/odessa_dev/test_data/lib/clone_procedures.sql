  PROCEDURE assert_true(p_condition BOOLEAN, p_message VARCHAR2) IS
  BEGIN
    IF NOT p_condition THEN
      RAISE_APPLICATION_ERROR(-20001, 'VALIDATION FAILED: ' || p_message);
    END IF;
  END assert_true;

  PROCEDURE assert_count_eq(
    p_sql      VARCHAR2,
    p_expected NUMBER,
    p_message  VARCHAR2
  ) IS
    l_actual NUMBER;
  BEGIN
    EXECUTE IMMEDIATE 'SELECT COUNT(*) FROM (' || p_sql || ')' INTO l_actual;
    IF l_actual <> p_expected THEN
      RAISE_APPLICATION_ERROR(
        -20001,
        'VALIDATION FAILED: ' || p_message
          || ' (expected ' || p_expected || ', got ' || NVL(TO_CHAR(l_actual), 'NULL') || ')'
      );
    END IF;
  END assert_count_eq;

  PROCEDURE assert_count_ge(
    p_sql      VARCHAR2,
    p_minimum  NUMBER,
    p_message  VARCHAR2
  ) IS
    l_actual NUMBER;
  BEGIN
    EXECUTE IMMEDIATE 'SELECT COUNT(*) FROM (' || p_sql || ')' INTO l_actual;
    IF l_actual < p_minimum THEN
      RAISE_APPLICATION_ERROR(
        -20001,
        'VALIDATION FAILED: ' || p_message
          || ' (expected >= ' || p_minimum || ', got ' || NVL(TO_CHAR(l_actual), 'NULL') || ')'
      );
    END IF;
  END assert_count_ge;

  PROCEDURE insert_clone(
    p_table     VARCHAR2,
    p_where     VARCHAR2,
    p_overrides t_override_map,
    p_rows      OUT NUMBER
  ) IS
    l_col_list VARCHAR2(32767);
    l_sel_list VARCHAR2(32767);
    l_col_name VARCHAR2(128);
    l_first    BOOLEAN := TRUE;
  BEGIN
    FOR rec IN (
      SELECT column_name
        FROM all_tab_columns
       WHERE owner = 'CISADM'
         AND table_name = UPPER(p_table)
         AND column_name NOT IN ('DATA_GRID_ID')
       ORDER BY column_id
    ) LOOP
      l_col_name := UPPER(rec.column_name);
      IF l_first THEN
        l_col_list := rec.column_name;
        IF p_overrides.EXISTS(l_col_name) THEN
          l_sel_list := p_overrides(l_col_name);
        ELSE
          l_sel_list := 'src.' || rec.column_name;
        END IF;
        l_first := FALSE;
      ELSE
        l_col_list := l_col_list || ', ' || rec.column_name;
        IF p_overrides.EXISTS(l_col_name) THEN
          l_sel_list := l_sel_list || ', ' || p_overrides(l_col_name);
        ELSE
          l_sel_list := l_sel_list || ', src.' || rec.column_name;
        END IF;
      END IF;
    END LOOP;

    EXECUTE IMMEDIATE
      'INSERT INTO cisadm.' || UPPER(p_table) || ' (' || l_col_list || ') '
      || 'SELECT ' || l_sel_list || ' FROM cisadm.' || UPPER(p_table) || ' src WHERE ' || p_where;

    p_rows := SQL%ROWCOUNT;
  END insert_clone;

  PROCEDURE set_override(
    p_overrides IN OUT NOCOPY t_override_map,
    p_column    VARCHAR2,
    p_expr      VARCHAR2
  ) IS
  BEGIN
    p_overrides(UPPER(p_column)) := p_expr;
  END set_override;

  PROCEDURE clear_overrides(p_overrides IN OUT NOCOPY t_override_map) IS
  BEGIN
    p_overrides.DELETE;
  END clear_overrides;
