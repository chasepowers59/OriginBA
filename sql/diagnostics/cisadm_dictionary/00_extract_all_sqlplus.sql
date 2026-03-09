-- 00_extract_all_sqlplus.sql
-- SQL*Plus/SQLcl driver to export full CISADM dictionary discovery pack.
--
-- Usage:
--   sqlplus user/password@host:1521/service @00_extract_all_sqlplus.sql
--
-- Optional:
--   define schema_owner = CISADM
--   define out_dir = output/cisadm_dictionary

set define on
set verify off
set feedback off
set heading on
set trimspool on
set pagesize 50000
set linesize 32767
set markup csv on quote on
whenever sqlerror exit failure

define schema_owner = CISADM
define out_dir = output/cisadm_dictionary

prompt ===== CISADM dictionary extraction started =====
prompt schema_owner=&schema_owner
prompt out_dir=&out_dir

spool &out_dir/tables.csv
@01_tables.sql
spool off

spool &out_dir/columns.csv
@02_columns.sql
spool off

spool &out_dir/constraints.csv
@03_constraints.sql
spool off

spool &out_dir/constraint_columns.csv
@04_constraint_columns.sql
spool off

spool &out_dir/indexes.csv
@05_indexes.sql
spool off

spool &out_dir/index_columns.csv
@06_index_columns.sql
spool off

spool &out_dir/views.csv
@07_views.sql
spool off

spool &out_dir/view_dependencies.csv
@08_view_dependencies.sql
spool off

spool &out_dir/mviews.csv
@09_mviews.sql
spool off

spool &out_dir/synonyms_to_cisadm.csv
@10_synonyms_to_cisadm.sql
spool off

spool &out_dir/table_partitions.csv
@11_table_partitions.sql
spool off

spool &out_dir/table_stats.csv
@12_table_stats.sql
spool off

spool &out_dir/column_stats.csv
@13_column_stats.sql
spool off

spool &out_dir/fk_join_map.csv
@14_fk_join_map.sql
spool off

spool &out_dir/keyword_table_map.csv
@15_keyword_table_map.sql
spool off

prompt ===== CISADM dictionary extraction complete =====
exit

