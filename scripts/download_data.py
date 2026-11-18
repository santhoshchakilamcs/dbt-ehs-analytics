#!/usr/bin/env python3
"""Download the OSHA Severe Injury Reports (SIR) dataset and sample it.

Source: U.S. Occupational Safety and Health Administration (OSHA),
Severe Injury Reports, employer-reported amputations, in-patient
hospitalizations, and eye losses, Jan 1, 2015 - Nov 30, 2025.
Download page: https://www.osha.gov/severe-injury-reports
Direct file: https://www.osha.gov/sites/default/files/January2015toNovember2025.zip
Full file: 105,996 records, ~57 MB uncompressed. This script keeps a
deterministic stratified sample (1,500 rows, seed 42, proportional by
event year) so the repo stays small and `dbt build` runs anywhere.
The sample preserves the full 2015-2025 year coverage and includes
employers with more than one NAICS code, which is what the SCD Type 2
snapshot demonstrates on.

osha.gov blocks plain HTTP clients, so the request carries a browser
User-Agent. If the download is ever blocked, fetch the same ZIP from
the Severe Injury Dashboard in a browser and place the extracted CSV
at data/raw/osha_sir_full.csv, then re-run this script with --local.
"""
import argparse
import csv
import io
import random
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

ZIP_URL = "https://www.osha.gov/sites/default/files/January2015toNovember2025.zip"
ZIP_NAME = "January2015toNovember2025.csv"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
SAMPLE_N = 1500
SEED = 42


def load_rows(local_csv=None):
    if local_csv:
        with open(local_csv, newline="", encoding="utf-8", errors="replace") as f:
            return list(csv.DictReader(f))
    req = urllib.request.Request(ZIP_URL, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        with z.open(ZIP_NAME) as f:
            text = io.TextIOWrapper(f, encoding="utf-8", errors="replace")
            return list(csv.DictReader(text))


def stratified_sample(rows, n=SAMPLE_N, seed=SEED):
    rng = random.Random(seed)
    by_year = {}
    for row in rows:
        year = (row.get("EventDate") or "")[-4:]
        by_year.setdefault(year, []).append(row)
    total = len(rows)
    sample = []
    for year, group in sorted(by_year.items()):
        k = max(1, round(n * len(group) / total))
        sample.extend(rng.sample(group, min(k, len(group))))
    # trim or top up to exactly n while keeping year coverage
    rng.shuffle(sample)
    if len(sample) > n:
        sample = sample[:n]
    while len(sample) < n:
        extra = rng.choice(rows)
        if extra not in sample:
            sample.append(extra)
    sample.sort(key=lambda r: (r.get("EventDate") or "", r.get("ID") or ""))
    return sample


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", help="path to an already-downloaded full SIR CSV")
    ap.add_argument("--out", default="data/raw/osha_sir.csv")
    args = ap.parse_args()
    rows = load_rows(args.local)
    print(f"full file: {len(rows)} records")
    sample = stratified_sample(rows)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(sample)
    years = Counter((r.get("EventDate") or "")[-4:] for r in sample)
    print(f"sample: {len(sample)} rows -> {out} ({out.stat().st_size} bytes)")
    print("years in sample:", dict(sorted(years.items())))


if __name__ == "__main__":
    main()
