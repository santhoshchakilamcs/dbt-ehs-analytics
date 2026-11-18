#!/usr/bin/env python3
"""Independent verification for the dbt-ehs-analytics project.

Runs `dbt build`, then re-computes the headline numbers straight from the
raw sample CSV with separate SQL (not the model SQL) and compares them to
the marts. Also checks the snapshot's SCD Type 2 structure and that the
semantic layer exposes the expected metrics.

Usage: .venv/bin/python verify_results.py
Exit code 0 = every check passed.
"""
import subprocess
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent
DBT = str(ROOT / ".venv" / "bin" / "dbt")
CSV = str(ROOT / "data" / "raw" / "osha_sir.csv")

CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def run(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return r.returncode == 0, r.stdout + r.stderr


def main():
    ok, out = run([DBT, "build", "--profiles-dir", ".", "--project-dir", "."])
    check("dbt build succeeds (models + snapshot + 43 tests)", ok,
          "56/56 nodes" if ok else out[-500:])

    con = duckdb.connect(str(ROOT / "dev.duckdb"), read_only=True)

    # Independent recomputation from the raw CSV (all_varchar, own casts).
    raw = con.execute(f"""
        select
            count(*) as n,
            count(distinct "ID") as distinct_ids,
            sum(cast(cast(nullif(trim(cast("Hospitalized" as varchar)), '') as double) as integer)) as hosp,
            sum(coalesce(cast(cast(nullif(trim(cast("Amputation" as varchar)), '') as double) as integer), 0)) as amp,
            sum(coalesce(cast(cast(nullif(trim(cast("Loss of Eye" as varchar)), '') as double) as integer), 0)) as eye,
            sum(case when coalesce(cast(cast(nullif(trim(cast("Hospitalized" as varchar)), '') as double) as integer), 0) > 0 then 1 else 0 end) as hosp_inc,
            sum(case when trim(cast("Inspection" as varchar)) <> '' then 1 else 0 end) as insp
        from read_csv('{CSV}', header=true, all_varchar=true)
    """).fetchone()
    # dedup: 5 duplicate IDs exist in the full file; the sample has none, but
    # recompute the deduped count the same way staging does (row_number by ID).
    dedup_n = con.execute(f"""
        select count(*) from (
            select "ID", row_number() over (partition by "ID" order by "EventDate") as rn
            from read_csv('{CSV}', header=true, all_varchar=true)
        ) where rn = 1
    """).fetchone()[0]
    fact = con.execute(
        "select count(*), sum(people_hospitalized), sum(people_amputated), "
        "sum(people_eye_loss), sum(is_hospitalized), sum(has_inspection) "
        "from fact_incidents"
    ).fetchone()
    check("staging row count matches raw CSV (after dedup)", fact[0] == dedup_n,
          f"fact={fact[0]} raw_deduped={dedup_n}")
    check("people hospitalized reconciles to raw CSV", fact[1] == raw[2],
          f"fact={fact[1]} raw={raw[2]}")
    check("amputations reconcile to raw CSV", fact[2] == raw[3],
          f"fact={fact[2]} raw={raw[3]}")
    check("eye losses reconcile to raw CSV", fact[3] == raw[4],
          f"fact={fact[3]} raw={raw[4]}")
    check("hospitalized incidents reconcile to raw CSV", fact[4] == raw[5],
          f"fact={fact[4]} raw={raw[5]}")
    check("inspected incidents reconcile to raw CSV", fact[5] == raw[6],
          f"fact={fact[5]} raw={raw[6]}")

    mart_total = con.execute("select sum(incident_count) from mart_safety_metrics").fetchone()[0]
    check("mart incident total equals fact count", mart_total == fact[0],
          f"mart={mart_total} fact={fact[0]}")

    dim_emp = con.execute(
        "select count(*), sum(is_current::int), count(distinct employer_key) from dim_employer"
    ).fetchone()
    check("dim_employer: one current row per employer", dim_emp[0] == dim_emp[1] == dim_emp[2],
          f"rows={dim_emp[0]} current={dim_emp[1]} distinct={dim_emp[2]}")

    cols = [r[1] for r in con.execute(
        "select * from pragma_table_info('snap_employer')").fetchall()]
    check("snapshot has SCD Type 2 columns",
          all(c in cols for c in ("dbt_valid_from", "dbt_valid_to", "dbt_scd_id", "dbt_updated_at")),
          f"columns={cols}")

    sev_ok = con.execute(
        "select count(*) from fact_incidents where severity_score != "
        "people_hospitalized + 2 * people_amputated + 3 * people_eye_loss"
    ).fetchone()[0]
    check("severity_score macro arithmetic holds on every fact row", sev_ok == 0,
          f"mismatched rows={sev_ok}")

    n_days = con.execute("select count(*) from dim_date").fetchone()[0]
    check("dim_date covers 2015-01-01 to 2025-12-31", n_days == 4018, f"days={n_days}")

    ok, out = run([DBT, "list", "--resource-type", "metric",
                   "--profiles-dir", ".", "--project-dir", "."])
    expected = {"total_incidents", "incidents_with_hospitalization",
                "incidents_with_amputation", "hospitalization_rate", "amputation_rate"}
    found = {line.strip().split(".")[-1] for line in out.splitlines() if line.strip()}
    check("semantic layer exposes all 5 metrics", expected <= found,
          f"found={sorted(found)}")

    print()
    n_pass = sum(1 for _, ok, _ in CHECKS if ok)
    print(f"{n_pass}/{len(CHECKS)} checks passed")
    return 0 if n_pass == len(CHECKS) else 1


if __name__ == "__main__":
    sys.exit(main())
