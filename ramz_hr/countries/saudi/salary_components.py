"""Saudi Salary Components + base Salary Structure seeder."""
from __future__ import annotations

import frappe

COMPONENTS: list[dict] = [
    {
        "salary_component": "Basic",
        "salary_component_abbr": "BASIC",
        "type": "Earning",
        "depends_on_payment_days": 1,
        "is_tax_applicable": 0,
    },
    {
        "salary_component": "Housing Allowance",
        "salary_component_abbr": "HRA",
        "type": "Earning",
        "depends_on_payment_days": 1,
        "is_tax_applicable": 0,
    },
    {
        "salary_component": "Transportation Allowance",
        "salary_component_abbr": "TA",
        "type": "Earning",
        "depends_on_payment_days": 1,
        "is_tax_applicable": 0,
    },
]

STRUCTURE_NAME = "Ramz Saudi Standard"


def setup() -> None:
    for comp in COMPONENTS:
        name = comp["salary_component"]
        if frappe.db.exists("Salary Component", name):
            continue
        doc = frappe.get_doc({
            "doctype": "Salary Component",
            **comp,
        })
        doc.insert(ignore_permissions=True)

    if not frappe.db.exists("Salary Structure", STRUCTURE_NAME):
        ss = frappe.new_doc("Salary Structure")
        ss.salary_structure_name = STRUCTURE_NAME
        ss.name = STRUCTURE_NAME
        ss.is_active = "Yes"
        ss.payroll_frequency = "Monthly"
        ss.currency = frappe.db.get_default("currency") or "SAR"
        for comp in COMPONENTS:
            ss.append("earnings", {
                "salary_component": comp["salary_component"],
                "abbr": comp["salary_component_abbr"],
                "amount_based_on_formula": 0,
            })
        ss.flags.ignore_mandatory = True
        ss.insert(ignore_permissions=True)

        # Ensure is_active persisted as "Yes" (some HRMS versions reset it)
        if frappe.db.get_value("Salary Structure", STRUCTURE_NAME, "is_active") != "Yes":
            frappe.db.set_value("Salary Structure", STRUCTURE_NAME, "is_active", "Yes")

    # Seed Ramz HR Settings.basic_salary_component if blank
    settings = frappe.get_single("Ramz HR Settings")
    if not settings.basic_salary_component:
        settings.basic_salary_component = "Basic"
        settings.save(ignore_permissions=True)

    frappe.db.commit()
