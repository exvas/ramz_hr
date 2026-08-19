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
    currency = frappe.db.get_default("currency") or "SAR"

    if frappe.db.exists("Salary Structure", STRUCTURE_NAME):
        ss = frappe.get_doc("Salary Structure", STRUCTURE_NAME)
    else:
        ss = frappe.new_doc("Salary Structure")
        ss.salary_structure_name = STRUCTURE_NAME
        ss.name = STRUCTURE_NAME

    ss.is_active = "Yes"
    ss.payroll_frequency = "Monthly"
    ss.currency = currency

    # Rebuild the component tables so re-running always converges to DESIRED_*.
    ss.set("earnings", [])
    ss.set("deductions", [])
    for row in DESIRED_EARNINGS:
        ss.append("earnings", _struct_row(row))
    for row in DESIRED_DEDUCTIONS:
        ss.append("deductions", _struct_row(row))

    ss.flags.ignore_mandatory = True
    ss.flags.ignore_permissions = True
    ss.save() if not ss.is_new() else ss.insert(ignore_permissions=True)

    # Some HRMS versions reset is_active on save of a formula-only structure.
    if frappe.db.get_value("Salary Structure", STRUCTURE_NAME, "is_active") != "Yes":
        frappe.db.set_value("Salary Structure", STRUCTURE_NAME, "is_active", "Yes")


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
