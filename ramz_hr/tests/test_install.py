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

    def test_medical_insurance_class_doctype_exists(self):
        self.assertTrue(
            frappe.db.exists("DocType", "Medical Insurance Class"),
            "Medical Insurance Class DocType must exist after install",
        )
        self.assertFalse(
            frappe.get_meta("Medical Insurance Class").issingle,
            "Medical Insurance Class must not be a single doctype",
        )

    def test_medical_insurance_class_autoname(self):
        meta = frappe.get_meta("Medical Insurance Class")
        self.assertEqual(
            meta.autoname, "field:class_name",
            "Medical Insurance Class must autoname from class_name",
        )

    def test_medical_insurance_classes_seeded(self):
        expected = {"VIP", "A+", "A", "B", "C"}
        existing = set(frappe.get_all("Medical Insurance Class", pluck="name"))
        missing = expected - existing
        self.assertEqual(missing, set(), f"Seeded Medical Insurance Classes missing: {missing}")

    def test_employee_saudi_custom_fields(self):
        meta = frappe.get_meta("Employee")
        fieldnames = {df.fieldname for df in meta.fields}
        required = {
            "custom_saudi_employment_details_section",
            "custom_iqama_number",
            "custom_iqama_expiry",
            "custom_contract_type",
            "custom_work_location",
            "custom_probation_period_days",
            "custom_probation_end_date",
            "custom_benefits_section",
            "custom_air_ticket_eligibility",
            "custom_medical_insurance_class",
            "custom_saudi_payroll_section",
            "custom_iban",
        }
        missing = required - fieldnames
        self.assertEqual(missing, set(), f"Employee missing Saudi fields: {missing}")

    def test_employee_nationality_required(self):
        # This ERPNext install uses `custom_nationality` rather than stock `nationality`.
        meta = frappe.get_meta("Employee")
        nat = next(
            (df for df in meta.fields if df.fieldname in ("nationality", "custom_nationality")),
            None,
        )
        self.assertIsNotNone(nat, "Employee must expose a nationality field (stock or custom)")
        self.assertEqual(nat.reqd, 1, "Employee nationality must be required by property setter")
