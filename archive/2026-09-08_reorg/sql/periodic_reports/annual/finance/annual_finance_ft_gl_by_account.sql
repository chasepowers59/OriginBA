-- PERIODIC_REPORT: A4 annual_finance_ft_gl_by_account
-- FREQUENCY: annual
-- WORKSTREAM: finance
-- GRAIN: GL_ACCT + DST_ID
-- WINDOW: previous full calendar year
-- SOURCE: CI_FT + CI_FT_GL (snapshot window too short for annual GL)
-- GOVERNED: freeze_sw = Y, exclude ODEV

SELECT gl.gl_acct,
       gl.dst_id,
       COUNT(*) AS gl_line_count,
       SUM(CASE WHEN gl.amount > 0 THEN gl.amount ELSE 0 END) AS total_debit_amt,
       SUM(CASE WHEN gl.amount < 0 THEN ABS(gl.amount) ELSE 0 END) AS total_credit_amt,
       SUM(gl.amount) AS net_gl_amt
FROM cisadm.ci_ft ft
JOIN cisadm.ci_ft_gl gl
  ON gl.ft_id = ft.ft_id
WHERE ft.accounting_dt >= TRUNC(ADD_MONTHS(SYSDATE, -12), 'YYYY')
  AND ft.accounting_dt < TRUNC(SYSDATE, 'YYYY')
  AND ft.freeze_sw = 'Y'
  AND ft.redundant_sw = 'N'
  AND ft.acct_id NOT LIKE 'ODEV%'
GROUP BY gl.gl_acct, gl.dst_id
ORDER BY gl.gl_acct, gl.dst_id;
