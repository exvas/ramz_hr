import datetime

import frappe
import unittest

from ramz_hr.countries.saudi.validators import (
    validate_iqama_format,
    validate_iqama_expiry_presence,
    validate_iban_format,
    compute_probation_end_date,
)


class _Stub:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def get(self, key, default=None):
        return self.__dict__.get(key, default)


class TestEmployeeValidators(unittest.TestCase):
    def test_iqama_valid_10_digits(self):
        doc = _Stub(custom_iqama_number="1234567890")
        validate_iqama_format(doc)  # should not raise

    def test_iqama_wrong_length(self):
        doc = _Stub(custom_iqama_number="12345")
        with self.assertRaises(frappe.ValidationError):
            validate_iqama_format(doc)

    def test_iqama_non_digits(self):
        doc = _Stub(custom_iqama_number="12345ABCDE")
        with self.assertRaises(frappe.ValidationError):
            validate_iqama_format(doc)

    def test_iqama_blank_is_allowed(self):
        doc = _Stub(custom_iqama_number="")
        validate_iqama_format(doc)  # blank → skip

    def test_iqama_expiry_required_for_non_saudi(self):
        doc = _Stub(custom_nationality="India", custom_iqama_expiry=None)
        with self.assertRaises(frappe.ValidationError):
            validate_iqama_expiry_presence(doc)

    def test_iqama_expiry_optional_for_saudi(self):
        doc = _Stub(custom_nationality="Saudi Arabia", custom_iqama_expiry=None)
        validate_iqama_expiry_presence(doc)  # not raised

    def test_iban_valid(self):
        doc = _Stub(custom_iban="SA" + "1" * 22)
        validate_iban_format(doc)

    def test_iban_wrong_prefix(self):
        doc = _Stub(custom_iban="AE" + "1" * 22)
        with self.assertRaises(frappe.ValidationError):
            validate_iban_format(doc)

    def test_iban_wrong_length(self):
        doc = _Stub(custom_iban="SA" + "1" * 10)
        with self.assertRaises(frappe.ValidationError):
            validate_iban_format(doc)

    def test_iban_blank_is_allowed(self):
        doc = _Stub(custom_iban="")
        validate_iban_format(doc)

    def test_probation_end_date_auto_computed(self):
        doc = _Stub(
            date_of_joining=datetime.date(2026, 1, 1),
            custom_probation_period_days=90,
            custom_probation_end_date=None,
        )
        compute_probation_end_date(doc)
        self.assertEqual(doc.custom_probation_end_date, datetime.date(2026, 4, 1))

    def test_probation_days_out_of_range(self):
        doc = _Stub(
            date_of_joining=datetime.date(2026, 1, 1),
            custom_probation_period_days=999,
            custom_probation_end_date=None,
        )
        with self.assertRaises(frappe.ValidationError):
            compute_probation_end_date(doc)
