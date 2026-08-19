import frappe
from frappe.model.document import Document


class RamzHRSettings(Document):
    def validate(self):
        if self.casual_leave_days is not None and not (0 <= int(self.casual_leave_days) <= 14):
            frappe.throw("Casual Leave Days must be between 0 and 14")
        if self.fiscal_year_start_month is not None and not (1 <= int(self.fiscal_year_start_month) <= 12):
            frappe.throw("Fiscal Year Start Month must be between 1 and 12")
