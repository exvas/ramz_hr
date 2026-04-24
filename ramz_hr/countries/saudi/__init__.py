"""Saudi Arabia country module for ramz_hr.

Exposes a single setup() entry point that install.py calls. setup() is
idempotent: running it twice is safe and never overwrites admin-modified
records. It composes the 5 sub-setups; each sub-module keeps its logic
isolated for clarity and future country parity.
"""
from __future__ import annotations

import frappe


def setup() -> None:
    """Run all Saudi seeders in dependency order."""
    from ramz_hr.countries.saudi import (
        custom_fields,
        medical_insurance_class,
        holidays,
        salary_components,
        leave_types,
    )

    # Order matters:
    #   1. Lookup doctypes first (Medical Insurance Class) so fields can Link to them.
    #   2. Custom fields on Employee (requires Medical Insurance Class to exist for the Link field).
    #   3. Holiday list (independent).
    #   4. Salary components + structure (independent).
    #   5. Leave types + policy + period (depends on nothing above, but seeded last to keep logical groupings adjacent).

    medical_insurance_class.setup()
    custom_fields.setup()
    holidays.setup()
    salary_components.setup()
    leave_types.setup()

    frappe.logger("ramz_hr").info("Saudi module setup complete")
