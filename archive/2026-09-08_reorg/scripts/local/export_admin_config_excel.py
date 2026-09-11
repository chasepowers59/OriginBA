#!/usr/bin/env python3
"""Export CIS Admin Configuration (Domain logic) for multiple clients to Excel."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import oracledb
import pandas as pd

from oracle_client import ensure_oracle_client, load_env_file, normalize_oracle_dsn
from run_client_oracle_sql import client_connection

REPO_ROOT = Path(__file__).resolve().parents[2]
VIEW_LOGIC_PATH = REPO_ROOT / "output/cisadm_views/demo/view_select_logic/CMS_ADMIN_CONFIG_VW.sql"
DEFAULT_CLIENTS = [
    "ellensburg",
    "fonddulac",
    "newark",
    "collegestation",
    "citycorp",
]

DOMAIN_SQL_TEMPLATE = """
SELECT
  cfg.TBL_NAME,
  cfg.TBL_DESCR,
  cfg.LANG_TBL_NAME,
  cfg.OWNER_FLG,
  cfg.MAINT_OBJ_CD,
  cfg.ENVIRONMENT,
  cfg.KEY,
  cfg.DESCR AS KEY_DESCR,
  mo.DESCR AS MAINT_OBJ_DESCR,
  tbl.DESCR AS TBL_NAME_DESCR,
  owner_l.DESCR AS OWNER_DESCR,
  env.ENV_NAME
FROM (
{view_body}
) cfg
INNER JOIN cisadm.ci_md_mo_l mo
  ON TRIM(cfg.MAINT_OBJ_CD) = TRIM(mo.MAINT_OBJ_CD)
 AND mo.LANGUAGE_CD = 'ENG'
INNER JOIN cisadm.ci_md_tbl_l tbl
  ON TRIM(cfg.TBL_NAME) = TRIM(tbl.TBL_NAME)
 AND tbl.LANGUAGE_CD = 'ENG'
LEFT JOIN cisadm.ci_lookup_val_l owner_l
  ON TRIM(cfg.OWNER_FLG) = TRIM(owner_l.FIELD_VALUE)
 AND owner_l.FIELD_NAME = 'OWNER_FLG'
 AND owner_l.LANGUAGE_CD = 'ENG'
CROSS JOIN (
  SELECT MAX(inst_msg_text) AS ENV_NAME
  FROM cisadm.ci_install_msg_l
  WHERE inst_msg_type_flg = 'F1DN'
) env
"""


def load_view_body() -> str:
    lines = VIEW_LOGIC_PATH.read_text(encoding="utf-8").splitlines()
    body = "\n".join(line for line in lines if not line.strip().startswith("--"))
    return body.rstrip().removesuffix("UNION").rstrip()


def build_domain_sql() -> str:
    return DOMAIN_SQL_TEMPLATE.format(view_body=load_view_body())


def db_connection_meta(client: str, cfg: dict) -> dict[str, str]:
    _, _, dsn = client_connection(cfg, client)
    service = dsn.split("/")[-1] if "/" in dsn else dsn
    service_upper = service.upper()
    if "PTESTDB" in service_upper or "TEST" in service_upper.split(".")[0]:
        tier = "TEST"
    elif "PPRODDB" in service_upper or "PROD" in service_upper.split(".")[0]:
        tier = "PROD"
    else:
        tier = "UNKNOWN"
    return {"DB_SERVICE": service, "DB_TIER": tier, "DB_DSN": dsn}


def fetch_client_config(client: str, cfg: dict, sql: str) -> pd.DataFrame:
    meta = db_connection_meta(client, cfg)
    user, password, dsn = client_connection(cfg, client)
    with oracledb.connect(
        user=user, password=password, dsn=normalize_oracle_dsn(dsn)
    ) as conn:
        df = pd.read_sql(sql, conn)
    df.insert(0, "CLIENT", client)
    df.insert(1, "DB_TIER", meta["DB_TIER"])
    df.insert(2, "DB_SERVICE", meta["DB_SERVICE"])
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].map(lambda v: v.strip() if isinstance(v, str) else v)
    df = df.rename(columns={"ENV_NAME": "ENV_NAME_CIS"})
    return df


def annotate_connection_meta(all_df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Add DB target metadata when rebuilding from an existing workbook."""
    all_df = all_df.copy()
    if "ENV_NAME" in all_df.columns and "ENV_NAME_CIS" not in all_df.columns:
        all_df = all_df.rename(columns={"ENV_NAME": "ENV_NAME_CIS"})
    tiers: dict[str, str] = {}
    services: dict[str, str] = {}
    for client in sorted(all_df["CLIENT"].unique()):
        meta = db_connection_meta(client, cfg)
        tiers[client] = meta["DB_TIER"]
        services[client] = meta["DB_SERVICE"]
    all_df["DB_TIER"] = all_df["CLIENT"].map(tiers)
    all_df["DB_SERVICE"] = all_df["CLIENT"].map(services)
    return all_df


def sheet_name(client: str) -> str:
    mapping = {
        "ellensburg": "Ellensburg",
        "fonddulac": "Fond_du_Lac",
        "newark": "Newark",
        "collegestation": "College_Station",
        "citycorp": "CityCorp",
    }
    return mapping.get(client, client[:31])


def client_display_name(client: str) -> str:
    return sheet_name(client)


def build_mo_pivot(all_df: pd.DataFrame) -> pd.DataFrame:
    """Key counts by maintenance object, one column per client."""
    counts = (
        all_df.groupby(["MAINT_OBJ_CD", "MAINT_OBJ_DESCR", "CLIENT"], dropna=False)
        .size()
        .reset_index(name="KEY_COUNT")
    )
    pivot = counts.pivot_table(
        index=["MAINT_OBJ_CD", "MAINT_OBJ_DESCR"],
        columns="CLIENT",
        values="KEY_COUNT",
        fill_value=0,
        aggfunc="sum",
    ).reset_index()
    pivot.columns.name = None
    client_cols = sorted(c for c in pivot.columns if c not in ("MAINT_OBJ_CD", "MAINT_OBJ_DESCR"))
    pivot["MIN_COUNT"] = pivot[client_cols].min(axis=1)
    pivot["MAX_COUNT"] = pivot[client_cols].max(axis=1)
    pivot["DELTA"] = pivot["MAX_COUNT"] - pivot["MIN_COUNT"]
    pivot["CLIENTS_WITH_DATA"] = pivot[client_cols].gt(0).sum(axis=1)
    return pivot.sort_values(["DELTA", "MAINT_OBJ_CD"], ascending=[False, True])


def build_key_matrix(all_df: pd.DataFrame) -> pd.DataFrame:
    """One row per MO+Key; Y/N presence flag per client."""
    clients = sorted(all_df["CLIENT"].unique())
    base = (
        all_df.groupby(
            ["MAINT_OBJ_CD", "MAINT_OBJ_DESCR", "TBL_NAME", "TBL_DESCR", "KEY"],
            dropna=False,
        )
        .agg(KEY_DESCR=("KEY_DESCR", "first"))
        .reset_index()
    )
    presence = (
        all_df.groupby(
            ["MAINT_OBJ_CD", "TBL_NAME", "KEY", "CLIENT"],
            dropna=False,
        )
        .size()
        .reset_index(name="_n")
    )
    for client in clients:
        client_keys = presence[presence["CLIENT"] == client][
            ["MAINT_OBJ_CD", "TBL_NAME", "KEY"]
        ].assign(**{client: "Y"})
        base = base.merge(client_keys, on=["MAINT_OBJ_CD", "TBL_NAME", "KEY"], how="left")
        base[client] = base[client].fillna("N")
    base["CLIENT_COUNT"] = base[clients].apply(
        lambda row: sum(v == "Y" for v in row), axis=1
    )
    base["IN_ALL_CLIENTS"] = base["CLIENT_COUNT"].eq(len(clients)).map({True: "Y", False: "N"})
    return base.sort_values(
        ["IN_ALL_CLIENTS", "CLIENT_COUNT", "MAINT_OBJ_CD", "TBL_NAME", "KEY"],
        ascending=[True, True, True, True, True],
    )


def _norm(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _config_key(row_or_tuple) -> tuple[str, str, str]:
    if hasattr(row_or_tuple, "get"):
        return (
            _norm(row_or_tuple.get("MAINT_OBJ_CD")),
            _norm(row_or_tuple.get("TBL_NAME")),
            _norm(row_or_tuple.get("KEY")),
        )
    mo, tbl, key = row_or_tuple
    return (_norm(mo), _norm(tbl), _norm(key))


def _sort_key_tuple(items: tuple) -> tuple:
    return _config_key(items)


def build_unique_to_client(all_df: pd.DataFrame) -> pd.DataFrame:
    """Configs that appear in exactly one client."""
    clients = sorted(all_df["CLIENT"].unique())
    key_cols = ["MAINT_OBJ_CD", "TBL_NAME", "KEY"]
    all_df = all_df.copy()
    all_df["_CONFIG_KEY"] = all_df.apply(_config_key, axis=1)
    client_sets = {
        client: set(all_df.loc[all_df["CLIENT"] == client, "_CONFIG_KEY"])
        for client in clients
    }
    rows: list[dict] = []
    for client in clients:
        others = set().union(*(client_sets[c] for c in clients if c != client))
        unique_keys = client_sets[client] - others
        if not unique_keys:
            continue
        client_df = all_df[all_df["CLIENT"] == client].drop_duplicates(subset=["_CONFIG_KEY"])
        lookup = {row["_CONFIG_KEY"]: row for _, row in client_df.iterrows()}
        for config_key in sorted(unique_keys, key=_sort_key_tuple):
            match = lookup[config_key]
            rows.append(
                {
                    "CLIENT": client,
                    "MAINT_OBJ_CD": match["MAINT_OBJ_CD"],
                    "MAINT_OBJ_DESCR": match["MAINT_OBJ_DESCR"],
                    "TBL_NAME": match["TBL_NAME"],
                    "TBL_DESCR": match["TBL_DESCR"],
                    "KEY": match["KEY"],
                    "KEY_DESCR": match["KEY_DESCR"],
                }
            )
    return pd.DataFrame(rows)


def build_gaps(all_df: pd.DataFrame) -> pd.DataFrame:
    """Configs not present in every client, with present/missing lists."""
    clients = sorted(all_df["CLIENT"].unique())
    all_df = all_df.copy()
    all_df["_CONFIG_KEY"] = all_df.apply(_config_key, axis=1)
    meta = (
        all_df.groupby("_CONFIG_KEY", dropna=False)
        .agg(
            MAINT_OBJ_CD=("MAINT_OBJ_CD", "first"),
            TBL_NAME=("TBL_NAME", "first"),
            KEY=("KEY", "first"),
            MAINT_OBJ_DESCR=("MAINT_OBJ_DESCR", "first"),
            TBL_DESCR=("TBL_DESCR", "first"),
            KEY_DESCR=("KEY_DESCR", "first"),
        )
        .reset_index()
    )
    presence = (
        all_df.groupby(["_CONFIG_KEY", "CLIENT"], dropna=False)
        .size()
        .reset_index(name="_n")
    )
    present_map = (
        presence.groupby("_CONFIG_KEY")["CLIENT"]
        .apply(lambda s: sorted(set(s)))
        .reset_index(name="PRESENT_CLIENTS")
    )
    matrix = meta.merge(present_map, on="_CONFIG_KEY", how="left")
    matrix = matrix.drop(columns=["_CONFIG_KEY"], errors="ignore")
    matrix["CLIENT_COUNT"] = matrix["PRESENT_CLIENTS"].map(len)
    matrix = matrix[matrix["CLIENT_COUNT"] < len(clients)].copy()
    matrix["MISSING_CLIENTS"] = matrix["PRESENT_CLIENTS"].map(
        lambda present: sorted(set(clients) - set(present or []))
    )
    matrix["PRESENT_CLIENTS"] = matrix["PRESENT_CLIENTS"].map(
        lambda present: ", ".join(present or [])
    )
    matrix["MISSING_CLIENTS"] = matrix["MISSING_CLIENTS"].map(", ".join)
    return matrix.sort_values(
        ["CLIENT_COUNT", "MAINT_OBJ_CD", "TBL_NAME", "KEY"],
        ascending=[True, True, True, True],
    )


def build_summary(all_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for client, grp in all_df.groupby("CLIENT", sort=True):
        rows.append(
            {
                "CLIENT": client,
                "DB_TIER": grp["DB_TIER"].dropna().iloc[0] if len(grp) else None,
                "DB_SERVICE": grp["DB_SERVICE"].dropna().iloc[0] if len(grp) else None,
                "ENV_NAME_CIS": grp["ENV_NAME_CIS"].dropna().iloc[0] if len(grp) else None,
                "ROW_COUNT": len(grp),
                "DISTINCT_MAINT_OBJ": grp["MAINT_OBJ_CD"].nunique(),
                "DISTINCT_TABLE": grp["TBL_NAME"].nunique(),
                "DISTINCT_MO_KEY": grp.apply(
                    lambda r: f"{r['MAINT_OBJ_CD']}_{r['KEY']}", axis=1
                ).nunique(),
            }
        )
    return pd.DataFrame(rows)


def export_excel(all_df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_df = build_summary(all_df)
    column_order = [
        "CLIENT",
        "DB_TIER",
        "DB_SERVICE",
        "ENV_NAME_CIS",
        "TBL_NAME",
        "TBL_DESCR",
        "LANG_TBL_NAME",
        "MAINT_OBJ_CD",
        "MAINT_OBJ_DESCR",
        "KEY",
        "KEY_DESCR",
        "OWNER_FLG",
        "OWNER_DESCR",
        "ENVIRONMENT",
        "TBL_NAME_DESCR",
    ]

    mo_pivot_df = build_mo_pivot(all_df)
    key_matrix_df = build_key_matrix(all_df)
    unique_df = build_unique_to_client(all_df)
    gaps_df = build_gaps(all_df)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        mo_pivot_df.to_excel(writer, sheet_name="Compare_MO_Pivot", index=False)
        key_matrix_df.to_excel(writer, sheet_name="Compare_Key_Matrix", index=False)
        gaps_df.to_excel(writer, sheet_name="Compare_Gaps", index=False)
        unique_df.to_excel(writer, sheet_name="Compare_Unique", index=False)
        all_df[column_order].to_excel(writer, sheet_name="All_Clients", index=False)
        for client in sorted(all_df["CLIENT"].unique()):
            client_df = all_df[all_df["CLIENT"] == client][column_order]
            client_df.to_excel(writer, sheet_name=sheet_name(client), index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--clients",
        nargs="+",
        default=DEFAULT_CLIENTS,
        help="Client aliases from .env",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output .xlsx path (default: output/spreadsheet/admin_config_<timestamp>.xlsx)",
    )
    parser.add_argument(
        "--from-xlsx",
        type=Path,
        default=None,
        help="Rebuild workbook (including comparison sheets) from an existing All_Clients export",
    )
    args = parser.parse_args()

    errors: list[str] = []
    if args.from_xlsx:
        print(f"Loading existing data from {args.from_xlsx}...")
        cfg = load_env_file(REPO_ROOT / ".env")
        all_df = pd.read_excel(args.from_xlsx, sheet_name="All_Clients")
        all_df = annotate_connection_meta(all_df, cfg)
        output_path = args.output or args.from_xlsx
    else:
        cfg = load_env_file(REPO_ROOT / ".env")
        ensure_oracle_client(cfg)
        sql = build_domain_sql()

        frames: list[pd.DataFrame] = []
        for client in args.clients:
            print(f"Querying {client}...")
            try:
                frames.append(fetch_client_config(client, cfg, sql))
                print(f"  rows: {len(frames[-1])}")
            except Exception as exc:
                errors.append(f"{client}: {exc}")
                print(f"  FAILED: {exc}")

        if not frames:
            raise SystemExit("No client data retrieved.\n" + "\n".join(errors))

        all_df = pd.concat(frames, ignore_index=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = args.output or (
            REPO_ROOT / f"output/spreadsheet/admin_config_254_clients_{timestamp}.xlsx"
        )

    export_excel(all_df, output_path)
    print(f"Wrote {output_path}")
    print(f"Total rows: {len(all_df)} across {all_df['CLIENT'].nunique()} clients")
    if errors:
        print("Errors:")
        for err in errors:
            print(f"  - {err}")


if __name__ == "__main__":
    main()
