CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."W1_BI_NODE_HIERARCHY_VW" ("NODE_ID", "DESCR100", "NODE_BUS_OBJ_DESCR100", "NODE_ID_LVL1", "DESCR100_LVL1", "NODE_BUS_OBJ_DESCR100_LVL1", "NODE_ID_LVL2", "DESCR100_LVL2", "NODE_BUS_OBJ_DESCR100_LVL2", "NODE_ID_LVL3", "DESCR100_LVL3", "NODE_BUS_OBJ_DESCR100_LVL3", "NODE_ID_LVL4", "DESCR100_LVL4", "NODE_BUS_OBJ_DESCR100_LVL4", "NODE_ID_LVL5", "DESCR100_LVL5", "NODE_BUS_OBJ_DESCR100_LVL5", "NODE_ID_LVL6", "DESCR100_LVL6", "NODE_BUS_OBJ_DESCR100_LVL6", "NODE_ID_LVL7", "DESCR100_LVL7", "NODE_BUS_OBJ_DESCR100_LVL7", "NODE_ID_LVL8", "DESCR100_LVL8", "NODE_BUS_OBJ_DESCR100_LVL8", "NODE_ID_LVL9", "DESCR100_LVL9", "NODE_BUS_OBJ_DESCR100_LVL9", "NODE_ID_LVL10", "DESCR100_LVL10", "NODE_BUS_OBJ_DESCR100_LVL10", "NODE_ID_LVL11", "DESCR100_LVL11", "NODE_BUS_OBJ_DESCR100_LVL11", "NODE_ID_LVL12", "DESCR100_LVL12", "NODE_BUS_OBJ_DESCR100_LVL12", "NODE_ID_LVL13", "DESCR100_LVL13", "NODE_BUS_OBJ_DESCR100_LVL13", "NODE_ID_LVL14", "DESCR100_LVL14", "NODE_BUS_OBJ_DESCR100_LVL14", "NODE_ID_LVL15", "DESCR100_LVL15", "NODE_BUS_OBJ_DESCR100_LVL15") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  with hierarchynodes as
(select /*+ materialize */ node_id, parent_node_id, bus_obj_cd, descr100
from w1_node q
WHERE q.parent_node_id is not null 
 union 
 select node_id, parent_node_id, bus_obj_cd, descr100
from w1_node q
WHERE q.parent_node_id is null and exists (select 'x' from W1_NODE NX where q.NODE_ID = NX.PARENT_NODE_ID)
)
select NODE_ID, descr100, bus_obj_cd AS NODE_BUS_OBJ_DESCR100, 
NODE_ID_LVL1, nvl2(descrs1, trim(substr(descrs1,1,100)), descr100) as DESCR100_LVL1, nvl2(descrs1, substr(descrs1,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL1,
NODE_ID_LVL2, nvl2(descrs2, trim(substr(descrs2,1,100)), descr100) as DESCR100_LVL2, nvl2(descrs2, substr(descrs2,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL2,
NODE_ID_LVL3, nvl2(descrs3, trim(substr(descrs3,1,100)), descr100) as DESCR100_LVL3, nvl2(descrs3, substr(descrs3,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL3,
NODE_ID_LVL4, nvl2(descrs4, trim(substr(descrs4,1,100)), descr100) as DESCR100_LVL4, nvl2(descrs4, substr(descrs4,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL4,
NODE_ID_LVL5, nvl2(descrs5, trim(substr(descrs5,1,100)), descr100) as DESCR100_LVL5, nvl2(descrs5, substr(descrs5,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL5,
NODE_ID_LVL6, nvl2(descrs6, trim(substr(descrs6,1,100)), descr100) as DESCR100_LVL6, nvl2(descrs6, substr(descrs6,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL6,
NODE_ID_LVL7, nvl2(descrs7, trim(substr(descrs7,1,100)), descr100) as DESCR100_LVL7, nvl2(descrs7, substr(descrs7,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL7,
NODE_ID_LVL8, nvl2(descrs8, trim(substr(descrs8,1,100)), descr100) as DESCR100_LVL8, nvl2(descrs8, substr(descrs8,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL8,
NODE_ID_LVL9, nvl2(descrs9, trim(substr(descrs9,1,100)), descr100) as DESCR100_LVL9, nvl2(descrs9, substr(descrs9,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL9,
NODE_ID_LVL10, nvl2(descrs10, trim(substr(descrs10,1,100)), descr100) as DESCR100_LVL10, nvl2(descrs10, substr(descrs10,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL10,
NODE_ID_LVL11, nvl2(descrs11, trim(substr(descrs11,1,100)), descr100) as DESCR100_LVL11, nvl2(descrs11, substr(descrs11,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL11,
NODE_ID_LVL12, nvl2(descrs12, trim(substr(descrs12,1,100)), descr100) as DESCR100_LVL12, nvl2(descrs12, substr(descrs12,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL12,
NODE_ID_LVL13, nvl2(descrs13, trim(substr(descrs13,1,100)), descr100) as DESCR100_LVL13, nvl2(descrs13, substr(descrs13,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL13,
NODE_ID_LVL14, nvl2(descrs14, trim(substr(descrs14,1,100)), descr100) as DESCR100_LVL14, nvl2(descrs14, substr(descrs14,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL14,
NODE_ID_LVL15, nvl2(descrs15, trim(substr(descrs15,1,100)), descr100) as DESCR100_LVL15, nvl2(descrs15, substr(descrs15,104), bus_obj_cd) as NODE_BUS_OBJ_DESCR100_LVL15
from
(
select vw.*,
decode(sign(hierarchyLevel),   1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL1), null) descrs1,
decode(sign(hierarchyLevel-1), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL2), null) descrs2,
decode(sign(hierarchyLevel-2), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL3), null) descrs3,
decode(sign(hierarchyLevel-3), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL4), null) descrs4,
decode(sign(hierarchyLevel-4), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL5), null) descrs5,
decode(sign(hierarchyLevel-5), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL6), null) descrs6,
decode(sign(hierarchyLevel-6), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL7), null) descrs7,
decode(sign(hierarchyLevel-7), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL8), null) descrs8,
decode(sign(hierarchyLevel-8), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL9), null) descrs9,
decode(sign(hierarchyLevel-9), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL10), null) descrs10,
decode(sign(hierarchyLevel-10), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL11), null) descrs11,
decode(sign(hierarchyLevel-11), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL12), null) descrs12,
decode(sign(hierarchyLevel-12), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL13), null) descrs13,
decode(sign(hierarchyLevel-13), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL14), null) descrs14,
decode(sign(hierarchyLevel-14), 1, (select rpad(z.descr100,100,' ')||'###'||z.bus_obj_cd from w1_node z where z.node_id = NODE_ID_LVL15), null) descrs15
from 
(
select NODE_ID, bus_obj_cd, descr100, hierarchyLevel, hierarchyPath,
decode(sign(hierarchyLevel), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,1)+1,12), NODE_ID) NODE_ID_LVL1,
decode(sign(hierarchyLevel-1), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,2)+1,12), NODE_ID) NODE_ID_LVL2,
decode(sign(hierarchyLevel-2), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,3)+1,12), NODE_ID) NODE_ID_LVL3,
decode(sign(hierarchyLevel-3), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,4)+1,12), NODE_ID) NODE_ID_LVL4,
decode(sign(hierarchyLevel-4), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,5)+1,12), NODE_ID) NODE_ID_LVL5,
decode(sign(hierarchyLevel-5), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,6)+1,12), NODE_ID) NODE_ID_LVL6,
decode(sign(hierarchyLevel-6), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,7)+1,12), NODE_ID) NODE_ID_LVL7,
decode(sign(hierarchyLevel-7), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,8)+1,12), NODE_ID) NODE_ID_LVL8,
decode(sign(hierarchyLevel-8), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,9)+1,12), NODE_ID) NODE_ID_LVL9,
decode(sign(hierarchyLevel-9), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,10)+1,12), NODE_ID) NODE_ID_LVL10,
decode(sign(hierarchyLevel-10), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,11)+1,12), NODE_ID) NODE_ID_LVL11,
decode(sign(hierarchyLevel-11), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,12)+1,12), NODE_ID) NODE_ID_LVL12,
decode(sign(hierarchyLevel-12), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,13)+1,12), NODE_ID) NODE_ID_LVL13,
decode(sign(hierarchyLevel-13), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,14)+1,12), NODE_ID) NODE_ID_LVL14,
decode(sign(hierarchyLevel-14), 1, substr(hierarchyPath,instr(hierarchyPath,'/',1,15)+1,12), NODE_ID) NODE_ID_LVL15
from
(
SELECT NODE_ID, bus_obj_cd, nvl(trim(descr100),' ') descr100, LEVEL-1 hierarchyLevel, SYS_CONNECT_BY_PATH(node_id, '/') hierarchyPath
FROM hierarchynodes q
start with q.parent_node_id is null
CONNECT BY PRIOR NODE_ID = PARENT_NODE_ID 
)
where hierarchyLevel <=15
) vw
);
