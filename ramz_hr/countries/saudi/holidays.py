"""Saudi Holiday List seeder.

Seeds one Holiday List per fiscal year ("Saudi Holidays <YYYY>") with:
  * Fixed Gregorian holidays (Founding Day, National Day)
  * Hijri-approximated placeholders for Eid Al-Fitr & Eid Al-Adha (admin
    must correct these after the Ministry of HR announces them)
  * Weekly off = Friday (HRMS supports only one weekly-off day on a Holiday
    List; Saturday must be added as a second holiday per week OR set via
    the Company's employment_type setting. For Phase 1 we use Friday only
    and let admin duplicate for Saturday if needed.)
"""
from __future__ import annotations

import datetime

import frappe

FIXED_HOLIDAYS: list[tuple[int, int, str]] = [
    # (month, day, description)
    (2, 22, "Saudi Founding Day"),
    (9, 23, "Saudi National Day"),
]

# Best-effort Hijri -> Gregorian mapping. Admin must verify against official
# Ministry announcements each year. Keys are the Gregorian year.
EID_AL_FITR_PLACEHOLDERS: dict[int, list[tuple[int, int]]] = {
    2026: [(3, 20), (3, 21), (3, 22)],
    2027: [(3, 10), (3, 11), (3, 12)],
    2028: [(2, 27), (2, 28), (2, 29)],
}
EID_AL_ADHA_PLACEHOLDERS: dict[int, list[tuple[int, int]]] = {
    2026: [(5, 26), (5, 27), (5, 28), (5, 29)],
    2027: [(5, 16), (5, 17), (5, 18), (5, 19)],
    2028: [(5, 4), (5, 5), (5, 6), (5, 7)],
}


def setup(year: int | None = None) -> str:
    year = year or datetime.date.today().year
    name = f"Saudi Holidays {year}"

    if frappe.db.exists("Holiday List", name):
        frappe.logger("ramz_hr").info(f"Holiday List '{name}' already exists; skipping.")
        return name

    hl = frappe.new_doc("Holiday List")
    hl.holiday_list_name = name
    hl.from_date = datetime.date(year, 1, 1)
    hl.to_date = datetime.date(year, 12, 31)
    hl.weekly_off = "Friday"

    for month, day, desc in FIXED_HOLIDAYS:
        hl.append("holidays", {
            "holiday_date": datetime.date(year, month, day),
            "description": desc,
        })

    for i, (month, day) in enumerate(EID_AL_FITR_PLACEHOLDERS.get(year, []), start=1):
        hl.append("holidays", {
            "holiday_date": datetime.date(year, month, day),
            "description": f"Eid Al-Fitr Day {i} (placeholder - verify with Ministry)",
        })
    for i, (month, day) in enumerate(EID_AL_ADHA_PLACEHOLDERS.get(year, []), start=1):
        hl.append("holidays", {
            "holiday_date": datetime.date(year, month, day),
            "description": f"Eid Al-Adha Day {i} (placeholder - verify with Ministry)",
        })

    # Auto-populate Friday weekly-offs
    hl.get_weekly_off_dates()
    hl.insert(ignore_permissions=True)

    if year not in EID_AL_FITR_PLACEHOLDERS:
        frappe.logger("ramz_hr").warning(
            f"No Eid placeholders defined for year {year}. "
            f"Admin must add Eid holidays manually to '{name}'."
        )

    # Add Saturdays as individual holidays (HRMS weekly_off is single-day only)
    d = datetime.date(year, 1, 1)
    one_day = datetime.timedelta(days=1)
    while d.year == year:
        if d.weekday() == 5:  # Saturday
            if not any(h.holiday_date == d for h in hl.holidays):
                hl.append("holidays", {
                    "holiday_date": d,
                    "description": "Weekly Off (Saturday)",
                    "weekly_off": 1,
                })
        d += one_day
    hl.save(ignore_permissions=True)
    frappe.db.commit()

    # Set as Company default if the Company has no default yet
    for company in frappe.get_all("Company", pluck="name"):
        existing = frappe.db.get_value("Company", company, "default_holiday_list")
        if not existing:
            frappe.db.set_value("Company", company, "default_holiday_list", name)

    return name
