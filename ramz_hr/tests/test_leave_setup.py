import datetime

import frappe
import unittest


EXPECTED_LEAVE_TYPES = [
    "Annual Leave",
    "Casual Leave",
    "Sick Leave - Full Pay",
    "Sick Leave - 75%",
    "Sick Leave - Unpaid",
    "Marriage Leave",
    "Paternity Leave",
    "Maternity Leave",
    "Bereavement Leave",
    "Hajj Leave",
    "Unpaid Leave",
]


class TestLeaveSetup(unittest.TestCase):
    def test_all_11_leave_types_exist(self):
        missing = [lt for lt in EXPECTED_LEAVE_TYPES if not frappe.db.exists("Leave Type", lt)]
        self.assertEqual(missing, [], f"Leave Types missing: {missing}")

    def test_annual_leave_is_carry_forward_and_earned(self):
        lt = frappe.get_doc("Leave Type", "Annual Leave")
        self.assertEqual(lt.is_carry_forward, 1)
        self.assertEqual(lt.max_carry_forwarded_leaves, 21)
        self.assertEqual(lt.is_earned_leave, 1)
        self.assertEqual(lt.earned_leave_frequency, "Monthly")

    def test_sick_leave_75_is_partially_paid(self):
        lt = frappe.get_doc("Leave Type", "Sick Leave - 75%")
        self.assertEqual(lt.is_ppl, 1)
        self.assertAlmostEqual(float(lt.fraction_of_daily_salary_per_leave), 0.75, places=2)

    def test_sick_leave_unpaid_is_lwp(self):
        lt = frappe.get_doc("Leave Type", "Sick Leave - Unpaid")
        self.assertEqual(lt.is_lwp, 1)

    def test_paternity_leave_male_only(self):
        lt = frappe.get_doc("Leave Type", "Paternity Leave")
        self.assertEqual(lt.applicable_for_gender, "Male")

    def test_maternity_leave_female_only(self):
        lt = frappe.get_doc("Leave Type", "Maternity Leave")
        self.assertEqual(lt.applicable_for_gender, "Female")

    def test_ramz_saudi_standard_policy_exists(self):
        self.assertTrue(frappe.db.exists("Leave Policy", "Ramz Saudi Standard"))
        policy = frappe.get_doc("Leave Policy", "Ramz Saudi Standard")
        totals = {d.leave_type: d.annual_allocation for d in policy.leave_policy_details}
        self.assertEqual(totals.get("Annual Leave"), 21)
        self.assertEqual(totals.get("Hajj Leave"), 15)
        self.assertEqual(totals.get("Maternity Leave"), 70)

    def test_leave_period_seeded_for_current_year(self):
        year = datetime.date.today().year
        self.assertTrue(frappe.db.exists("Leave Period", f"Saudi {year}"))

    def test_unpaid_leave_not_in_policy(self):
        policy = frappe.get_doc("Leave Policy", "Ramz Saudi Standard")
        types = {d.leave_type for d in policy.leave_policy_details}
        self.assertNotIn("Unpaid Leave", types)


class TestAutoAssignLeavePolicy(unittest.TestCase):
    def setUp(self):
        frappe.db.set_single_value("Ramz HR Settings", "auto_assign_leave_policy", 1)

    def tearDown(self):
        frappe.db.rollback()

    def _make_employee(self, **overrides):
        company = frappe.get_all("Company", limit=1, pluck="name")[0]
        payload = {
            "doctype": "Employee",
            "employee_name": "Test Saudi Employee",
            "first_name": "Test",
            "last_name": "SaudiEmp",
            "gender": "Male",
            "date_of_birth": "1990-01-01",
            "date_of_joining": datetime.date.today().replace(month=1, day=1),
            "company": company,
            "custom_nationality": "Saudi Arabia",
            "status": "Active",
        }
        payload.update(overrides)
        return frappe.get_doc(payload).insert(ignore_permissions=True)

    def test_new_employee_gets_leave_policy_assignment(self):
        emp = self._make_employee()
        assignments = frappe.get_all(
            "Leave Policy Assignment",
            filters={"employee": emp.name, "docstatus": 1},
            fields=["leave_policy"],
        )
        self.assertTrue(assignments, "New employee should have a Leave Policy Assignment")
        self.assertEqual(assignments[0].leave_policy, "Ramz Saudi Standard")

    def test_toggle_off_skips_assignment(self):
        frappe.db.set_single_value("Ramz HR Settings", "auto_assign_leave_policy", 0)
        emp = self._make_employee()
        assignments = frappe.get_all(
            "Leave Policy Assignment",
            filters={"employee": emp.name},
        )
        self.assertEqual(assignments, [])
