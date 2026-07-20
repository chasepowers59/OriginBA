CREATE OR REPLACE FORCE EDITIONABLE VIEW "CISADM"."F1_MENU_APP_SVCS_VW" ("MENU_LINE_ID", "APP_SVC_ID", "LINE_VISIBILITY_SW") DEFAULT COLLATION "USING_NLS_COMP"  AS 
  with 
linesvc as
(
select /*+ materialize leading(a) use_nl(svc key nav a) */ a.menu_line_id, a.app_svc_id item_app_svc_id, s.svc_name, s.app_svc_id, a.nav_opt_cd
from ci_md_menu_item a,
     ci_md_nav key,
     CI_MD_SVC_PRG svc,
     CI_MD_SVC s,
     ci_nav_opt nav
where nav.target_nav_key = key.navigation_key
and key.prog_com_id = svc.prog_com_id
and svc.svc_name = s.svc_name
and a.nav_opt_cd = nav.nav_opt_cd
),
/* MO associated with the line navigation option =  maintenance BPA MO option, Query Portal MO option, MO page service, All-in-one BO portal */
linemo as
(
SELECT /*+ leading(mo) use_nl(key svc mo) */  mo.maint_obj_cd, ' ' scr_cd, a.menu_line_id
from ci_md_menu_item a,
     ci_md_nav key,
     CI_MD_SVC_PRG svc,
     CI_MD_SVC s,
     ci_nav_opt nav,
     ci_md_mo mo
where a.nav_opt_cd = nav.nav_opt_cd
and nav.target_nav_key = key.navigation_key
and key.prog_com_id = svc.prog_com_id
and svc.svc_name = s.svc_name
and mo.svc_name = s.svc_name
union all
select /*+ leading(moopt) */  moopt.maint_obj_cd, nav.scr_cd, a.menu_line_id
from ci_md_menu_item a,
     ci_md_mo_opt moopt,
     ci_nav_opt nav
where nav.nav_opt_type_flg = 'F1SC'
and nav.scr_cd = rpad(moopt.maint_obj_opt_val,12)
and moopt.maint_obj_opt_flg = 'F1MB'
and a.nav_opt_cd = nav.nav_opt_cd
union all
select /*+ leading(boopt) */  bo.maint_obj_cd, nav.scr_cd, a.menu_line_id
from ci_md_menu_item a,
     f1_bus_obj_opt boopt,
     f1_bus_obj bo,
     ci_nav_opt nav
where nav.nav_opt_type_flg = 'F1SC'
and nav.scr_cd = rpad(boopt.bus_obj_opt_val,12)
and boopt.bus_obj_opt_flg = 'F1MB'
and boopt.bus_obj_cd = bo.bus_obj_cd
and a.nav_opt_cd = nav.nav_opt_cd
union all
select /*+ leading(moopt) */ moopt.maint_obj_cd, ' ' scr_cd, a.menu_line_id
from linesvc a,
     ci_md_mo_opt moopt
where a.nav_opt_cd = rpad(moopt.maint_obj_opt_val,32)
and moopt.maint_obj_opt_flg = 'F1QN'
union all
select /*+ leading(mo) */  mo.maint_obj_cd, ' ' scr_cd, a.menu_line_id
from linesvc a,
     ci_md_mo mo,
     CI_MD_SVC s
where a.app_svc_id = s.app_svc_id
and s.svc_name = mo.svc_name
union all
select /*+ leading(boopt) */  bo.maint_obj_cd, ' ' scr_cd, a.menu_line_id
from linesvc a,
     f1_bus_obj bo,
     f1_bus_obj_opt boopt
where a.nav_opt_cd = rpad(boopt.bus_obj_opt_val,32)
and bo.bus_obj_cd = boopt.bus_obj_cd
and boopt.bus_obj_opt_flg = 'F1NO'
union all
select /*+ leading(mo) */  mo.maint_obj_cd, ' ' scr_cd, a.menu_line_id
from ci_md_menu_item a,
     ci_md_mo mo,
     CI_MD_SVC s
where a.app_svc_id > ' ' 
and a.app_svc_id = s.app_svc_id
and s.svc_name = mo.svc_name
),
/* all MOs include related MOs via MO option */
linemos as
(
select a.maint_obj_cd, a.scr_cd, a.menu_line_id
from linemo a
union
select /*+ leading(a) */ b.maint_obj_cd, ' ' scr_cd, a.menu_line_id
from linemo a, 
     ci_md_mo_opt moopt,
     ci_md_mo b
where a.maint_obj_cd = moopt.maint_obj_cd
and moopt.maint_obj_opt_flg = 'F1CH'
and b.maint_obj_cd = rpad(moopt.maint_obj_opt_val,12)
),
linebos as 
(
select /*+ leading(a) */ bo.bus_obj_cd, bo.app_svc_id, a.menu_line_id 
from linemos a,
     f1_bus_obj bo
where a.maint_obj_cd = bo.maint_obj_cd
and not exists 
(
select /*+ no_unnest  */ 'x' 
from f1_bus_obj_opt boopt, 
     ci_nav_opt bonav, 
     ci_md_menu_item boitm
where a.scr_cd > ' ' 
and bo.bus_obj_cd = boopt.bus_obj_cd 
and boopt.bus_obj_opt_flg = 'F1MB' 
and a.scr_cd <> rpad(boopt.bus_obj_opt_val,12)
and rpad(boopt.bus_obj_opt_val,12) = bonav.scr_cd 
and bonav.nav_opt_cd = boitm.nav_opt_cd 
)     
),
/* navigation options associated with the line = directly and via the BOs of the line MO */
linenavopts as
(
select a.menu_line_id, a.nav_opt_cd
from ci_md_menu_item a
union 
select /*+ leading(boopt) */ a.menu_line_id, rpad(boopt.bus_obj_opt_val,32) nav_opt_cd
from linebos a,
     f1_bus_obj_opt boopt
where a.bus_obj_cd = boopt.bus_obj_cd
and boopt.bus_obj_opt_flg = 'F1NO'
),
/* portals associated with the line */
linenavportals as 
(
select /*+ leading(a) */ a.menu_line_id, prtl.portal_cd, s.app_svc_id, prtl.prog_com_id 
from linenavopts a,
     ci_nav_opt nav,
     ci_md_nav key,
     ci_portal prtl,
     CI_MD_SVC_PRG svc,
     CI_MD_SVC s     
where a.nav_opt_cd = nav.nav_opt_cd
and nav.target_nav_key = key.navigation_key
and key.prog_com_id = prtl.prog_com_id 
and key.prog_com_id = svc.prog_com_id
and svc.svc_name = s.svc_name
),
lineportals as 
(
select a.menu_line_id, a.portal_cd, a.app_svc_id, a.prog_com_id
from linenavportals a
union all
select /*+ leading(prtlo) */ a.menu_line_id, a.portal_cd, s.app_svc_id, prtl.prog_com_id
from linenavportals a,
     ci_portal_opt prtlo,
     ci_portal prtl,
     CI_MD_SVC_PRG svc,
     CI_MD_SVC s        
where a.portal_cd = prtlo.portal_cd
and prtlo.portal_opt_flg = 'F1RP'
and rpad(prtlo.portal_opt_val,12) = prtl.portal_cd 
and prtl.prog_com_id = svc.prog_com_id
and svc.svc_name = s.svc_name
)
select distinct menu_line_id, app_svc_id, line_visibility_sw
from 
(
/* menu line and items */
/* */
/* application service directly defined on the menu line */
select a.menu_line_id, 'MENU_ITEM' itemtype, a.menu_item_id item, a.app_svc_id app_svc_id, 'Y' line_visibility_sw 
from ci_md_menu_item a
where a.app_svc_id > ' '
union all
/* application service of the page or portal defined on the menu line */
select menu_line_id, 'SVC_NAME' itemtype, linesvc.svc_name item, linesvc.app_svc_id, 'Y' line_visibility_sw
from linesvc
union all
/* application services associated with all portals of all navigation options. Inlcudes all BO maintenance portals for the MO. */
select menu_line_id, 'PORTAL' itemtype, a.portal_cd item, a.app_svc_id, ' ' line_visibility_sw
from lineportals a
union all 
/* application services associated with all zones of all portals */
select /*+ leading(a) */ a.menu_line_id, 'ZONE' item_type, zone.zone_cd item, zone.app_svc_id, ' ' line_visibility_sw
from lineportals a,
     ci_portal_zone pz,
     ci_zone zone
where a.portal_cd = pz.portal_cd 
and pz.zone_cd = zone.zone_cd 
union all
/* application services associated with all zones of all tab portals of all portals */
select /*+ leading(a) */ a.menu_line_id, 'ZONE' item_type, zone.zone_cd item, zone.app_svc_id, ' ' line_visibility_sw
from lineportals a,
     ci_md_prg_tab q,
     ci_portal b,
     ci_md_nav nav,
     CI_MD_PRG_VAR var,
     ci_portal_zone pz,
     ci_zone zone
where a.prog_com_id = q.prog_com_id
and q.navigation_key = nav.navigation_key
and nav.prog_com_id = var.PROG_COM_ID
and var.var_name = 'portalName          '
and trim(var.VAR_VAL) = trim(b.portal_cd)
and b.portal_cd <> a.portal_cd
and b.portal_cd = pz.portal_cd 
and pz.zone_cd = zone.zone_cd 
union all
select /*+ leading(var) */ distinct a.menu_line_id, 'ZONE' item_type, zone.zone_cd item, zone.app_svc_id, ' ' line_visibility_sw
from ci_md_menu_item a,
     ci_nav_opt nav,
     ci_md_nav key,
     ci_md_prg_tab tab,
     ci_md_nav tabkey,
     ci_md_prg_var var,
     ci_portal prtl,
     ci_portal_zone pz,
     ci_zone zone     
where a.nav_opt_cd = nav.nav_opt_cd
and nav.target_nav_key = key.navigation_key
and key.prog_com_id = tab.prog_com_id
and tab.navigation_key = tabkey.navigation_key
and tabkey.prog_com_id = var.prog_com_id
and var.var_name = 'PORTAL'
and rpad(var.var_val,12) = prtl.portal_cd
and prtl.portal_cd = pz.portal_cd
and pz.zone_cd = zone.zone_cd
union all
/* application services associated with the MO */
select /*+ leading(a) */ a.menu_line_id, 'MO' itemtype, a.maint_obj_cd item, s.app_svc_id, ' ' line_visibility_sw 
from linemos a,
     ci_md_mo mo,
     CI_MD_SVC s
where a.maint_obj_cd = mo.maint_obj_cd
and mo.svc_name = s.svc_name
union all
/* application services associated with all BOs */
select bo.menu_line_id, 'BO' itemtype, bo.bus_obj_cd item, bo.app_svc_id, ' ' line_visibility_sw
from linebos bo
where bo.app_svc_id > ' '
union all
/* application services related to all BOs */
select /*+ leading(boopt) */ a.menu_line_id, 'APP SVC' itemtype, a.bus_obj_cd item, svc.app_svc_id,  ' ' line_visibility_sw
from linebos a,
     f1_bus_obj_opt boopt,
     sc_app_service svc
where a.bus_obj_cd = boopt.bus_obj_cd
and boopt.bus_obj_opt_flg = 'F1SV'
and svc.app_svc_id = rpad(boopt.bus_obj_opt_val,20)
union all
/* application service of the item BPA script */
select /*+ leading(a) */ a.menu_line_id, 'BPA' itemtype, q.scr_cd item, q.app_svc_id, ' ' line_visibility_sw 
from ci_md_menu_item a,
     ci_scr q,
     ci_nav_opt nav
where nav.scr_cd = q.scr_cd
and q.app_svc_id > ' '
and a.nav_opt_cd = nav.nav_opt_cd
union all
/* detail fixed page from a summary fixed page */
Select /*+ leading(elm) */ a.menu_line_id, 'RELATED_SVC' itemtype, svc.svc_name item, svc.app_svc_id, ' ' line_visibility_sw
from linesvc a, ci_md_svc_prg tabsvcprg, ci_md_prg_tab tab, ci_md_nav elmpgnav, ci_md_prg_elem elmpg, ci_md_prg_com secpg, ci_md_prg_sec sec, ci_md_prg_elem elm, ci_md_nav nav, ci_md_svc_prg spg, ci_md_svc svc     
where tabsvcprg.svc_name = a.svc_name
and tab.prog_com_id = tabsvcprg.prog_com_id 
and elmpgnav.navigation_key = tab.navigation_key 
and elmpg.prog_com_id = elmpgnav.prog_com_id 
and elmpg.url = secpg.prog_com_name
and secpg.prog_com_id = sec.prog_com_id
and sec.prog_com_id = elm.prog_com_id 
and elm.script > ' '
and elm.script not like '%Search%'
and elm.script like '%'||trim(nav.navigation_key)||'%'
and not exists (select 'x' from ci_nav_opt npt, ci_md_menu_item itm where npt.target_nav_key = nav.navigation_key and npt.nav_opt_cd =  itm.nav_opt_cd)
and spg.prog_com_id = nav.prog_com_id
and svc.svc_name = spg.svc_name
and nav.owner_flg = elm.owner_flg
and nav.navigation_key in ('algorithmTab','toDoEntryMaint')
);
