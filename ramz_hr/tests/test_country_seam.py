import frappe
import unittest
from unittest.mock import patch

from ramz_hr.countries import COUNTRY_REGISTRY, get_active_country_module


class TestCountrySeam(unittest.TestCase):
    def test_saudi_registered(self):
        self.assertIn("Saudi Arabia", COUNTRY_REGISTRY)
        self.assertEqual(COUNTRY_REGISTRY["Saudi Arabia"], "ramz_hr.countries.saudi")

    def test_get_active_country_module_returns_saudi_by_default(self):
        frappe.db.set_single_value("Ramz HR Settings", "country", "Saudi Arabia")
        mod = get_active_country_module()
        self.assertEqual(mod.__name__, "ramz_hr.countries.saudi")

    def test_get_active_country_module_throws_for_unknown(self):
        # simulate a site configured for a not-yet-implemented country
        with patch(
            "frappe.db.get_single_value",
            return_value="Bangladesh",
        ):
            with self.assertRaises(frappe.ValidationError):
                get_active_country_module()
