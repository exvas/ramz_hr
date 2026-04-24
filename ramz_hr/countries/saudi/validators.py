"""Employee.validate handlers for Saudi Arabia.

Each function accepts the Employee doc and raises frappe.ValidationError on
failure. validate_employee() is the aggregator wired in hooks.py.

Nationality fieldname note: this site uses `custom_nationality` (added by
ksa_compliance or similar app) rather than a stock `nationality` field.
"""
from __future__ import annotations

import datetime
import re

import frappe

IQAMA_RE = re.compile(r"^\d{10}$")
IBAN_RE = re.compile(r"^SA\d{22}$")

MAX_PROBATION_DAYS = 180


def validate_employee(doc, method=None):
    """Wire point for doc_events.Employee.validate."""
    validate_iqama_format(doc)
    validate_iqama_expiry_presence(doc)
    validate_iban_format(doc)
    compute_probation_end_date(doc)


def validate_iqama_format(doc):
    iqama = (doc.get("custom_iqama_number") or "").strip()
    if not iqama:
        return
    if not IQAMA_RE.match(iqama):
        frappe.throw("Iqama / National ID must be exactly 10 digits.")


def validate_iqama_expiry_presence(doc):
    nationality = (doc.get("custom_nationality") or "").strip()
    if nationality and nationality != "Saudi Arabia":
        if not doc.get("custom_iqama_expiry"):
            frappe.throw("Iqama Expiry is required for non-Saudi employees.")


def validate_iban_format(doc):
    iban = (doc.get("custom_iban") or "").strip()
    if not iban:
        return
    if not IBAN_RE.match(iban):
        frappe.throw("IBAN must match 'SA' followed by exactly 22 digits.")


def compute_probation_end_date(doc):
    days = doc.get("custom_probation_period_days")
    doj = doc.get("date_of_joining")
    if days is None or doj is None:
        return
    days = int(days)
    if not (0 <= days <= MAX_PROBATION_DAYS):
        frappe.throw(f"Probation Period must be between 0 and {MAX_PROBATION_DAYS} days.")
    if isinstance(doj, str):
        doj = datetime.date.fromisoformat(doj)
    doc.custom_probation_end_date = doj + datetime.timedelta(days=days)
