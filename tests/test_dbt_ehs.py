"""Tests for dbt-ehs-analytics.

Run: .venv/bin/python -m pytest tests/ -q
The snapshot-change test runs in an isolated copy of the project so the
real dev.duckdb and sample CSV are never touched.
"""
import csv
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parent.parent
DBT = str(ROOT / ".venv" / "bin" / "dbt")
CSV = ROOT / "data" / "raw" / "osha_sir.csv"
FIXTURE = ROOT / "tests" / "fixtures_sir_incremental.csv"


def dbt(*args, cwd=ROOT):
    r = subprocess.run([DBT, *args, "--profiles-dir", ".", "--project-dir", "."],
                       cwd=cwd, capture_output=True, text=True)
    return r


def test_sample_csv_schema_and_coverage():
    rows = list(csv.DictReader(open(CSV, newline="", encoding="utf-8")))
    assert len(rows) == 1500
    assert list(rows[0].keys())[:6] == ["ID", "UPA", "EventDate", "Employer", "Address1", "Address2"]
    years = {r["EventDate"][-4:] for r in rows}
    assert years == {str(y) for y in range(2015, 2026)}, f"missing years: {years}"
    assert len({r["ID"] for r in rows}) == 1500, "sample must have unique report IDs"


def test_sampling_is_deterministic():
    sys.path.insert(0, str(ROOT / "scripts"))
    import download_data
    rows = list(csv.DictReader(open(CSV, newline="", encoding="utf-8")))
    a = [r["ID"] for r in download_data.stratified_sample(rows, n=200)]
    b = [r["ID"] for r in download_data.stratified_sample(rows, n=200)]
    assert a == b


def test_dbt_build_passes():
    r = dbt("build")
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]


def test_kpi_recomputation_matches_raw_csv():
    con = duckdb.connect(str(ROOT / "dev.duckdb"), read_only=True)
    fact = con.execute(
        "select count(*), sum(people_hospitalized), sum(is_hospitalized), "
        "sum(has_inspection) from fact_incidents").fetchone()
    raw = con.execute(f"""
        select count(*),
            sum(coalesce(cast(cast(nullif(trim(cast("Hospitalized" as varchar)), '') as double) as integer), 0)),
            sum(case when coalesce(cast(cast(nullif(trim(cast("Hospitalized" as varchar)), '') as double) as integer), 0) > 0 then 1 else 0 end),
            sum(case when trim(cast("Inspection" as varchar)) <> '' then 1 else 0 end)
        from read_csv('{CSV}', header=true, all_varchar=true)
    """).fetchone()
    assert fact == raw


def test_snapshot_captures_attribute_change():
    """End-to-end SCD Type 2: appending real later incidents whose employer
    attributes changed must expire the old version and open a new one."""
    tmp = Path(tempfile.mkdtemp(prefix="dbt_ehs_test_"))
    try:
        shutil.copytree(ROOT, tmp / "proj", ignore=shutil.ignore_patterns(
            ".venv", "target", "dev.duckdb", "__pycache__", ".pytest_cache",
            ".git", "dev.duckdb.wal"))
        proj = tmp / "proj"
        os.symlink(ROOT / ".venv", proj / ".venv")
        r = dbt("build", cwd=proj)
        assert r.returncode == 0, r.stdout[-1500:]

        # Append the 4 real fixture rows (later incidents, changed NAICS/address).
        sample_rows = list(csv.DictReader(open(proj / "data" / "raw" / "osha_sir.csv",
                                               newline="", encoding="utf-8")))
        fixture_rows = list(csv.DictReader(open(FIXTURE, newline="", encoding="utf-8")))
        assert len(fixture_rows) == 4
        with open(proj / "data" / "raw" / "osha_sir.csv", "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(sample_rows[0].keys()))
            w.writerows(fixture_rows)

        r = dbt("run", "--select", "stg_osha_sir", "int_sir_clean",
                "int_employer_attributes", cwd=proj)
        assert r.returncode == 0, r.stdout[-1500:]
        r = dbt("snapshot", "--select", "snap_employer", cwd=proj)
        assert r.returncode == 0, r.stdout[-1500:]

        con = duckdb.connect(str(proj / "dev.duckdb"), read_only=True)
        # Employer names change case across incidents, so match on the
        # surrogate key, not the name string.
        for employer, new_naics in (("resers fine foods|topeka|KANSAS", "311991"),
                                    ("knife river corporation south|bryan|TEXAS", "212321")):
            key = hashlib.md5(employer.encode()).hexdigest()
            versions = con.execute(
                "select naics_code, dbt_valid_to is null as is_current "
                "from snap_employer where employer_key = ? order by dbt_valid_from",
                [key]).fetchall()
            assert len(versions) == 2, f"{employer}: {versions}"
            assert versions[0][1] is False, "old version must be expired"
            assert versions[1] == (new_naics, True), f"new version wrong: {versions}"
        con.close()  # release the DuckDB lock before dbt test re-opens the file
        r = dbt("test", "--select", "assert_snapshot_one_current_row_per_employer", cwd=proj)
        assert r.returncode == 0, r.stdout[-1500:]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_semantic_layer_metrics_listed():
    r = dbt("list", "--resource-type", "metric")
    assert r.returncode == 0
    names = {line.strip().split(".")[-1] for line in r.stdout.splitlines() if line.strip()}
    assert {"total_incidents", "hospitalization_rate", "amputation_rate"} <= names


def test_docs_generate():
    r = dbt("docs", "generate")
    assert r.returncode == 0, r.stdout[-1500:]
    assert (ROOT / "target" / "catalog.json").exists()
