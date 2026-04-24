import frappe
import unittest


class TestInstall(unittest.TestCase):
    def test_ramz_hr_settings_single_exists(self):
        self.assertTrue(
            frappe.db.exists("DocType", "Ramz HR Settings"),
            "Ramz HR Settings DocType must exist after install",
        )
        self.assertEqual(
            frappe.get_meta("Ramz HR Settings").issingle, 1,
            "Ramz HR Settings must be a Single doctype",
        )

    def test_ramz_hr_settings_has_phase_1_fields(self):
        meta = frappe.get_meta("Ramz HR Settings")
        fieldnames = {df.fieldname for df in meta.fields}
        required = {
            "country",
            "auto_assign_leave_policy",
            "default_leave_policy",
            "fiscal_year_start_month",
            "casual_leave_days",
            "basic_salary_component",
            "basic_pct_min",
            "basic_pct_max",
            "basic_pct_strict",
            "iqama_reminder_days",
        }
        missing = required - fieldnames
        self.assertEqual(missing, set(), f"Missing fields on Ramz HR Settings: {missing}")
