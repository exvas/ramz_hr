"""App-level install orchestrator for ramz_hr.

after_install and after_migrate run the same idempotent sequence:
  1. Seed Ramz HR Settings Single doctype defaults.
  2. Sync country-neutral custom fields & property setters (empty in Phase 1).
  3. Dispatch to the active country module's setup().
"""
from __future__ import annotations

import frappe

from ramz_hr.countries import get_active_country_module


DEFAULT_SETTINGS = {
    "country": "Saudi Arabia",
    "auto_assign_leave_policy": 1,
    "fiscal_year_start_month": 1,
    "casual_leave_days": 7,
    "basic_pct_min": 50,
    "basic_pct_max": 70,
    "basic_pct_strict": 1,
    "iqama_reminder_days": 30,
}


def after_install() -> None:
    _run_sequence()


def after_migrate() -> None:
    _run_sequence()


def _run_sequence() -> None:
    _seed_settings_defaults()
    # Phase 1 has no country-neutral custom fields — placeholder for later.
    _sync_country_neutral_schema()
    _dispatch_country_setup()
    frappe.db.commit()


def _seed_settings_defaults() -> None:
    if not frappe.db.exists("DocType", "Ramz HR Settings"):
        return  # doctype hasn't migrated yet — install.py was called before doctype migrate
    settings = frappe.get_single("Ramz HR Settings")
    changed = False
    for key, value in DEFAULT_SETTINGS.items():
        if not settings.get(key):
            settings.set(key, value)
            changed = True
    if changed:
        settings.save(ignore_permissions=True)


def _sync_country_neutral_schema() -> None:
    # Reserved for future country-neutral custom fields / property setters.
    pass


def _dispatch_country_setup() -> None:
    if not frappe.db.exists("DocType", "Ramz HR Settings"):
        return
    country_module = get_active_country_module()
    country_module.setup()
