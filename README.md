# Vendor Invoice & Material Receipt Processor

A Python automation pipeline that validates vendor invoice and material receipt
submissions, flags anomalies, and produces a structured CSV audit log.

Originally built as a **Power Automate cloud flow** (Microsoft Forms trigger →
validation conditions → SharePoint log). This Python implementation reproduces
the same pipeline so it can run anywhere — locally, in a container, or on a
schedule via cron or Airflow.

---

## What it does

```
Form submission (JSON)
        │
        ▼
┌───────────────────┐
│  Load submissions │  ← reads from JSON file (or swap in an API call)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Validate each    │  ← required fields, amount range, date, currency
└────────┬──────────┘
         │
         ├──► approved   all rules pass
         ├──► flagged    soft issue (high amount, unsupported currency, future date)
         └──► rejected   hard failure (missing field, zero amount, bad data)
         │
         ▼
┌───────────────────┐
│  Write CSV log    │  ← data/processed_YYYYMMDD.csv
└───────────────────┘
```

---

## Validation rules

| Rule | Threshold | Status if triggered |
|---|---|---|
| Required fields present | vendor name, invoice number, date, amount, description | rejected |
| Amount in range | €0.01 – €50,000 | flagged (above) / rejected (zero/negative) |
| Invoice date not in future | today's date | flagged |
| Currency supported | EUR, USD, GBP | flagged |

---

## Quick start

```bash
# Clone and run (Python 3.10+ required, no third-party packages needed)
git clone https://github.com/mansipurohit11/vendor-invoice-automation
cd vendor-invoice-automation

# Process the included sample data
python invoice_processor.py

# Dry-run (validate only, no file written)
python invoice_processor.py --dry-run

# Custom input file
python invoice_processor.py --input my_submissions.json --output results/out.csv
```

---

## Sample output

```
2024-10-26 11:00:01  INFO      Loading submissions from data/sample_submissions.json
2024-10-26 11:00:01  INFO      Loaded 5 submissions
2024-10-26 11:00:01  INFO      ──────────────────────────────────────────────────
2024-10-26 11:00:01  INFO      SUMMARY  total=5  approved=2  flagged=2  rejected=1
2024-10-26 11:00:01  INFO      ──────────────────────────────────────────────────
2024-10-26 11:00:01  INFO      Items requiring attention:
2024-10-26 11:00:01  INFO        [FLAGGED]  SUB-002 | FastParts Ltd   | AMOUNT_EXCEEDS_THRESHOLD:62000.00
2024-10-26 11:00:01  INFO        [FLAGGED]  SUB-004 | Global Tech AG  | INVOICE_DATE_FUTURE; UNSUPPORTED_CURRENCY:USD
2024-10-26 11:00:01  INFO        [REJECTED] SUB-003 |                 | MISSING_FIELD:vendor_name
2024-10-26 11:00:01  INFO      Results written → data/processed_20241026.csv
```

---

## Run tests

```bash
pip install pytest
pytest test_invoice_processor.py -v
```

---

## Extending this pipeline

- **Swap the data source**: replace `load_submissions()` with a call to the
  Microsoft Forms API, a SharePoint list, or any REST endpoint.
- **Add notification**: send flagged items to a Slack webhook or email via
  `smtplib` — same pattern as the Power Automate email action.
- **Schedule it**: drop `invoice_processor.py` into an Airflow DAG or a
  GitHub Actions cron workflow for fully automated daily runs.

---

## Skills demonstrated

`Python` · `data validation` · `ETL pipelines` · `automation` · `CSV/JSON` ·
`unit testing (pytest)` · `argparse` · `logging` · `dataclasses`
