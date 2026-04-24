"""Salary Structure Assignment validator: enforce Basic % is within
Ramz HR Settings bounds (default 50-70%).

Wired via doc_events.Salary Structure Assignment.validate in hooks.py.
"""
from __future__ import annotations

import frappe


def compute_basic_percentage(basic_amount: float, gross: float) -> float:
    if not gross:
        return 0.0
    return float(basic_amount) / float(gross) * 100.0


def validate_basic_percentage(doc, method=None, salary_structure=None):
    settings = frappe.get_single("Ramz HR Settings")
    basic_component = settings.basic_salary_component or "Basic"
    pct_min = float(settings.basic_pct_min or 50)
    pct_max = float(settings.basic_pct_max or 70)
    strict = bool(settings.basic_pct_strict)

    base = float(doc.get("base") or 0)
    if base <= 0:
        return  # validator only fires when base is set; base.reqd is enforced by property setter

    ss = salary_structure or frappe.get_doc("Salary Structure", doc.get("salary_structure"))
    earning_amounts = {}
    for row in ss.earnings:
        comp = row.salary_component
        if comp == basic_component:
            earning_amounts[comp] = base
        else:
            earning_amounts[comp] = float(row.amount or 0)

    gross = sum(earning_amounts.values())
    if basic_component not in earning_amounts:
        # Structure doesn't include the basic component — skip silently
        return
    basic_amount = earning_amounts[basic_component]
    pct = compute_basic_percentage(basic_amount, gross)

    if pct_min <= pct <= pct_max:
        return

    msg = (
        f"Basic must be between {pct_min:.0f}% and {pct_max:.0f}% of gross "
        f"(currently {pct:.2f}%). "
        f"Basic={basic_amount:,.2f}, Gross={gross:,.2f}."
    )
    if strict:
        frappe.throw(msg)
    else:
        frappe.msgprint(msg, alert=True, indicator="orange")
