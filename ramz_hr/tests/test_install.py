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

    def test_saudi_holiday_list_seeded(self):
        import datetime

        year = datetime.date.today().year
        name = f"Saudi Holidays {year}"
        self.assertTrue(
            frappe.db.exists("Holiday List", name),
            f"Holiday List '{name}' must be seeded on install",
        )
        hl = frappe.get_doc("Holiday List", name)

        descriptions = {h.description for h in hl.holidays}
        for must_have in ["Saudi Founding Day", "Saudi National Day"]:
            self.assertTrue(
                any(must_have in d for d in descriptions),
                f"Holiday list must include {must_have}",
            )
        self.assertEqual(hl.weekly_off, "Friday", "Weekly off should be Friday (week-end 1)")

    def test_saudi_salary_components_seeded(self):
        for name in ["Basic", "Housing Allowance", "Transportation Allowance"]:
            self.assertTrue(
                frappe.db.exists("Salary Component", name),
                f"Salary Component '{name}' must exist",
            )
        for name, expected_type in [("Basic", "Earning"), ("Housing Allowance", "Earning"), ("Transportation Allowance", "Earning")]:
            actual = frappe.db.get_value("Salary Component", name, "type")
            self.assertEqual(actual, expected_type)

    def test_ramz_saudi_standard_structure_seeded(self):
        self.assertTrue(
            frappe.db.exists("Salary Structure", "Ramz Saudi Standard"),
            "Salary Structure 'Ramz Saudi Standard' must be seeded",
        )
        s = frappe.get_doc("Salary Structure", "Ramz Saudi Standard")
        self.assertEqual(s.is_active, "Yes")
        earnings = {row.salary_component for row in s.earnings}
        self.assertEqual(earnings, {"Basic", "Housing Allowance", "Transportation Allowance"})
