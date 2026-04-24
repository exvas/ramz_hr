"""Country-module dispatcher for ramz_hr.

Each country's rules (custom fields, holidays, leave types, salary components,
lookup data) live in a dedicated sub-module. The active country is read from
Ramz HR Settings.country at install/migrate time; install.py calls the
returned module's setup() function.

To add a new country:
    1. Create ramz_hr/countries/<slug>/ with an __init__.py exposing setup()
    2. Register it below in COUNTRY_REGISTRY
    3. On the target site, set Ramz HR Settings.country = "<Country Name>"
"""
from __future__ import annotations

import importlib

import frappe

COUNTRY_REGISTRY: dict[str, str] = {
    "Saudi Arabia": "ramz_hr.countries.saudi",
    # "United Arab Emirates": "ramz_hr.countries.uae",
    # "Qatar":                "ramz_hr.countries.qatar",
    # "India":                "ramz_hr.countries.india",
}


def get_active_country_module():
    country = frappe.db.get_single_value("Ramz HR Settings", "country") or "Saudi Arabia"
    if country not in COUNTRY_REGISTRY:
        frappe.throw(
            f"Country '{country}' is not implemented in ramz_hr yet. "
            f"Supported: {sorted(COUNTRY_REGISTRY)}"
        )
    return importlib.import_module(COUNTRY_REGISTRY[country])
