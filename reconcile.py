#!/usr/bin/env python3
"""Reconcile payment attempts and print the application code.

Run from any directory with:
    python3 reconcile.py
"""
import json
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent


def parse_timestamp(value):
    """Parse an ISO-8601 timestamp, including the provider's trailing Z."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_amount(value):
    """Convert numeric or comma-formatted amounts to an exact Decimal."""
    return Decimal(str(value).replace(",", "").strip())


def reconcile():
    # Keep only the latest event for each transaction ID.
    latest_by_txn = {}

    with (DATA_DIR / "payments.jsonl").open(encoding="utf-8") as payments:
        for line in payments:
            try:
                event = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                # The provider export can contain malformed JSON lines.
                continue

            txn_id = event.get("txn_id")
            if not txn_id:
                continue

            # Every event with a transaction ID is valid per the README.
            timestamp = parse_timestamp(event["ts"])
            previous = latest_by_txn.get(txn_id)

            # On equal timestamps, keep the later line in the export.
            if previous is None or timestamp >= previous[0]:
                latest_by_txn[txn_id] = (timestamp, event)

    total = Decimal("0")
    count = 0

    for _, event in latest_by_txn.values():
        if event["status"] == "success":
            total += parse_amount(event["amount"])
            count += 1

    with (DATA_DIR / "expected.txt").open(encoding="utf-8") as expected_file:
        expected = int(expected_file.read().strip())

    if count != expected:
        print(
            f"Check failed: counted {count} successful payments, "
            f"expected {expected}."
        )
        print("Something in the data isn't being handled the way the README describes.")
        return

    rounded_total = total.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    print(f"Check passed: {count} successful payments.")
    print(f"Your code: KOYA-{rounded_total}")


if __name__ == "__main__":
    reconcile()
