-- PERIODIC_REPORT: Q4 quarterly_finance_ft_gl_by_fund
-- FREQUENCY: quarterly
-- WORKSTREAM: finance
-- GRAIN: GL_DIVISION + GL_ACCT
-- WINDOW: previous full calendar quarter
-- SOURCE: FT_GL_DISTRIBUTION_RPT_CURR

SELECT gl.gl_division,
       gl.gl_division_desc,
       gl.gl_acct,
       COUNT(*) AS gl_line_count,
       SUM(gl.debit_amt) AS total_debit_amt,
       SUM(gl.credit_amt) AS total_credit_amt,
       SUM(gl.gl_amount) AS net_gl_amt
FROM cisadm.ft_gl_distribution_rpt_curr gl
WHERE gl.accounting_dt >= TRUNC(ADD_MONTHS(SYSDATE, -3), 'Q')
  AND gl.accounting_dt < TRUNC(SYSDATE, 'Q')
  AND NULLIF(TRIM(gl.freeze_sw), '') = 'Y'
  AND gl.acct_id NOT LIKE 'ODEV%'
GROUP BY gl.gl_division, gl.gl_division_desc, gl.gl_acct
ORDER BY gl.gl_division, gl.gl_acct;
