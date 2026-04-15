ALTER TABLE cisadm.d1_usage_rpt_curr
    MODIFY (
        d2_skip_reason_flg VARCHAR2(100),
        date_break VARCHAR2(254),
        profile_factor_cd VARCHAR2(254),
        factor_char_value VARCHAR2(400),
        scalar_min_offset_days VARCHAR2(100),
        scalar_max_offset_days VARCHAR2(100)
    );
