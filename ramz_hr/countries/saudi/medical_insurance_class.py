from __future__ import annotations

import frappe

SEED_CLASSES: list[tuple[str, str]] = [
    ("VIP", "Top-tier medical coverage, private hospitals"),
    ("A+", "Premium coverage"),
    ("A", "Standard coverage"),
    ("B", "Basic coverage"),
    ("C", "Entry-level coverage"),
]


def setup() -> None:
    for name, description in SEED_CLASSES:
        if frappe.db.exists("Medical Insurance Class", name):
            # Patch blank description only — never overwrite admin-set value.
            current = frappe.db.get_value("Medical Insurance Class", name, "description")
            if not current and description:
                frappe.db.set_value("Medical Insurance Class", name, "description", description)
            continue

        doc = frappe.get_doc(
            {
                "doctype": "Medical Insurance Class",
                "class_name": name,
                "description": description,
            }
        )
        doc.insert(ignore_permissions=True)
    frappe.db.commit()
