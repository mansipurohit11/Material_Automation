# 🧾 vendor invoice processor

because manually checking 50 invoice submissions in a spreadsheet is not going to cut it anymore.

---

## what this does

someone submits a vendor invoice or material receipt via a form. this pipeline picks it up, runs it through a set of validation rules, and tells you whether it's good to go, needs a second look, or should be thrown back.

```
form submission (json)
        │
        ▼
┌─────────────────────┐
│  load submissions   │  reads from json (swap in any api call you like)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  validate each one  │  required fields, amount range, date sanity, currency
└──────────┬──────────┘
           │
           ├──► ✅ approved    everything checks out
           ├──► ⚠️  flagged    something's off — human should look
           └──► ❌ rejected    hard failure — missing data or clearly wrong
           │
           ▼
┌─────────────────────┐
│  write csv audit log│  data/processed_YYYYMMDD.csv
└─────────────────────┘
```

---

## validation rules

| rule | detail | outcome |
|---|---|---|
| required fields | vendor name, invoice number, date, amount, description | ❌ rejected if missing |
| amount range | must be between €0.01 and €50,000 | ⚠️ flagged if over / ❌ rejected if zero |
| invoice date | can't be in the future (yes, this has happened) | ⚠️ flagged |
| currency | EUR, USD, GBP only | ⚠️ flagged otherwise |

---

## quick start

```bash
git clone https://github.com/mansipurohit11/vendor-invoice-automation
cd vendor-invoice-automation

# no pip install needed — pure standard library
python invoice_processor.py

# just validate, don't write anything
python invoice_processor.py --dry-run

# custom input/output
python invoice_processor.py --input my_data.json --output results/out.csv
```

requires python 3.10+. that's it.

---

## what the output looks like

```
2024-10-26 11:00:01  INFO      loaded 5 submissions
2024-10-26 11:00:01  INFO      ──────────────────────────────────────────────────
2024-10-26 11:00:01  INFO      SUMMARY  total=5  approved=2  flagged=2  rejected=1
2024-10-26 11:00:01  INFO      ──────────────────────────────────────────────────
2024-10-26 11:00:01  INFO      items requiring attention:
2024-10-26 11:00:01  INFO        [FLAGGED]  SUB-002 | FastParts Ltd  | AMOUNT_EXCEEDS_THRESHOLD:62000.00
2024-10-26 11:00:01  INFO        [FLAGGED]  SUB-004 | Global Tech AG | INVOICE_DATE_FUTURE; UNSUPPORTED_CURRENCY:USD
2024-10-26 11:00:01  INFO        [REJECTED] SUB-003 |               | MISSING_FIELD:vendor_name
```

---

## run the tests

```bash
pip install pytest
pytest test_invoice_processor.py -v
```

8 tests. all pass. (please tell me if they don't.)

---

## extending it

this was originally a **power automate cloud flow** (microsoft forms → validation conditions → sharepoint log). the logic is the same, just in python now so it can run anywhere.

some things you could swap in without much effort:

- **different data source** — replace `load_submissions()` with a real api call, a database query, or a sharepoint connector
- **notifications** — send flagged items to slack or email with a few extra lines
- **scheduling** — drop it into an airflow dag or a github actions cron job and forget about it

---

## what i learned

- validating data is 80% of the actual work. the "automation" part is easy once the rules are clear.
- zero-amount invoices are more common than you'd expect.
- writing tests first makes the validation logic much cleaner.

---

## stack

`python 3.10+` · `csv` · `json` · `dataclasses` · `argparse` · `logging` · `pytest`

no third-party packages required for the main script. refreshing.
