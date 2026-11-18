# dbt-ehs-analytics

A dbt project that models OSHA Severe Injury Reports into a Kimball
star schema with data-quality tests, an SCD Type 2 employer snapshot,
reusable macros, and a dbt Semantic Layer — on real public safety data.

Built as a personal project to cover the dbt gap in a Data Engineer
(EHS&S) role: hands-on dbt in production means models, tests, macros,
snapshots, and documentation, plus dimensional modeling (Kimball, SCDs,
metric/semantic layer), data-quality tests, and KPI governance. Every
number below was verified by an independent recomputation
(`verify_results.py`, 13/13) and a pytest suite (`tests/`, 7/7).

## Data

**Source:** U.S. Occupational Safety and Health Administration (OSHA),
Severe Injury Reports — employer-reported amputations, in-patient
hospitalizations, and eye losses, Jan 1, 2015 – Nov 30, 2025.
Download page: https://www.osha.gov/severe-injury-reports
(direct file `January2015toNovember2025.zip`, 105,996 records).

**Committed sample:** `data/raw/osha_sir.csv` — 1,500 rows, a deterministic
stratified sample (seed 42, proportional by event year) of the full file,
so the repo stays small and `dbt build` runs anywhere. All 11 years
(2015–2025) are covered. `scripts/download_data.py` reproduces the sample
from the official ZIP (run it with `--local <full csv>` if you already
downloaded the file in a browser).

## Architecture

```
data/raw/osha_sir.csv                  (OSHA SIR sample, 1,500 rows)
        |
        v
stg_osha_sir                           staging: typed, cleaned, deduplicated
        |                                (5 duplicate report IDs exist in the
        v                                 full file; staging keeps one per ID)
int_sir_clean                          intermediate: employer keys, flags,
        |                               severity score, NAICS sector
        +---> int_employer_attributes  one row per employer (latest incident)
        |                               |
        v                               v
fact_incidents                snap_employer (check strategy on NAICS/address)
dim_date · dim_event ·              |
dim_nature · dim_source ·           v
dim_body_part             dim_employer (SCD Type 2, from the snapshot)
        |
        v
mart_safety_metrics                    monthly KPIs by state + NAICS sector
        |
        v
Semantic Layer                         semantic model `incidents` + 5 metrics
```

## Models

| Layer | Models |
|---|---|
| Staging | `stg_osha_sir` (view): renames, type-casts, dedupes on report ID |
| Intermediate | `int_sir_clean` (view): surrogate employer key, hospitalization/amputation/eye-loss flags, severity score, NAICS sector; `int_employer_attributes` (view): one row per employer, latest-incident attributes |
| Marts | `fact_incidents` (table, grain = one report); `dim_employer` (table, SCD Type 2); `dim_date` (table, 2015-01-01–2025-12-31, 4,018 days); `dim_event`, `dim_nature`, `dim_source`, `dim_body_part` (tables, OIICS codes + titles); `mart_safety_metrics` (table, monthly KPIs) |
| Semantic | `metricflow_time_spine` (table, day grain); semantic model `incidents` with 6 measures and 4 dimensions; metrics `total_incidents`, `incidents_with_hospitalization`, `incidents_with_amputation`, `hospitalization_rate`, `amputation_rate` |

## Macros

- `severity_score(hospitalized, amputation, eye_loss)` — one comparable
  number per incident: hospitalized + 2×amputated + 3×eye loss.
- `naics_sector(naics_code)` — 2-digit NAICS code to sector name.
- `generate_schema_name` — single-schema layout for DuckDB.

## Snapshot (SCD Type 2)

`snap_employer` tracks employer attributes with a **check strategy** on
`naics_code, address1, city, state, zip_code`. When an employer's NAICS or
address changes across incidents, the old version is expired
(`dbt_valid_to` set) and a new current version opens. The pytest suite
proves this end to end with 4 real later incidents from the official file
(`tests/fixtures_sir_incremental.csv`): Resers Fine Foods (Topeka, KS)
changes NAICS 311999 → 311991 and Knife River Corporation South (Bryan,
TX) changes address/NAICS — both get a second version, and the
`assert_snapshot_one_current_row_per_employer` test still passes.

## Tests

43 dbt tests (schema: unique / not_null / relationships / accepted
values; singular: no duplicate report IDs, event dates in range, fact
reconciles to staging, counts non-negative, one current snapshot row per
employer) plus 7 pytest tests. `dbt build`: **56/56 pass**.

## Verified numbers (1,500-row sample)

| Measure | Value |
|---|---|
| Incidents | 1,500 |
| Employers | 1,496 |
| People hospitalized | 1,225 (1,216 incidents, **81.1%**) |
| Amputations | 396 people (26.4% of incidents) |
| Eye losses | 0 in the sample (35 in the full file) |
| Incidents followed by an OSHA inspection | 507 (**33.8%**) |
| Mean severity score | 1.345 |
| Top sectors | Manufacturing 506, Construction 288, Transportation and Warehousing 131 |

## KPI definitions (`mart_safety_metrics`)

- `hospitalization_rate` = incidents with ≥1 person hospitalized ÷ incidents
- `amputation_rate` = incidents with ≥1 amputation ÷ incidents
- `eye_loss_rate` = incidents with ≥1 eye loss ÷ incidents
- `inspection_rate` = incidents followed by an OSHA inspection ÷ incidents
- `repeat_employer_incidents` = incidents at employers that reported more
  than one incident in the same month
- `avg_severity_score` = mean severity score for the month

The same five metrics are defined once in the dbt Semantic Layer
(`models/metrics/_semantic_models.yml`) so dashboards and ad-hoc queries
compute them identically — that is the KPI-governance point.

## How to run

```bash
python3 -m venv .venv && .venv/bin/pip install dbt-duckdb pytest
.venv/bin/dbt build --profiles-dir . --project-dir .   # models + snapshot + tests
.venv/bin/python verify_results.py                     # independent recomputation
.venv/bin/python -m pytest tests/ -q                  # 7 tests incl. SCD2 demo
.venv/bin/dbt docs generate --profiles-dir . --project-dir .  # docs site
```

DuckDB is the warehouse (no cloud credentials needed); the same models
run on Snowflake/BigQuery by swapping the profile. Requires Python 3.11+.

## Honest limits

- The repo commits a 1,500-row sample, not the full 105,996-record file;
  rerun `scripts/download_data.py` for the full data (the models are
  unchanged — only the CSV grows).
- No Power BI semantic model is built here; the dbt Semantic Layer is the
  governed metric layer, and `mart_safety_metrics` is the table a BI tool
  would read. No dbt Cloud / Snowflake / BigQuery run — DuckDB locally.
- The incident narratives are kept as text for future classification work;
  no LLM incident classifier is built in this repo (classification
  modeling lives in my dispute-case-analytics project).
- Employer identity is name + city + state, not a stable employer ID —
  the official file has no persistent employer identifier, so two sites
  of one company with different names stay separate employers.
