"""
Vendor Invoice & Material Receipt Processor
============================================
Polls a form submission endpoint for new vendor invoice / material receipt
entries, validates each submission against configurable business rules,
and writes structured results to a CSV log with status flags.

Originally automated in Power Automate (Microsoft Forms + cloud flow).
This Python implementation reproduces the same pipeline so it can run
anywhere — locally, in a container, or on a schedule via cron / Airflow.

Usage:
    python invoice_processor.py                  # process all pending
    python invoice_processor.py --dry-run        # validate only, no output
    python invoice_processor.py --input sample_submissions.json
"""

import argparse
import csv
import json
import logging
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
REQUIRED_FIELDS = ["vendor_name", "invoice_number", "invoice_date", "amount_eur", "material_description"]
AMOUNT_MAX = 50_000.00          # flag for manual review above this threshold
AMOUNT_MIN = 0.01
VALID_CURRENCIES = {"EUR", "USD", "GBP"}
OUTPUT_DIR = Path("data")
OUTPUT_FILE = OUTPUT_DIR / f"processed_{datetime.now().strftime('%Y%m%d')}.csv"


# ── Data model ────────────────────────────────────────────────────────────────
@dataclass
class InvoiceSubmission:
    submission_id: str
    vendor_name: str
    invoice_number: str
    invoice_date: str
    amount_eur: float
    currency: str
    material_description: str
    submitter_email: str = ""
    notes: str = ""


@dataclass
class ValidationResult:
    submission_id: str
    vendor_name: str
    invoice_number: str
    invoice_date: str
    amount_eur: float
    material_description: str
    status: str = "pending"          # pending | approved | flagged | rejected
    flags: list = field(default_factory=list)
    processed_at: str = ""


# ── Validation rules ──────────────────────────────────────────────────────────
def validate(submission: InvoiceSubmission) -> ValidationResult:
    """
    Apply business rules and return a ValidationResult with status and flags.
    Rules mirror what the original Power Automate cloud flow checked:
      - All required fields present and non-empty
      - Amount within acceptable range
      - Invoice date not in the future
      - Currency in approved list
    """
    flags = []

    # 1. Required fields
    raw = asdict(submission)
    for f_name in REQUIRED_FIELDS:
        if not str(raw.get(f_name, "")).strip():
            flags.append(f"MISSING_FIELD:{f_name}")

    # 2. Amount range
    try:
        amount = float(submission.amount_eur)
        if amount < AMOUNT_MIN:
            flags.append("AMOUNT_NEGATIVE_OR_ZERO")
        if amount > AMOUNT_MAX:
            flags.append(f"AMOUNT_EXCEEDS_THRESHOLD:{amount:.2f}")
    except (ValueError, TypeError):
        flags.append("AMOUNT_NOT_NUMERIC")

    # 3. Date not in future
    try:
        inv_date = datetime.strptime(submission.invoice_date, "%Y-%m-%d")
        if inv_date.date() > datetime.today().date():
            flags.append("INVOICE_DATE_FUTURE")
    except ValueError:
        flags.append("INVOICE_DATE_INVALID_FORMAT")

    # 4. Currency
    if submission.currency.upper() not in VALID_CURRENCIES:
        flags.append(f"UNSUPPORTED_CURRENCY:{submission.currency}")

    # Decide status
    hard_failures = [f for f in flags if f.startswith("MISSING") or "NEGATIVE" in f or "NOT_NUMERIC" in f]
    if hard_failures:
        status = "rejected"
    elif flags:
        status = "flagged"          # needs manual review
    else:
        status = "approved"

    return ValidationResult(
        submission_id=submission.submission_id,
        vendor_name=submission.vendor_name,
        invoice_number=submission.invoice_number,
        invoice_date=submission.invoice_date,
        amount_eur=submission.amount_eur,
        material_description=submission.material_description,
        status=status,
        flags=flags,
        processed_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


# ── I/O helpers ───────────────────────────────────────────────────────────────
def load_submissions(path: str) -> list[InvoiceSubmission]:
    """Load submissions from a local JSON file (replaces the Forms API call)."""
    with open(path) as f:
        raw = json.load(f)

    submissions = []
    for item in raw:
        try:
            submissions.append(InvoiceSubmission(**item))
        except TypeError as e:
            log.warning("Skipping malformed entry %s: %s", item.get("submission_id", "?"), e)
    return submissions


def write_results(results: list[ValidationResult], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "submission_id", "vendor_name", "invoice_number", "invoice_date",
        "amount_eur", "material_description", "status", "flags", "processed_at",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            row = asdict(r)
            row["flags"] = "; ".join(r.flags) if r.flags else ""
            writer.writerow(row)
    log.info("Results written → %s", output_path)


def print_summary(results: list[ValidationResult]) -> None:
    counts = {"approved": 0, "flagged": 0, "rejected": 0, "pending": 0}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1

    log.info("─" * 50)
    log.info("SUMMARY  total=%d  approved=%d  flagged=%d  rejected=%d",
             len(results), counts["approved"], counts["flagged"], counts["rejected"])
    log.info("─" * 50)

    if counts["flagged"] or counts["rejected"]:
        log.info("Items requiring attention:")
        for r in results:
            if r.status in ("flagged", "rejected"):
                log.info("  [%s] %s | %s | %s",
                         r.status.upper(), r.submission_id, r.vendor_name,
                         "; ".join(r.flags))


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Vendor Invoice Processor")
    parser.add_argument("--input", default="data/sample_submissions.json",
                        help="Path to JSON file with form submissions")
    parser.add_argument("--output", default=str(OUTPUT_FILE),
                        help="Path for the output CSV")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate and print summary without writing output")
    args = parser.parse_args()

    log.info("Loading submissions from %s", args.input)
    submissions = load_submissions(args.input)
    log.info("Loaded %d submissions", len(submissions))

    results = [validate(s) for s in submissions]

    print_summary(results)

    if not args.dry_run:
        write_results(results, Path(args.output))
    else:
        log.info("Dry-run mode — no file written.")


if __name__ == "__main__":
    main()
