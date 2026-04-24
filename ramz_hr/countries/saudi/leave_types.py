"""Saudi Leave Types + Leave Policy + Leave Period seeder.

Sick leave is split into 3 tiers (Full / 75% / Unpaid) to model the PDF's
30/60/30 progression using stock HRMS fields without custom payroll logic.
"""
from __future__ import annotations

import datetime

import frappe

POLICY_NAME = "Ramz Saudi Standard"

# Base definition + allocation used by the Leave Policy.
LEAVE_TYPES: list[dict] = [
    {
        "leave_type_name": "Annual Leave",
        "max_leaves_allowed": 21,
        "is_carry_forward": 1,
        "max_carry_forwarded_leaves": 21,
        "is_lwp": 0,
        "is_ppl": 0,
        "allow_encashment": 1,
        "is_earned_leave": 1,
        "earned_leave_frequency": "Monthly",
        "annual_allocation": 21,
    },
    {
        "leave_type_name": "Casual Leave",
        "max_leaves_allowed": 7,
        "is_carry_forward": 0,
        "is_lwp": 0,
        "is_ppl": 0,
        "annual_allocation": 7,
    },
    {
        "leave_type_name": "Sick Leave - Full Pay",
        "max_leaves_allowed": 30,
        "is_carry_forward": 0,
        "is_lwp": 0,
        "is_ppl": 0,
        "annual_allocation": 30,
    },
    {
        "leave_type_name": "Sick Leave - 75%",
        "max_leaves_allowed": 60,
        "is_carry_forward": 0,
        "is_lwp": 0,
        "is_ppl": 1,
        "fraction_of_daily_salary_per_leave": 0.75,
        "annual_allocation": 60,
    },
    {
        "leave_type_name": "Sick Leave - Unpaid",
        "max_leaves_allowed": 30,
        "is_carry_forward": 0,
        "is_lwp": 1,
        "is_ppl": 0,
        "annual_allocation": 30,
    },
    {
        "leave_type_name": "Marriage Leave",
        "max_leaves_allowed": 5,
        "is_carry_forward": 0,
        "is_lwp": 0,
        "is_ppl": 0,
        "annual_allocation": 5,
    },
    {
        "leave_type_name": "Paternity Leave",
        "max_leaves_allowed": 3,
        "is_carry_forward": 0,
        "is_lwp": 0,
        "is_ppl": 0,
        "applicable_for_gender": "Male",
        "annual_allocation": 3,
    },
    {
        "leave_type_name": "Maternity Leave",
        "max_leaves_allowed": 70,
        "is_carry_forward": 0,
        "is_lwp": 0,
        "is_ppl": 0,
        "applicable_for_gender": "Female",
        "annual_allocation": 70,
    },
    {
        "leave_type_name": "Bereavement Leave",
        "max_leaves_allowed": 5,
        "is_carry_forward": 0,
        "is_lwp": 0,
        "is_ppl": 0,
        "annual_allocation": 5,
    },
    {
        "leave_type_name": "Hajj Leave",
        "max_leaves_allowed": 15,
        "is_carry_forward": 0,
        "is_lwp": 0,
        "is_ppl": 0,
        "annual_allocation": 15,
    },
    {
        "leave_type_name": "Unpaid Leave",
        "max_leaves_allowed": 0,
        "is_carry_forward": 0,
        "is_lwp": 1,
        "is_ppl": 0,
        "annual_allocation": None,  # not in Leave Policy
    },
]


def setup() -> None:
    _ensure_custom_fields()
    for lt in LEAVE_TYPES:
        _ensure_leave_type(lt)
    _ensure_leave_policy()
    _ensure_leave_period()
    _seed_default_policy_in_settings()
    frappe.db.commit()


def _ensure_custom_fields() -> None:
    """Add Saudi-specific custom fields to Leave Type that stock HRMS lacks.

    - applicable_for_gender: restrict leave to Male/Female (Paternity/Maternity).
    - max_carry_forwarded_leaves: alias of maximum_carry_forwarded_leaves for
      stable API naming (stock HRMS renamed the field across versions).
    """
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    custom_fields = {
        "Leave Type": [
            {
                "fieldname": "applicable_for_gender",
                "label": "Applicable For Gender",
                "fieldtype": "Select",
                "options": "\nMale\nFemale\nOther",
                "insert_after": "leave_type_name",
            },
            {
                "fieldname": "max_carry_forwarded_leaves",
                "label": "Max Carry Forwarded Leaves",
                "fieldtype": "Int",
                "insert_after": "maximum_carry_forwarded_leaves",
                "description": "Alias of maximum_carry_forwarded_leaves for stable API.",
            },
        ]
    }
    create_custom_fields(custom_fields, update=True)


def _ensure_leave_type(spec: dict) -> None:
    name = spec["leave_type_name"]
    payload = {k: v for k, v in spec.items() if k != "annual_allocation"}
    if frappe.db.exists("Leave Type", name):
        # Idempotent update: ensure custom fields (applicable_for_gender,
        # max_carry_forwarded_leaves) populate on previously-created rows
        # where they may have been silently dropped.
        doc = frappe.get_doc("Leave Type", name)
        dirty = False
        for key, value in payload.items():
            if getattr(doc, key, None) != value:
                try:
                    setattr(doc, key, value)
                    dirty = True
                except AttributeError:
                    # Field may not exist on this HRMS version; skip.
                    pass
        if dirty:
            doc.save(ignore_permissions=True)
        return
    payload["doctype"] = "Leave Type"
    frappe.get_doc(payload).insert(ignore_permissions=True)


def _ensure_leave_policy() -> None:
    if frappe.db.exists("Leave Policy", POLICY_NAME):
        return
    policy = frappe.new_doc("Leave Policy")
    policy.title = POLICY_NAME
    for lt in LEAVE_TYPES:
        if lt["annual_allocation"] is None:
            continue
        policy.append("leave_policy_details", {
            "leave_type": lt["leave_type_name"],
            "annual_allocation": lt["annual_allocation"],
        })
    # Force .name == POLICY_NAME
    policy.name = POLICY_NAME
    policy.flags.name_set = True
    policy.insert(ignore_permissions=True)


def _ensure_leave_period() -> None:
    settings = frappe.get_single("Ramz HR Settings")
    start_month = int(settings.fiscal_year_start_month or 1)
    year = datetime.date.today().year
    name = f"Saudi {year}"
    if frappe.db.exists("Leave Period", name):
        return
    from_date = datetime.date(year, start_month, 1)
    # end on last day of month 12 months later (same date next year minus 1 day)
    to_year = year + 1 if start_month > 1 else year
    to_month = start_month - 1 if start_month > 1 else 12
    # last day of to_month
    if to_month == 12:
        to_date = datetime.date(to_year, 12, 31)
    else:
        to_date = datetime.date(to_year, to_month + 1, 1) - datetime.timedelta(days=1)

    period = frappe.new_doc("Leave Period")
    period.name = name
    period.from_date = from_date
    period.to_date = to_date
    period.is_active = 1
    period.flags.name_set = True
    period.insert(ignore_permissions=True)


def _seed_default_policy_in_settings() -> None:
    current = frappe.db.get_single_value("Ramz HR Settings", "default_leave_policy")
    if not current and frappe.db.exists("Leave Policy", POLICY_NAME):
        # Use db.set_single_value to avoid triggering the full Ramz HR Settings
        # validate hook (which requires basic_pct_min/max to be populated).
        frappe.db.set_single_value("Ramz HR Settings", "default_leave_policy", POLICY_NAME)


def auto_assign_leave_policy(doc, method=None):
    """doc_events handler wired on Employee.after_insert."""
    settings = frappe.get_single("Ramz HR Settings")
    if not settings.auto_assign_leave_policy:
        return
    policy_name = settings.default_leave_policy or POLICY_NAME
    if not frappe.db.exists("Leave Policy", policy_name):
        return
    year = datetime.date.today().year
    period_name = f"Saudi {year}"
    if not frappe.db.exists("Leave Period", period_name):
        return

    assignment = frappe.new_doc("Leave Policy Assignment")
    assignment.employee = doc.name
    assignment.assignment_based_on = "Leave Period"
    assignment.leave_policy = policy_name
    assignment.leave_period = period_name
    assignment.effective_from = doc.get("date_of_joining") or datetime.date(year, 1, 1)
    assignment.insert(ignore_permissions=True)
    assignment.submit()
