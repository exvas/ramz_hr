"""Saudi-specific Custom Fields + Property Setters for stock doctypes.

Design note: fields are grouped by visual section for the Employee form.
Fieldname prefix is `custom_` per Frappe convention; underscores in labels
are translated to spaces by Frappe's UI automatically.
"""
from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


CUSTOM_FIELDS: dict[str, list[dict]] = {
    "Employee": [
        # ---- Saudi Employment Details section ----
        {
            "fieldname": "custom_saudi_employment_details_section",
            "fieldtype": "Section Break",
            "label": "Saudi Employment Details",
            "insert_after": "department",
            "collapsible": 1,
        },
        {
            "fieldname": "custom_iqama_number",
            "fieldtype": "Data",
            "label": "Iqama / National ID",
            "insert_after": "custom_saudi_employment_details_section",
            "description": "10 digits. Iqama for expats, National ID for Saudi nationals.",
        },
        {
            "fieldname": "custom_iqama_expiry",
            "fieldtype": "Date",
            "label": "Iqama Expiry",
            "insert_after": "custom_iqama_number",
            "description": "Mandatory for non-Saudi nationals.",
        },
        {
            "fieldname": "custom_contract_type",
            "fieldtype": "Select",
            "label": "Contract Type",
            "options": "\nLimited\nUnlimited",
            "insert_after": "custom_iqama_expiry",
            "description": "Saudi Labor Law contract type (used by EOSB formula).",
        },
        {
            "fieldname": "custom_employment_column_break",
            "fieldtype": "Column Break",
            "insert_after": "custom_contract_type",
        },
        {
            "fieldname": "custom_work_location",
            "fieldtype": "Data",
            "label": "Work Location",
            "insert_after": "custom_employment_column_break",
        },
        {
            "fieldname": "custom_probation_period_days",
            "fieldtype": "Int",
            "label": "Probation Period (Days)",
            "default": "90",
            "insert_after": "custom_work_location",
            "description": "Saudi Labor Law max 180 days.",
        },
        {
            "fieldname": "custom_probation_end_date",
            "fieldtype": "Date",
            "label": "Probation End Date",
            "read_only": 1,
            "insert_after": "custom_probation_period_days",
            "description": "Auto-computed from Date of Joining + Probation Period.",
        },
        # ---- Benefits & Entitlements section ----
        {
            "fieldname": "custom_benefits_section",
            "fieldtype": "Section Break",
            "label": "Benefits & Entitlements",
            "insert_after": "custom_probation_end_date",
            "collapsible": 1,
        },
        {
            "fieldname": "custom_air_ticket_eligibility",
            "fieldtype": "Select",
            "label": "Air Ticket Eligibility",
            "options": "\nNone\nAnnual\nBiennial",
            "insert_after": "custom_benefits_section",
        },
        {
            "fieldname": "custom_benefits_column_break",
            "fieldtype": "Column Break",
            "insert_after": "custom_air_ticket_eligibility",
        },
        {
            "fieldname": "custom_medical_insurance_class",
            "fieldtype": "Link",
            "label": "Medical Insurance Class",
            "options": "Medical Insurance Class",
            "insert_after": "custom_benefits_column_break",
        },
        # ---- Saudi Payroll Info section ----
        {
            "fieldname": "custom_saudi_payroll_section",
            "fieldtype": "Section Break",
            "label": "Saudi Payroll Info",
            "insert_after": "custom_medical_insurance_class",
            "collapsible": 1,
        },
        {
            "fieldname": "custom_iban",
            "fieldtype": "Data",
            "label": "IBAN",
            "insert_after": "custom_saudi_payroll_section",
            "description": "Saudi IBAN: 'SA' + 22 digits.",
        },
    ],
    # Per-employee salary amounts for the single "Ramz Saudi Standard" structure.
    # The structure's component formulas read these fields at salary-slip time
    # (Basic comes from the native `base` field). See countries/saudi/salary_components.py.
    "Salary Structure Assignment": [
        {
            "fieldname": "custom_ramz_components_section",
            "fieldtype": "Section Break",
            "label": "Ramz Salary Components",
            "insert_after": "base",
        },
        {
            "fieldname": "custom_housing",
            "fieldtype": "Currency",
            "label": "Housing Allowance",
            "insert_after": "custom_ramz_components_section",
            "description": "Monthly Housing amount for this employee.",
        },
        {
            "fieldname": "custom_transportation",
            "fieldtype": "Currency",
            "label": "Transportation Allowance",
            "insert_after": "custom_housing",
        },
        {
            "fieldname": "custom_column_break_ramz",
            "fieldtype": "Column Break",
            "insert_after": "custom_transportation",
        },
        {
            "fieldname": "custom_other_allowance",
            "fieldtype": "Currency",
            "label": "Other Allowance",
            "insert_after": "custom_column_break_ramz",
        },
        {
            "fieldname": "custom_other_deduction",
            "fieldtype": "Currency",
            "label": "Other Deduction",
            "insert_after": "custom_other_allowance",
        },
    ],
}


# [doctype, fieldname, property, property_type, value]
# Note: this ERPNext install uses `custom_nationality` (custom field) rather
# than a stock `nationality` docfield, so we target that.
PROPERTY_SETTERS: list[tuple[str, str, str, str, str]] = [
    ("Employee", "custom_nationality", "reqd", "Check", "1"),
    ("Employee", "date_of_joining", "reqd", "Check", "1"),
    ("Salary Structure Assignment", "base", "reqd", "Check", "1"),
]


# (doctype, fieldname) pairs to remove on migrate if no FK references exist.
DEPRECATED_FIELDS: list[tuple[str, str]] = []


def setup() -> None:
    create_custom_fields(CUSTOM_FIELDS, update=True)
    for dt, fn, prop, ptype, value in PROPERTY_SETTERS:
        make_property_setter(dt, fn, prop, value, ptype, validate_fields_for_doctype=False)
    _remove_deprecated()
    frappe.db.commit()


def _remove_deprecated() -> None:
    for dt, fn in DEPRECATED_FIELDS:
        cf = frappe.db.get_value("Custom Field", {"dt": dt, "fieldname": fn})
        if cf:
            # Only delete if no records use the field (safe check).
            refs = frappe.db.sql(f"SELECT COUNT(*) FROM `tab{dt}` WHERE `{fn}` IS NOT NULL AND `{fn}` != ''")
            if refs and refs[0][0] == 0:
                frappe.delete_doc("Custom Field", cf, ignore_permissions=True, force=True)
