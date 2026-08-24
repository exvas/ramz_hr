"""Saudi Salary Components + the single dynamic Salary Structure.

Design (per Ramz payroll spec):
  * ONE Salary Structure, "Ramz Saudi Standard", shared by every own employee.
  * Per-employee amounts are NOT stored on the structure. They are entered on
    each Salary Structure Assignment via custom fields (see
    countries/saudi/custom_fields.py):
        base                       -> Basic
        custom_housing             -> Housing Allowance
        custom_transportation      -> Transportation Allowance
        custom_other_allowance     -> Other Allowance
        custom_other_deduction     -> Other Deduction
  * The structure component formulas reference those SSA fields. HRMS merges the
    whole SSA doc AND the Employee doc into the formula-eval context
    (salary_slip.get_data_for_eval -> data.update(_salary_structure_assignment);
    data.update(employee)), so `base`, `custom_*` and `custom_nationality` are
    all resolvable inside the formulas.
  * GOSI is Saudi-nationals-only and computed as (Basic + Housing) * 9.75%,
    matching the client sheet's documented "SUM(BASIC+HOUSING)*9.75%" formula.
  * Overtime / Standby / Food / Site allowances and timesheet-based absences are
    NOT part of the structure — they are posted per-month via Additional Salary.

Idempotent: safe to re-run on every migrate; the structure's earnings/deductions
are rebuilt to match DESIRED_* each time.
"""
from __future__ import annotations

import frappe

STRUCTURE_NAME = "Ramz Saudi Standard"

# GOSI employee contribution rate for Saudi nationals.
GOSI_RATE = 0.0975

# Master Salary Components (created if missing; existing ones left untouched).
COMPONENTS: list[dict] = [
    {"salary_component": "Basic", "salary_component_abbr": "BASIC", "type": "Earning", "depends_on_payment_days": 1, "is_tax_applicable": 0},
    {"salary_component": "Housing Allowance", "salary_component_abbr": "HRA", "type": "Earning", "depends_on_payment_days": 1, "is_tax_applicable": 0},
    {"salary_component": "Transportation Allowance", "salary_component_abbr": "TA", "type": "Earning", "depends_on_payment_days": 1, "is_tax_applicable": 0},
    {"salary_component": "Other Allowance", "salary_component_abbr": "OA", "type": "Earning", "depends_on_payment_days": 1, "is_tax_applicable": 0},
    {"salary_component": "GOSI", "salary_component_abbr": "GOSI", "type": "Deduction", "depends_on_payment_days": 0},
    {"salary_component": "Other Deduction", "salary_component_abbr": "OD", "type": "Deduction", "depends_on_payment_days": 0},
]

# Structure earning rows. `formula` is evaluated against the SSA + Employee data.
DESIRED_EARNINGS: list[dict] = [
    {"salary_component": "Basic", "abbr": "BASIC", "formula": "base", "depends_on_payment_days": 1},
    {"salary_component": "Housing Allowance", "abbr": "HRA", "formula": "custom_housing", "depends_on_payment_days": 1},
    {"salary_component": "Transportation Allowance", "abbr": "TA", "formula": "custom_transportation", "depends_on_payment_days": 1},
    {"salary_component": "Other Allowance", "abbr": "OA", "formula": "custom_other_allowance", "depends_on_payment_days": 1},
]

# Structure deduction rows.
DESIRED_DEDUCTIONS: list[dict] = [
    {
        "salary_component": "GOSI",
        "abbr": "GOSI",
        # Saudi nationals only; matches the client sheet "(BASIC+HOUSING)*9.75%".
        "condition": "custom_nationality == 'Saudi Arabia'",
        "formula": f"(base + custom_housing) * {GOSI_RATE}",
        "depends_on_payment_days": 0,
    },
    {"salary_component": "Other Deduction", "abbr": "OD", "formula": "custom_other_deduction", "depends_on_payment_days": 0},
]


def setup() -> None:
    _ensure_components()
    _upsert_structure()
    _configure_calendar_day_payroll()
    frappe.db.commit()


def _configure_calendar_day_payroll() -> None:
    """Ramz runs payroll on a calendar-day basis: the month denominator is the
    calendar days in the period (30/31), not only the working days. Enabling
    Payroll Settings.include_holidays_in_total_working_days makes HRMS set
    total_working_days = calendar days, so payment_days / absence proration is
    on /30 (/31), matching the client's "MONTH DAYS = 30" sheet."""
    if not frappe.db.get_single_value("Payroll Settings", "include_holidays_in_total_working_days"):
        frappe.db.set_single_value("Payroll Settings", "include_holidays_in_total_working_days", 1)


def _ensure_components() -> None:
    for comp in COMPONENTS:
        if frappe.db.exists("Salary Component", comp["salary_component"]):
            continue
        frappe.get_doc({"doctype": "Salary Component", **comp}).insert(ignore_permissions=True)


def _upsert_structure() -> None:
    """Create the structure on a fresh site; converge an existing DRAFT one to
    DESIRED_*. Idempotent and submit-safe.

    Salary Structure is submittable, and it must be submitted before any Salary
    Structure Assignment can reference it. Once submitted its child rows cannot
    be cleared/re-appended and saved (that raises "Salary Detail <x> not found"),
    so after_migrate must NEVER mutate+save a submitted structure. We therefore
    no-op when the config already matches, and skip (with a warning) if it is
    submitted but differs — rather than crash the whole migrate.
    """
    currency = frappe.db.get_default("currency") or "SAR"

    if not frappe.db.exists("Salary Structure", STRUCTURE_NAME):
        ss = frappe.new_doc("Salary Structure")
        ss.salary_structure_name = STRUCTURE_NAME
        ss.name = STRUCTURE_NAME
        ss.is_active = "Yes"
        ss.payroll_frequency = "Monthly"
        ss.currency = currency
        for row in DESIRED_EARNINGS:
            ss.append("earnings", _struct_row(row))
        for row in DESIRED_DEDUCTIONS:
            ss.append("deductions", _struct_row(row))
        ss.flags.ignore_mandatory = True
        ss.insert(ignore_permissions=True)
        _ensure_active()
        return

    ss = frappe.get_doc("Salary Structure", STRUCTURE_NAME)

    if _structure_matches_desired(ss):
        _ensure_active()  # cheap raw-write, safe on submitted docs
        return

    if ss.docstatus == 1:
        frappe.logger("ramz_hr").warning(
            f"Salary Structure {STRUCTURE_NAME!r} is submitted and differs from the "
            "desired ramz_hr config; skipping auto-update. Amend it manually if a "
            "component change is required."
        )
        _ensure_active()
        return

    # Draft and differs — safe to rebuild + save.
    ss.is_active = "Yes"
    ss.payroll_frequency = "Monthly"
    ss.currency = currency
    ss.set("earnings", [])
    ss.set("deductions", [])
    for row in DESIRED_EARNINGS:
        ss.append("earnings", _struct_row(row))
    for row in DESIRED_DEDUCTIONS:
        ss.append("deductions", _struct_row(row))
    ss.flags.ignore_mandatory = True
    ss.flags.ignore_permissions = True
    ss.save()
    _ensure_active()


def _ensure_active() -> None:
    """Raw DB write (docstatus-agnostic) so is_active stays 'Yes' without a save."""
    if frappe.db.get_value("Salary Structure", STRUCTURE_NAME, "is_active") != "Yes":
        frappe.db.set_value("Salary Structure", STRUCTURE_NAME, "is_active", "Yes")


def _structure_matches_desired(ss) -> bool:
    """True when the structure's earnings + deductions already match DESIRED_*
    (component, formula, condition, payment-days, formula-flag). Comparison is
    order-independent and keyed by salary_component."""

    def rows_match(actual_rows, desired_rows) -> bool:
        if len(actual_rows) != len(desired_rows):
            return False
        by_comp = {r.salary_component: r for r in actual_rows}
        for d in desired_rows:
            r = by_comp.get(d["salary_component"])
            if r is None:
                return False
            if (r.formula or "").strip() != d["formula"].strip():
                return False
            if int(r.amount_based_on_formula or 0) != 1:
                return False
            if int(r.depends_on_payment_days or 0) != int(d.get("depends_on_payment_days", 0)):
                return False
            if (r.condition or "").strip() != (d.get("condition") or "").strip():
                return False
        return True

    return rows_match(ss.earnings, DESIRED_EARNINGS) and rows_match(ss.deductions, DESIRED_DEDUCTIONS)


def _struct_row(row: dict) -> dict:
    out = {
        "salary_component": row["salary_component"],
        "abbr": row["abbr"],
        "amount_based_on_formula": 1,
        "formula": row["formula"],
        "depends_on_payment_days": row.get("depends_on_payment_days", 0),
    }
    if row.get("condition"):
        out["condition"] = row["condition"]
    return out
