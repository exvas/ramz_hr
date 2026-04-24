import frappe
import unittest

from ramz_hr.overrides.salary_structure_assignment import (
    compute_basic_percentage,
    validate_basic_percentage,
)


class _FakeAssignment:
    """Minimal Salary Structure Assignment stub for unit-testing the validator."""

    def __init__(self, salary_structure, base):
        self.salary_structure = salary_structure
        self.base = base
        self.employee = "TEST-EMP"

    def get(self, key, default=None):
        return getattr(self, key, default)


class TestBasicPercentage(unittest.TestCase):
    def test_compute_basic_pct_known_values(self):
        # Basic 5500 + Housing 2000 + Transport 500 = 8000; 5500/8000 = 68.75%
        pct = compute_basic_percentage(basic_amount=5500, gross=8000)
        self.assertAlmostEqual(pct, 68.75, places=2)

    def test_compute_basic_pct_zero_gross_is_zero(self):
        self.assertEqual(compute_basic_percentage(basic_amount=0, gross=0), 0.0)

    def test_validate_throws_when_above_max(self):
        _set_settings(basic_pct_min=50, basic_pct_max=70, basic_pct_strict=1, basic_salary_component="Basic")
        # 6000 basic / 8500 gross = 70.588% → throws
        with self.assertRaises(frappe.ValidationError):
            _run_validator_with_amounts(base=6000, other_earnings={"Housing Allowance": 2000, "Transportation Allowance": 500})

    def test_validate_passes_within_bounds(self):
        _set_settings(basic_pct_min=50, basic_pct_max=70, basic_pct_strict=1, basic_salary_component="Basic")
        _run_validator_with_amounts(base=5500, other_earnings={"Housing Allowance": 2000, "Transportation Allowance": 500})

    def test_validate_strict_off_only_warns(self):
        _set_settings(basic_pct_min=50, basic_pct_max=70, basic_pct_strict=0, basic_salary_component="Basic")
        # Must NOT raise:
        _run_validator_with_amounts(base=6000, other_earnings={"Housing Allowance": 2000, "Transportation Allowance": 500})


def _set_settings(**kwargs):
    """Write settings via frappe.db.set_single_value to avoid triggering the doctype
    validator (which itself enforces basic_pct_min < basic_pct_max)."""
    for k, v in kwargs.items():
        frappe.db.set_single_value("Ramz HR Settings", k, v)
    frappe.db.commit()


def _run_validator_with_amounts(base, other_earnings):
    """Exercise validate_basic_percentage against Ramz Saudi Standard."""
    doc = _FakeAssignment(salary_structure="Ramz Saudi Standard", base=base)
    ss = frappe.get_doc("Salary Structure", "Ramz Saudi Standard")
    for row in ss.earnings:
        row.amount = other_earnings.get(row.salary_component, 0)
    validate_basic_percentage(doc, salary_structure=ss)
