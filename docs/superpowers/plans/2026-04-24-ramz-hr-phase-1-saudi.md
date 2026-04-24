# Ramz HR Phase 1 (Saudi) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Phase 1 of `ramz_hr` — Saudi HR customization covering Employee master fields, 11 Leave Types & Saudi Holiday List, Salary Structure with Basic 50–70% validation, plus a country-abstraction seam ready for UAE/Qatar/India.

**Architecture:** Single Frappe app layered on stock HRMS v15+. Custom Fields via fixtures. Saudi-specific logic in `ramz_hr/countries/saudi/`. A `Ramz HR Settings` Single doctype drives country dispatch and configurable thresholds. No stock-doctype class overrides.

**Tech Stack:** Frappe v15, HRMS v15, Python 3.10+, Frappe's built-in `unittest` runner.

**Spec:** [2026-04-24-ramz-hr-phase-1-saudi-design.md](../specs/2026-04-24-ramz-hr-phase-1-saudi-design.md)

---

## Working environment

- **Bench path:** `/Users/sammishthundiyil/frappe-bench-kenz/`
- **App path:** `apps/ramz_hr/` (already git-initialized, branch `develop`, remote `origin` → `https://github.com/exvas/ramz_hr.git`)
- **Target site:** `ramzunited` (Saudi site on this bench)
- **Module name (Title Case):** `Ramz HR` (as defined in `ramz_hr/modules.txt`)
- **Python package root:** `apps/ramz_hr/ramz_hr/` (standard Frappe layout — outer folder is project, inner is app package)

## Commands you'll use repeatedly

```bash
# Run from bench root
cd /Users/sammishthundiyil/frappe-bench-kenz

# Apply code → DB changes
bench --site ramzunited migrate

# Run the app's tests
bench --site ramzunited run-tests --app ramz_hr

# Run a single test
bench --site ramzunited run-tests --app ramz_hr --module ramz_hr.tests.test_install

# Open a python REPL bound to the site (useful for inspection)
bench --site ramzunited console

# Clear cache (often needed after Custom Field changes)
bench --site ramzunited clear-cache
```

## Ground rules

1. **TDD**: for each task, write the failing test, verify it fails, implement, verify it passes, commit. Do not write production code without a test that demands it.
2. **Idempotency**: every seed function must tolerate being re-run. Check existence before insert; patch blank fields only; never overwrite admin-set values.
3. **Commits**: one commit per task. Use `feat:` / `test:` / `chore:` / `docs:` prefixes matching the existing repo (`feat: Initialize App`, `docs: add Phase 1 design spec`).
4. **File paths**: always absolute from bench root in commands; absolute from app root in file listings.
5. **Do not** override stock HRMS doctype classes. Do not add fields that Phase 1 doesn't validate or display with purpose.

## File structure created by this plan

```
apps/ramz_hr/ramz_hr/
├── hooks.py                                          # MODIFIED: doc_events, after_install/after_migrate, fixtures
├── install.py                                        # CREATED: orchestrator
├── ramz_hr/                                          # (existing module folder)
│   ├── doctype/
│   │   ├── __init__.py                               # CREATED
│   │   ├── ramz_hr_settings/
│   │   │   ├── __init__.py
│   │   │   ├── ramz_hr_settings.json
│   │   │   └── ramz_hr_settings.py
│   │   └── medical_insurance_class/
│   │       ├── __init__.py
│   │       ├── medical_insurance_class.json
│   │       └── medical_insurance_class.py
├── countries/
│   ├── __init__.py                                   # CREATED: COUNTRY_REGISTRY + dispatch
│   └── saudi/
│       ├── __init__.py                               # CREATED: setup() aggregator
│       ├── custom_fields.py                          # CREATED: CUSTOM_FIELDS + PROPERTY_SETTERS + sync fn
│       ├── validators.py                             # CREATED: Employee.validate handler
│       ├── holidays.py                               # CREATED: Saudi Holiday List seeder
│       ├── salary_components.py                      # CREATED: components + Salary Structure seeder
│       ├── leave_types.py                            # CREATED: 11 types + Policy + Period + auto-assign
│       └── medical_insurance_class.py                # CREATED: seed VIP/A+/A/B/C
├── overrides/
│   ├── __init__.py                                   # CREATED
│   └── salary_structure_assignment.py                # CREATED: Basic% validator
└── tests/
    ├── __init__.py                                   # CREATED
    ├── test_install.py                               # CREATED
    ├── test_employee_validators.py                   # CREATED
    ├── test_leave_setup.py                           # CREATED
    ├── test_basic_pct.py                             # CREATED
    └── test_country_seam.py                          # CREATED
```

Each file has one clear responsibility. Files that change together live together (the Saudi module is self-contained so future UAE/Qatar/India modules drop in parallel).

---

## Task 1: Scaffold app skeleton — `tests/`, `countries/`, `overrides/` folders

**Files:**
- Create: `apps/ramz_hr/ramz_hr/tests/__init__.py`
- Create: `apps/ramz_hr/ramz_hr/countries/__init__.py` (empty for now — filled in Task 4)
- Create: `apps/ramz_hr/ramz_hr/countries/saudi/__init__.py` (empty for now — filled in Task 5)
- Create: `apps/ramz_hr/ramz_hr/overrides/__init__.py`
- Create: `apps/ramz_hr/ramz_hr/ramz_hr/doctype/__init__.py`

- [ ] **Step 1: Create empty package markers**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz/apps/ramz_hr
touch ramz_hr/tests/__init__.py
touch ramz_hr/countries/__init__.py
touch ramz_hr/countries/saudi/__init__.py
touch ramz_hr/overrides/__init__.py
touch ramz_hr/ramz_hr/doctype/__init__.py
mkdir -p ramz_hr/tests ramz_hr/countries/saudi ramz_hr/overrides ramz_hr/ramz_hr/doctype
```

- [ ] **Step 2: Verify directory structure**

```bash
find ramz_hr -type d -not -path '*__pycache__*' -not -path '*.git*' | sort
```

Expected output (at minimum):
```
ramz_hr
ramz_hr/config
ramz_hr/countries
ramz_hr/countries/saudi
ramz_hr/overrides
ramz_hr/patches
ramz_hr/public
ramz_hr/ramz_hr
ramz_hr/ramz_hr/doctype
ramz_hr/templates
ramz_hr/tests
ramz_hr/www
```

- [ ] **Step 3: Commit**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz/apps/ramz_hr
git add ramz_hr/
git commit -m "chore: scaffold countries/, overrides/, tests/ folders"
```

---

## Task 2: Create `Ramz HR Settings` Single doctype

**Files:**
- Create: `apps/ramz_hr/ramz_hr/ramz_hr/doctype/ramz_hr_settings/__init__.py`
- Create: `apps/ramz_hr/ramz_hr/ramz_hr/doctype/ramz_hr_settings/ramz_hr_settings.json`
- Create: `apps/ramz_hr/ramz_hr/ramz_hr/doctype/ramz_hr_settings/ramz_hr_settings.py`
- Create: `apps/ramz_hr/ramz_hr/tests/test_install.py` (first test case only for this task — we'll extend it later)

- [ ] **Step 1: Write the failing test**

Create `apps/ramz_hr/ramz_hr/tests/test_install.py`:

```python
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
```

- [ ] **Step 2: Run test, confirm it fails**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz
bench --site ramzunited run-tests --app ramz_hr --module ramz_hr.tests.test_install
```
Expected: both tests fail with `DocType 'Ramz HR Settings' not found` or similar.

- [ ] **Step 3: Create doctype folder marker**

Create `apps/ramz_hr/ramz_hr/ramz_hr/doctype/ramz_hr_settings/__init__.py` (empty file).

- [ ] **Step 4: Create the doctype JSON**

Create `apps/ramz_hr/ramz_hr/ramz_hr/doctype/ramz_hr_settings/ramz_hr_settings.json`:

```json
{
 "actions": [],
 "creation": "2026-04-24 12:00:00.000000",
 "doctype": "DocType",
 "engine": "InnoDB",
 "field_order": [
  "country_section",
  "country",
  "column_break_country",
  "fiscal_year_start_month",
  "leave_section",
  "auto_assign_leave_policy",
  "default_leave_policy",
  "casual_leave_days",
  "column_break_leave",
  "iqama_reminder_days",
  "salary_section",
  "basic_salary_component",
  "basic_pct_min",
  "column_break_salary",
  "basic_pct_max",
  "basic_pct_strict"
 ],
 "fields": [
  {"fieldname": "country_section", "fieldtype": "Section Break", "label": "Country"},
  {"fieldname": "country", "fieldtype": "Select", "label": "Country", "options": "Saudi Arabia", "default": "Saudi Arabia", "reqd": 1, "description": "Drives country-module dispatch. Select options expand as countries are added."},
  {"fieldname": "column_break_country", "fieldtype": "Column Break"},
  {"fieldname": "fiscal_year_start_month", "fieldtype": "Int", "label": "Fiscal Year Start Month", "default": "1", "description": "Used to seed Leave Period (1 = January)."},
  {"fieldname": "leave_section", "fieldtype": "Section Break", "label": "Leave Defaults"},
  {"fieldname": "auto_assign_leave_policy", "fieldtype": "Check", "label": "Auto-Assign Leave Policy on Employee Create", "default": "1"},
  {"fieldname": "default_leave_policy", "fieldtype": "Link", "label": "Default Leave Policy", "options": "Leave Policy"},
  {"fieldname": "casual_leave_days", "fieldtype": "Int", "label": "Casual Leave Days / Year", "default": "7", "description": "PDF range 3–7. Used at install time when seeding the Leave Policy."},
  {"fieldname": "column_break_leave", "fieldtype": "Column Break"},
  {"fieldname": "iqama_reminder_days", "fieldtype": "Int", "label": "Iqama Expiry Reminder (Days)", "default": "30", "description": "Reserved — used by Phase 2 Iqama-expiry scheduler."},
  {"fieldname": "salary_section", "fieldtype": "Section Break", "label": "Salary Validation"},
  {"fieldname": "basic_salary_component", "fieldtype": "Link", "label": "Basic Salary Component", "options": "Salary Component", "description": "Which Salary Component is considered "Basic" for the 50–70% rule."},
  {"fieldname": "basic_pct_min", "fieldtype": "Float", "label": "Basic % Minimum", "default": "50"},
  {"fieldname": "column_break_salary", "fieldtype": "Column Break"},
  {"fieldname": "basic_pct_max", "fieldtype": "Float", "label": "Basic % Maximum", "default": "70"},
  {"fieldname": "basic_pct_strict", "fieldtype": "Check", "label": "Strict Basic % Enforcement", "default": "1", "description": "1 = throw on violation; 0 = warning only."}
 ],
 "index_web_pages_for_search": 1,
 "issingle": 1,
 "links": [],
 "modified": "2026-04-24 12:00:00.000000",
 "modified_by": "Administrator",
 "module": "Ramz HR",
 "name": "Ramz HR Settings",
 "owner": "Administrator",
 "permissions": [
  {"create": 1, "delete": 1, "email": 1, "print": 1, "read": 1, "role": "System Manager", "share": 1, "write": 1},
  {"read": 1, "role": "HR Manager", "write": 1}
 ],
 "sort_field": "modified",
 "sort_order": "DESC",
 "states": [],
 "track_changes": 1
}
```

- [ ] **Step 5: Create the Python controller**

Create `apps/ramz_hr/ramz_hr/ramz_hr/doctype/ramz_hr_settings/ramz_hr_settings.py`:

```python
import frappe
from frappe.model.document import Document


class RamzHRSettings(Document):
    def validate(self):
        if self.basic_pct_min is not None and self.basic_pct_max is not None:
            if float(self.basic_pct_min) >= float(self.basic_pct_max):
                frappe.throw("Basic % Minimum must be less than Basic % Maximum")
        if self.casual_leave_days is not None and not (0 <= int(self.casual_leave_days) <= 14):
            frappe.throw("Casual Leave Days must be between 0 and 14")
        if self.fiscal_year_start_month is not None and not (1 <= int(self.fiscal_year_start_month) <= 12):
            frappe.throw("Fiscal Year Start Month must be between 1 and 12")
```

- [ ] **Step 6: Migrate + run test**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz
bench --site ramzunited migrate
bench --site ramzunited run-tests --app ramz_hr --module ramz_hr.tests.test_install
```
Expected: both tests pass.

- [ ] **Step 7: Commit**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz/apps/ramz_hr
git add ramz_hr/ramz_hr/doctype/ramz_hr_settings/ ramz_hr/tests/test_install.py ramz_hr/ramz_hr/doctype/__init__.py
git commit -m "feat: add Ramz HR Settings single doctype"
```

---

## Task 3: Create `Medical Insurance Class` doctype

**Files:**
- Create: `apps/ramz_hr/ramz_hr/ramz_hr/doctype/medical_insurance_class/__init__.py`
- Create: `apps/ramz_hr/ramz_hr/ramz_hr/doctype/medical_insurance_class/medical_insurance_class.json`
- Create: `apps/ramz_hr/ramz_hr/ramz_hr/doctype/medical_insurance_class/medical_insurance_class.py`
- Modify: `apps/ramz_hr/ramz_hr/tests/test_install.py` (append test)

- [ ] **Step 1: Add failing test**

Append to `apps/ramz_hr/ramz_hr/tests/test_install.py` (inside the same `TestInstall` class):

```python
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
```

- [ ] **Step 2: Run test, confirm it fails**

```bash
bench --site ramzunited run-tests --app ramz_hr --module ramz_hr.tests.test_install
```
Expected: the two new tests fail.

- [ ] **Step 3: Create the doctype**

Create `apps/ramz_hr/ramz_hr/ramz_hr/doctype/medical_insurance_class/__init__.py` (empty).

Create `apps/ramz_hr/ramz_hr/ramz_hr/doctype/medical_insurance_class/medical_insurance_class.json`:

```json
{
 "actions": [],
 "autoname": "field:class_name",
 "creation": "2026-04-24 12:00:00.000000",
 "doctype": "DocType",
 "engine": "InnoDB",
 "field_order": ["class_name", "description"],
 "fields": [
  {"fieldname": "class_name", "fieldtype": "Data", "label": "Class Name", "reqd": 1, "unique": 1, "in_list_view": 1},
  {"fieldname": "description", "fieldtype": "Small Text", "label": "Description"}
 ],
 "index_web_pages_for_search": 1,
 "links": [],
 "modified": "2026-04-24 12:00:00.000000",
 "modified_by": "Administrator",
 "module": "Ramz HR",
 "name": "Medical Insurance Class",
 "owner": "Administrator",
 "permissions": [
  {"create": 1, "delete": 1, "email": 1, "print": 1, "read": 1, "role": "System Manager", "share": 1, "write": 1},
  {"create": 1, "delete": 1, "read": 1, "role": "HR Manager", "write": 1},
  {"read": 1, "role": "HR User"}
 ],
 "sort_field": "modified",
 "sort_order": "DESC",
 "states": [],
 "track_changes": 1
}
```

Create `apps/ramz_hr/ramz_hr/ramz_hr/doctype/medical_insurance_class/medical_insurance_class.py`:

```python
from frappe.model.document import Document


class MedicalInsuranceClass(Document):
    pass
```

- [ ] **Step 4: Migrate + run test**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz
bench --site ramzunited migrate
bench --site ramzunited run-tests --app ramz_hr --module ramz_hr.tests.test_install
```
Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz/apps/ramz_hr
git add ramz_hr/ramz_hr/doctype/medical_insurance_class/ ramz_hr/tests/test_install.py
git commit -m "feat: add Medical Insurance Class lookup doctype"
```

---

## Task 4: Country dispatcher — `countries/__init__.py`

**Files:**
- Modify: `apps/ramz_hr/ramz_hr/countries/__init__.py`
- Create: `apps/ramz_hr/ramz_hr/tests/test_country_seam.py`

- [ ] **Step 1: Write the failing test**

Create `apps/ramz_hr/ramz_hr/tests/test_country_seam.py`:

```python
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
```

- [ ] **Step 2: Run test, confirm it fails**

```bash
bench --site ramzunited run-tests --app ramz_hr --module ramz_hr.tests.test_country_seam
```
Expected: fails — `COUNTRY_REGISTRY` doesn't exist.

- [ ] **Step 3: Implement the dispatcher**

Write `apps/ramz_hr/ramz_hr/countries/__init__.py`:

```python
"""Country-module dispatcher for ramz_hr.

Each country's rules (custom fields, holidays, leave types, salary components,
lookup data) live in a dedicated sub-module. The active country is read from
Ramz HR Settings.country at install/migrate time; install.py calls the
returned module's setup() function.

To add a new country:
    1. Create ramz_hr/countries/<slug>/ with an __init__.py exposing setup()
    2. Register it below in COUNTRY_REGISTRY
    3. On the target site, set Ramz HR Settings.country = "<Country Name>"
"""
from __future__ import annotations

import importlib

import frappe

COUNTRY_REGISTRY: dict[str, str] = {
    "Saudi Arabia": "ramz_hr.countries.saudi",
    # "United Arab Emirates": "ramz_hr.countries.uae",
    # "Qatar":                "ramz_hr.countries.qatar",
    # "India":                "ramz_hr.countries.india",
}


def get_active_country_module():
    country = frappe.db.get_single_value("Ramz HR Settings", "country") or "Saudi Arabia"
    if country not in COUNTRY_REGISTRY:
        frappe.throw(
            f"Country '{country}' is not implemented in ramz_hr yet. "
            f"Supported: {sorted(COUNTRY_REGISTRY)}"
        )
    return importlib.import_module(COUNTRY_REGISTRY[country])
```

- [ ] **Step 4: Run test, verify passes**

```bash
bench --site ramzunited run-tests --app ramz_hr --module ramz_hr.tests.test_country_seam
```
Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz/apps/ramz_hr
git add ramz_hr/countries/__init__.py ramz_hr/tests/test_country_seam.py
git commit -m "feat: add country-module dispatcher with Saudi Arabia registered"
```

---

## Task 5: Saudi module scaffold — `countries/saudi/__init__.py` aggregator

**Files:**
- Modify: `apps/ramz_hr/ramz_hr/countries/saudi/__init__.py`

- [ ] **Step 1: Write the aggregator (no test yet — Tasks 6–11 add the real seeders)**

Write `apps/ramz_hr/ramz_hr/countries/saudi/__init__.py`:

```python
"""Saudi Arabia country module for ramz_hr.

Exposes a single setup() entry point that install.py calls. setup() is
idempotent: running it twice is safe and never overwrites admin-modified
records. It composes the 5 sub-setups; each sub-module keeps its logic
isolated for clarity and future country parity.
"""
from __future__ import annotations

import frappe


def setup() -> None:
    """Run all Saudi seeders in dependency order."""
    from ramz_hr.countries.saudi import (
        custom_fields,
        medical_insurance_class,
        holidays,
        salary_components,
        leave_types,
    )

    # Order matters:
    #   1. Lookup doctypes first (Medical Insurance Class) so fields can Link to them.
    #   2. Custom fields on Employee (requires Medical Insurance Class to exist for the Link field).
    #   3. Holiday list (independent).
    #   4. Salary components + structure (independent).
    #   5. Leave types + policy + period (depends on nothing above, but seeded last to keep logical groupings adjacent).

    medical_insurance_class.setup()
    custom_fields.setup()
    holidays.setup()
    salary_components.setup()
    leave_types.setup()

    frappe.logger("ramz_hr").info("Saudi module setup complete")
```

- [ ] **Step 2: Commit (will fail imports until Tasks 6–11 land — we push anyway as a checkpoint)**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz/apps/ramz_hr
git add ramz_hr/countries/saudi/__init__.py
git commit -m "feat: add Saudi country module setup() aggregator"
```

---

## Task 6: Saudi — Medical Insurance Class seeder

**Files:**
- Create: `apps/ramz_hr/ramz_hr/countries/saudi/medical_insurance_class.py`
- Modify: `apps/ramz_hr/ramz_hr/tests/test_install.py` (append test)

- [ ] **Step 1: Add failing test**

Append to `apps/ramz_hr/ramz_hr/tests/test_install.py`:

```python
    def test_medical_insurance_classes_seeded(self):
        expected = {"VIP", "A+", "A", "B", "C"}
        existing = set(frappe.get_all("Medical Insurance Class", pluck="name"))
        missing = expected - existing
        self.assertEqual(missing, set(), f"Seeded Medical Insurance Classes missing: {missing}")
```

- [ ] **Step 2: Run test, confirm failure**

```bash
bench --site ramzunited run-tests --app ramz_hr --module ramz_hr.tests.test_install
```
Expected: `test_medical_insurance_classes_seeded` fails.

- [ ] **Step 3: Implement seeder**

Create `apps/ramz_hr/ramz_hr/countries/saudi/medical_insurance_class.py`:

```python
from __future__ import annotations

import frappe

SEED_CLASSES: list[tuple[str, str]] = [
    ("VIP", "Top-tier medical coverage, private hospitals"),
    ("A+", "Premium coverage"),
    ("A", "Standard coverage"),
    ("B", "Basic coverage"),
    ("C", "Entry-level coverage"),
]


def setup() -> None:
    for name, description in SEED_CLASSES:
        if frappe.db.exists("Medical Insurance Class", name):
            # Patch blank description only — never overwrite admin-set value.
            current = frappe.db.get_value("Medical Insurance Class", name, "description")
            if not current and description:
                frappe.db.set_value("Medical Insurance Class", name, "description", description)
            continue

        doc = frappe.get_doc(
            {
                "doctype": "Medical Insurance Class",
                "class_name": name,
                "description": description,
            }
        )
        doc.insert(ignore_permissions=True)
    frappe.db.commit()
```

- [ ] **Step 4: Manually invoke seeder + run test**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz
bench --site ramzunited execute ramz_hr.countries.saudi.medical_insurance_class.setup
bench --site ramzunited run-tests --app ramz_hr --module ramz_hr.tests.test_install
```
Expected: all tests pass (including the new one).

- [ ] **Step 5: Commit**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz/apps/ramz_hr
git add ramz_hr/countries/saudi/medical_insurance_class.py ramz_hr/tests/test_install.py
git commit -m "feat: seed Medical Insurance Class defaults (VIP, A+, A, B, C)"
```

---

## Task 7: Saudi — Employee Custom Fields + Property Setters

**Files:**
- Create: `apps/ramz_hr/ramz_hr/countries/saudi/custom_fields.py`
- Modify: `apps/ramz_hr/ramz_hr/tests/test_install.py` (append test)

- [ ] **Step 1: Add failing test**

Append to `apps/ramz_hr/ramz_hr/tests/test_install.py`:

```python
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
        meta = frappe.get_meta("Employee")
        nat = next((df for df in meta.fields if df.fieldname == "nationality"), None)
        self.assertIsNotNone(nat)
        self.assertEqual(nat.reqd, 1, "Employee.nationality must be required by property setter")
```

- [ ] **Step 2: Run test, confirm failure**

```bash
bench --site ramzunited run-tests --app ramz_hr --module ramz_hr.tests.test_install
```
Expected: both new tests fail.

- [ ] **Step 3: Implement custom_fields seeder**

Create `apps/ramz_hr/ramz_hr/countries/saudi/custom_fields.py`:

```python
"""Saudi-specific Custom Fields + Property Setters for stock doctypes.

Design note: fields are grouped by visual section for the Employee form.
Fieldname prefix is `custom_` per Frappe convention; underscores in labels
are translated to spaces by Frappe's UI automatically.
"""
from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


CUSTOM_FIELDS: dict[str, list[dict]] = {
    "Employee": [
        # ---- Saudi Employment Details section ----
        {
            "fieldname": "custom_saudi_employment_details_section",
            "fieldtype": "Section Break",
            "label": "Saudi Employment Details",
            "insert_after": "department",
            "collapsible": 1,
        },
        {
            "fieldname": "custom_iqama_number",
            "fieldtype": "Data",
            "label": "Iqama / National ID",
            "insert_after": "custom_saudi_employment_details_section",
            "description": "10 digits. Iqama for expats, National ID for Saudi nationals.",
        },
        {
            "fieldname": "custom_iqama_expiry",
            "fieldtype": "Date",
            "label": "Iqama Expiry",
            "insert_after": "custom_iqama_number",
            "description": "Mandatory for non-Saudi nationals.",
        },
        {
            "fieldname": "custom_contract_type",
            "fieldtype": "Select",
            "label": "Contract Type",
            "options": "\nLimited\nUnlimited",
            "insert_after": "custom_iqama_expiry",
            "description": "Saudi Labor Law contract type (used by EOSB formula).",
        },
        {
            "fieldname": "custom_employment_column_break",
            "fieldtype": "Column Break",
            "insert_after": "custom_contract_type",
        },
        {
            "fieldname": "custom_work_location",
            "fieldtype": "Data",
            "label": "Work Location",
            "insert_after": "custom_employment_column_break",
        },
        {
            "fieldname": "custom_probation_period_days",
            "fieldtype": "Int",
            "label": "Probation Period (Days)",
            "default": "90",
            "insert_after": "custom_work_location",
            "description": "Saudi Labor Law max 180 days.",
        },
        {
            "fieldname": "custom_probation_end_date",
            "fieldtype": "Date",
            "label": "Probation End Date",
            "read_only": 1,
            "insert_after": "custom_probation_period_days",
            "description": "Auto-computed from Date of Joining + Probation Period.",
        },
        # ---- Benefits & Entitlements section ----
        {
            "fieldname": "custom_benefits_section",
            "fieldtype": "Section Break",
            "label": "Benefits & Entitlements",
            "insert_after": "custom_probation_end_date",
            "collapsible": 1,
        },
        {
            "fieldname": "custom_air_ticket_eligibility",
            "fieldtype": "Select",
            "label": "Air Ticket Eligibility",
            "options": "\nNone\nAnnual\nBiennial",
            "insert_after": "custom_benefits_section",
        },
        {
            "fieldname": "custom_benefits_column_break",
            "fieldtype": "Column Break",
            "insert_after": "custom_air_ticket_eligibility",
        },
        {
            "fieldname": "custom_medical_insurance_class",
            "fieldtype": "Link",
            "label": "Medical Insurance Class",
            "options": "Medical Insurance Class",
            "insert_after": "custom_benefits_column_break",
        },
        # ---- Saudi Payroll Info section ----
        {
            "fieldname": "custom_saudi_payroll_section",
            "fieldtype": "Section Break",
            "label": "Saudi Payroll Info",
            "insert_after": "custom_medical_insurance_class",
            "collapsible": 1,
        },
        {
            "fieldname": "custom_iban",
            "fieldtype": "Data",
            "label": "IBAN",
            "insert_after": "custom_saudi_payroll_section",
            "description": "Saudi IBAN: 'SA' + 22 digits.",
        },
    ],
}


# [doctype, fieldname, property, property_type, value]
PROPERTY_SETTERS: list[tuple[str, str, str, str, str]] = [
    ("Employee", "nationality", "reqd", "Check", "1"),
    ("Employee", "date_of_joining", "reqd", "Check", "1"),
    ("Salary Structure Assignment", "base", "reqd", "Check", "1"),
]


# (doctype, fieldname) pairs to remove on migrate if no FK references exist.
DEPRECATED_FIELDS: list[tuple[str, str]] = []


def setup() -> None:
    create_custom_fields(CUSTOM_FIELDS, update=True)
    for dt, fn, prop, ptype, value in PROPERTY_SETTERS:
        make_property_setter(dt, fn, prop, value, ptype, validate_fields_for_doctype=False)
    _remove_deprecated()
    frappe.db.commit()


def _remove_deprecated() -> None:
    for dt, fn in DEPRECATED_FIELDS:
        cf = frappe.db.get_value("Custom Field", {"dt": dt, "fieldname": fn})
        if cf:
            # Only delete if no records use the field (safe check).
            refs = frappe.db.sql(f"SELECT COUNT(*) FROM `tab{dt}` WHERE `{fn}` IS NOT NULL AND `{fn}` != ''")
            if refs and refs[0][0] == 0:
                frappe.delete_doc("Custom Field", cf, ignore_permissions=True, force=True)
```

- [ ] **Step 4: Invoke seeder + migrate + test**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz
bench --site ramzunited execute ramz_hr.countries.saudi.custom_fields.setup
bench --site ramzunited clear-cache
bench --site ramzunited run-tests --app ramz_hr --module ramz_hr.tests.test_install
```
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz/apps/ramz_hr
git add ramz_hr/countries/saudi/custom_fields.py ramz_hr/tests/test_install.py
git commit -m "feat: add Saudi Employee custom fields and property setters"
```

---

## Task 8: Saudi — Employee validators (Iqama, IBAN, probation)

**Files:**
- Create: `apps/ramz_hr/ramz_hr/countries/saudi/validators.py`
- Create: `apps/ramz_hr/ramz_hr/tests/test_employee_validators.py`

- [ ] **Step 1: Write the failing tests**

Create `apps/ramz_hr/ramz_hr/tests/test_employee_validators.py`:

```python
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
        doc = _Stub(nationality="Indian", custom_iqama_expiry=None)
        with self.assertRaises(frappe.ValidationError):
            validate_iqama_expiry_presence(doc)

    def test_iqama_expiry_optional_for_saudi(self):
        doc = _Stub(nationality="Saudi Arabia", custom_iqama_expiry=None)
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
```

- [ ] **Step 2: Run test, confirm failure**

```bash
bench --site ramzunited run-tests --app ramz_hr --module ramz_hr.tests.test_employee_validators
```
Expected: all 12 tests fail (imports fail).

- [ ] **Step 3: Implement validators**

Create `apps/ramz_hr/ramz_hr/countries/saudi/validators.py`:

```python
"""Employee.validate handlers for Saudi Arabia.

Each function accepts the Employee doc and raises frappe.ValidationError on
failure. validate_employee() is the aggregator wired in hooks.py.
"""
from __future__ import annotations

import datetime
import re

import frappe

IQAMA_RE = re.compile(r"^\d{10}$")
IBAN_RE = re.compile(r"^SA\d{22}$")

MAX_PROBATION_DAYS = 180


def validate_employee(doc, method=None):
    """Wire point for doc_events.Employee.validate."""
    validate_iqama_format(doc)
    validate_iqama_expiry_presence(doc)
    validate_iban_format(doc)
    compute_probation_end_date(doc)


def validate_iqama_format(doc):
    iqama = (doc.get("custom_iqama_number") or "").strip()
    if not iqama:
        return
    if not IQAMA_RE.match(iqama):
        frappe.throw("Iqama / National ID must be exactly 10 digits.")


def validate_iqama_expiry_presence(doc):
    nationality = (doc.get("nationality") or "").strip()
    if nationality and nationality != "Saudi Arabia":
        if not doc.get("custom_iqama_expiry"):
            frappe.throw("Iqama Expiry is required for non-Saudi employees.")


def validate_iban_format(doc):
    iban = (doc.get("custom_iban") or "").strip()
    if not iban:
        return
    if not IBAN_RE.match(iban):
        frappe.throw("IBAN must match 'SA' followed by exactly 22 digits.")


def compute_probation_end_date(doc):
    days = doc.get("custom_probation_period_days")
    doj = doc.get("date_of_joining")
    if days is None or doj is None:
        return
    days = int(days)
    if not (0 <= days <= MAX_PROBATION_DAYS):
        frappe.throw(f"Probation Period must be between 0 and {MAX_PROBATION_DAYS} days.")
    if isinstance(doj, str):
        doj = datetime.date.fromisoformat(doj)
    doc.custom_probation_end_date = doj + datetime.timedelta(days=days)
```

- [ ] **Step 4: Run tests, verify pass**

```bash
bench --site ramzunited run-tests --app ramz_hr --module ramz_hr.tests.test_employee_validators
```
Expected: 12 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz/apps/ramz_hr
git add ramz_hr/countries/saudi/validators.py ramz_hr/tests/test_employee_validators.py
git commit -m "feat: add Saudi employee validators (Iqama, IBAN, probation)"
```

---

## Task 9: Saudi — Holiday List seeder

**Files:**
- Create: `apps/ramz_hr/ramz_hr/countries/saudi/holidays.py`
- Modify: `apps/ramz_hr/ramz_hr/tests/test_install.py` (append test)

- [ ] **Step 1: Add failing test**

Append to `apps/ramz_hr/ramz_hr/tests/test_install.py`:

```python
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
```

- [ ] **Step 2: Run test, confirm failure**

```bash
bench --site ramzunited run-tests --app ramz_hr --module ramz_hr.tests.test_install
```
Expected: `test_saudi_holiday_list_seeded` fails.

- [ ] **Step 3: Implement holidays seeder**

Create `apps/ramz_hr/ramz_hr/countries/saudi/holidays.py`:

```python
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

# Best-effort Hijri → Gregorian mapping. Admin must verify against official
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
            "description": f"Eid Al-Fitr Day {i} (placeholder — verify with Ministry)",
        })
    for i, (month, day) in enumerate(EID_AL_ADHA_PLACEHOLDERS.get(year, []), start=1):
        hl.append("holidays", {
            "holiday_date": datetime.date(year, month, day),
            "description": f"Eid Al-Adha Day {i} (placeholder — verify with Ministry)",
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
```

- [ ] **Step 4: Invoke + test**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz
bench --site ramzunited execute ramz_hr.countries.saudi.holidays.setup
bench --site ramzunited run-tests --app ramz_hr --module ramz_hr.tests.test_install
```
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz/apps/ramz_hr
git add ramz_hr/countries/saudi/holidays.py ramz_hr/tests/test_install.py
git commit -m "feat: seed Saudi Holiday List (Founding Day, National Day, Eid placeholders, Fri+Sat off)"
```

---

## Task 10: Saudi — Salary Components + "Ramz Saudi Standard" Structure

**Files:**
- Create: `apps/ramz_hr/ramz_hr/countries/saudi/salary_components.py`
- Modify: `apps/ramz_hr/ramz_hr/tests/test_install.py` (append test)

- [ ] **Step 1: Add failing test**

Append to `apps/ramz_hr/ramz_hr/tests/test_install.py`:

```python
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
        self.assertEqual(s.is_active, 1)
        earnings = {row.salary_component for row in s.earnings}
        self.assertEqual(earnings, {"Basic", "Housing Allowance", "Transportation Allowance"})
```

- [ ] **Step 2: Run test, confirm failure**

```bash
bench --site ramzunited run-tests --app ramz_hr --module ramz_hr.tests.test_install
```
Expected: both new tests fail.

- [ ] **Step 3: Implement seeder**

Create `apps/ramz_hr/ramz_hr/countries/saudi/salary_components.py`:

```python
"""Saudi Salary Components + base Salary Structure seeder."""
from __future__ import annotations

import frappe

COMPONENTS: list[dict] = [
    {
        "salary_component": "Basic",
        "salary_component_abbr": "BASIC",
        "type": "Earning",
        "depends_on_payment_days": 1,
        "is_tax_applicable": 0,
    },
    {
        "salary_component": "Housing Allowance",
        "salary_component_abbr": "HRA",
        "type": "Earning",
        "depends_on_payment_days": 1,
        "is_tax_applicable": 0,
    },
    {
        "salary_component": "Transportation Allowance",
        "salary_component_abbr": "TA",
        "type": "Earning",
        "depends_on_payment_days": 1,
        "is_tax_applicable": 0,
    },
]

STRUCTURE_NAME = "Ramz Saudi Standard"


def setup() -> None:
    for comp in COMPONENTS:
        name = comp["salary_component"]
        if frappe.db.exists("Salary Component", name):
            continue
        doc = frappe.get_doc({
            "doctype": "Salary Component",
            **comp,
        })
        doc.insert(ignore_permissions=True)

    if not frappe.db.exists("Salary Structure", STRUCTURE_NAME):
        ss = frappe.new_doc("Salary Structure")
        ss.name = STRUCTURE_NAME
        ss.is_active = "Yes"
        ss.payroll_frequency = "Monthly"
        ss.currency = frappe.db.get_default("currency") or "SAR"
        for comp in COMPONENTS:
            ss.append("earnings", {
                "salary_component": comp["salary_component"],
                "abbr": comp["salary_component_abbr"],
                "amount_based_on_formula": 0,
            })
        ss.insert(ignore_permissions=True)

    # Seed Ramz HR Settings.basic_salary_component if blank
    settings = frappe.get_single("Ramz HR Settings")
    if not settings.basic_salary_component:
        settings.basic_salary_component = "Basic"
        settings.save(ignore_permissions=True)

    frappe.db.commit()
```

- [ ] **Step 4: Invoke + test**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz
bench --site ramzunited execute ramz_hr.countries.saudi.salary_components.setup
bench --site ramzunited run-tests --app ramz_hr --module ramz_hr.tests.test_install
```
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz/apps/ramz_hr
git add ramz_hr/countries/saudi/salary_components.py ramz_hr/tests/test_install.py
git commit -m "feat: seed Saudi Salary Components and Ramz Saudi Standard structure"
```

---

## Task 11: Saudi — Leave Types + Leave Policy + Leave Period

**Files:**
- Create: `apps/ramz_hr/ramz_hr/countries/saudi/leave_types.py`
- Create: `apps/ramz_hr/ramz_hr/tests/test_leave_setup.py`

- [ ] **Step 1: Write the failing tests**

Create `apps/ramz_hr/ramz_hr/tests/test_leave_setup.py`:

```python
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
```

- [ ] **Step 2: Run test, confirm failure**

```bash
bench --site ramzunited run-tests --app ramz_hr --module ramz_hr.tests.test_leave_setup
```
Expected: all 9 tests fail.

- [ ] **Step 3: Implement seeder**

Create `apps/ramz_hr/ramz_hr/countries/saudi/leave_types.py`:

```python
"""Saudi Leave Types + Leave Policy + Leave Period seeder.

Sick leave is split into 3 tiers (Full / 75% / Unpaid) to model the PDF's
30/60/30 progression using stock HRMS fields without custom payroll logic.
"""
from __future__ import annotations

import datetime

import frappe

POLICY_NAME = "Ramz Saudi Standard"

# Base definition + allocation used by the Leave Policy.
LEAVE_TYPES: list[dict] = [
    {
        "leave_type_name": "Annual Leave",
        "max_leaves_allowed": 21,
        "is_carry_forward": 1,
        "max_carry_forwarded_leaves": 21,
        "is_lwp": 0,
        "is_ppl": 0,
        "allow_encashment": 1,
        "is_earned_leave": 1,
        "earned_leave_frequency": "Monthly",
        "annual_allocation": 21,
    },
    {
        "leave_type_name": "Casual Leave",
        "max_leaves_allowed": 7,
        "is_carry_forward": 0,
        "is_lwp": 0,
        "is_ppl": 0,
        "annual_allocation": 7,
    },
    {
        "leave_type_name": "Sick Leave - Full Pay",
        "max_leaves_allowed": 30,
        "is_carry_forward": 0,
        "is_lwp": 0,
        "is_ppl": 0,
        "annual_allocation": 30,
    },
    {
        "leave_type_name": "Sick Leave - 75%",
        "max_leaves_allowed": 60,
        "is_carry_forward": 0,
        "is_lwp": 0,
        "is_ppl": 1,
        "fraction_of_daily_salary_per_leave": 0.75,
        "annual_allocation": 60,
    },
    {
        "leave_type_name": "Sick Leave - Unpaid",
        "max_leaves_allowed": 30,
        "is_carry_forward": 0,
        "is_lwp": 1,
        "is_ppl": 0,
        "annual_allocation": 30,
    },
    {
        "leave_type_name": "Marriage Leave",
        "max_leaves_allowed": 5,
        "is_carry_forward": 0,
        "is_lwp": 0,
        "is_ppl": 0,
        "annual_allocation": 5,
    },
    {
        "leave_type_name": "Paternity Leave",
        "max_leaves_allowed": 3,
        "is_carry_forward": 0,
        "is_lwp": 0,
        "is_ppl": 0,
        "applicable_for_gender": "Male",
        "annual_allocation": 3,
    },
    {
        "leave_type_name": "Maternity Leave",
        "max_leaves_allowed": 70,
        "is_carry_forward": 0,
        "is_lwp": 0,
        "is_ppl": 0,
        "applicable_for_gender": "Female",
        "annual_allocation": 70,
    },
    {
        "leave_type_name": "Bereavement Leave",
        "max_leaves_allowed": 5,
        "is_carry_forward": 0,
        "is_lwp": 0,
        "is_ppl": 0,
        "annual_allocation": 5,
    },
    {
        "leave_type_name": "Hajj Leave",
        "max_leaves_allowed": 15,
        "is_carry_forward": 0,
        "is_lwp": 0,
        "is_ppl": 0,
        "annual_allocation": 15,
    },
    {
        "leave_type_name": "Unpaid Leave",
        "max_leaves_allowed": 0,
        "is_carry_forward": 0,
        "is_lwp": 1,
        "is_ppl": 0,
        "annual_allocation": None,  # not in Leave Policy
    },
]


def setup() -> None:
    for lt in LEAVE_TYPES:
        _ensure_leave_type(lt)
    _ensure_leave_policy()
    _ensure_leave_period()
    _seed_default_policy_in_settings()
    frappe.db.commit()


def _ensure_leave_type(spec: dict) -> None:
    name = spec["leave_type_name"]
    if frappe.db.exists("Leave Type", name):
        return
    payload = {k: v for k, v in spec.items() if k != "annual_allocation"}
    payload["doctype"] = "Leave Type"
    frappe.get_doc(payload).insert(ignore_permissions=True)


def _ensure_leave_policy() -> None:
    if frappe.db.exists("Leave Policy", POLICY_NAME):
        return
    policy = frappe.new_doc("Leave Policy")
    policy.title = POLICY_NAME
    for lt in LEAVE_TYPES:
        if lt["annual_allocation"] is None:
            continue
        policy.append("leave_policy_details", {
            "leave_type": lt["leave_type_name"],
            "annual_allocation": lt["annual_allocation"],
        })
    # Force .name == POLICY_NAME
    policy.name = POLICY_NAME
    policy.flags.name_set = True
    policy.insert(ignore_permissions=True)


def _ensure_leave_period() -> None:
    settings = frappe.get_single("Ramz HR Settings")
    start_month = int(settings.fiscal_year_start_month or 1)
    year = datetime.date.today().year
    name = f"Saudi {year}"
    if frappe.db.exists("Leave Period", name):
        return
    from_date = datetime.date(year, start_month, 1)
    # end on last day of month 12 months later (same date next year minus 1 day)
    to_year = year + 1 if start_month > 1 else year
    to_month = start_month - 1 if start_month > 1 else 12
    # last day of to_month
    if to_month == 12:
        to_date = datetime.date(to_year, 12, 31)
    else:
        to_date = datetime.date(to_year, to_month + 1, 1) - datetime.timedelta(days=1)

    period = frappe.new_doc("Leave Period")
    period.name = name
    period.from_date = from_date
    period.to_date = to_date
    period.is_active = 1
    period.flags.name_set = True
    period.insert(ignore_permissions=True)


def _seed_default_policy_in_settings() -> None:
    settings = frappe.get_single("Ramz HR Settings")
    if not settings.default_leave_policy and frappe.db.exists("Leave Policy", POLICY_NAME):
        settings.default_leave_policy = POLICY_NAME
        settings.save(ignore_permissions=True)


def auto_assign_leave_policy(doc, method=None):
    """doc_events handler wired on Employee.after_insert."""
    settings = frappe.get_single("Ramz HR Settings")
    if not settings.auto_assign_leave_policy:
        return
    policy_name = settings.default_leave_policy or POLICY_NAME
    if not frappe.db.exists("Leave Policy", policy_name):
        return
    year = datetime.date.today().year
    period_name = f"Saudi {year}"
    if not frappe.db.exists("Leave Period", period_name):
        return

    assignment = frappe.new_doc("Leave Policy Assignment")
    assignment.employee = doc.name
    assignment.assignment_based_on = "Leave Period"
    assignment.leave_policy = policy_name
    assignment.leave_period = period_name
    assignment.effective_from = doc.get("date_of_joining") or datetime.date(year, 1, 1)
    assignment.insert(ignore_permissions=True)
    assignment.submit()
```

- [ ] **Step 4: Invoke + test**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz
bench --site ramzunited execute ramz_hr.countries.saudi.leave_types.setup
bench --site ramzunited run-tests --app ramz_hr --module ramz_hr.tests.test_leave_setup
```
Expected: all 9 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz/apps/ramz_hr
git add ramz_hr/countries/saudi/leave_types.py ramz_hr/tests/test_leave_setup.py
git commit -m "feat: seed 11 Saudi Leave Types, Leave Policy, Leave Period"
```

---

## Task 12: Employee.after_insert auto-assign Leave Policy integration test

**Files:**
- Modify: `apps/ramz_hr/ramz_hr/tests/test_leave_setup.py` (append test)

- [ ] **Step 1: Append the failing test**

Append to `apps/ramz_hr/ramz_hr/tests/test_leave_setup.py`:

```python
class TestAutoAssignLeavePolicy(unittest.TestCase):
    def setUp(self):
        settings = frappe.get_single("Ramz HR Settings")
        settings.auto_assign_leave_policy = 1
        settings.save(ignore_permissions=True)

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
            "nationality": "Saudi Arabia",
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
        settings = frappe.get_single("Ramz HR Settings")
        settings.auto_assign_leave_policy = 0
        settings.save(ignore_permissions=True)
        emp = self._make_employee()
        assignments = frappe.get_all(
            "Leave Policy Assignment",
            filters={"employee": emp.name},
        )
        self.assertEqual(assignments, [])
```

- [ ] **Step 2: Run test, confirm failure**

```bash
bench --site ramzunited run-tests --app ramz_hr --module ramz_hr.tests.test_leave_setup
```
Expected: the 2 new tests fail because `doc_events` isn't wired yet. (Task 14 wires it.)

- [ ] **Step 3: No code change yet — this task sets the contract for Task 14**

Skip to commit; Task 14 completes this.

- [ ] **Step 4: Commit**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz/apps/ramz_hr
git add ramz_hr/tests/test_leave_setup.py
git commit -m "test: add auto-assign-leave-policy integration tests (expected to pass after hooks wiring in Task 14)"
```

---

## Task 13: Salary Structure Assignment Basic% validator

**Files:**
- Create: `apps/ramz_hr/ramz_hr/overrides/salary_structure_assignment.py`
- Create: `apps/ramz_hr/ramz_hr/tests/test_basic_pct.py`

- [ ] **Step 1: Write the failing test**

Create `apps/ramz_hr/ramz_hr/tests/test_basic_pct.py`:

```python
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
        settings = frappe.get_single("Ramz HR Settings")
        settings.basic_pct_min = 50
        settings.basic_pct_max = 70
        settings.basic_pct_strict = 1
        settings.basic_salary_component = "Basic"
        settings.save(ignore_permissions=True)

        # 6000 basic / 8500 gross = 70.588% → throws
        with self.assertRaises(frappe.ValidationError):
            _run_validator_with_amounts(base=6000, other_earnings={"Housing Allowance": 2000, "Transportation Allowance": 500})

    def test_validate_passes_within_bounds(self):
        _run_validator_with_amounts(base=5500, other_earnings={"Housing Allowance": 2000, "Transportation Allowance": 500})

    def test_validate_strict_off_only_warns(self):
        settings = frappe.get_single("Ramz HR Settings")
        settings.basic_pct_strict = 0
        settings.save(ignore_permissions=True)
        # Must NOT raise:
        _run_validator_with_amounts(base=6000, other_earnings={"Housing Allowance": 2000, "Transportation Allowance": 500})


def _run_validator_with_amounts(base, other_earnings):
    """Exercise validate_basic_percentage against Ramz Saudi Standard."""
    doc = _FakeAssignment(salary_structure="Ramz Saudi Standard", base=base)
    # Inject a helper the validator will use to read other-earning amounts.
    # For Phase 1 we rely on validate_basic_percentage's own resolver; this test
    # simulates by temporarily setting default amounts on the structure's rows.
    ss = frappe.get_doc("Salary Structure", "Ramz Saudi Standard")
    for row in ss.earnings:
        row.amount = other_earnings.get(row.salary_component, 0)
    validate_basic_percentage(doc, salary_structure=ss)
```

- [ ] **Step 2: Run test, confirm failure**

```bash
bench --site ramzunited run-tests --app ramz_hr --module ramz_hr.tests.test_basic_pct
```
Expected: all 5 tests fail (module doesn't exist yet).

- [ ] **Step 3: Implement validator**

Create `apps/ramz_hr/ramz_hr/overrides/salary_structure_assignment.py`:

```python
"""Salary Structure Assignment validator: enforce Basic % is within
Ramz HR Settings bounds (default 50-70%).

Wired via doc_events.Salary Structure Assignment.validate in hooks.py.
"""
from __future__ import annotations

import frappe


def compute_basic_percentage(basic_amount: float, gross: float) -> float:
    if not gross:
        return 0.0
    return float(basic_amount) / float(gross) * 100.0


def validate_basic_percentage(doc, method=None, salary_structure=None):
    settings = frappe.get_single("Ramz HR Settings")
    basic_component = settings.basic_salary_component or "Basic"
    pct_min = float(settings.basic_pct_min or 50)
    pct_max = float(settings.basic_pct_max or 70)
    strict = bool(settings.basic_pct_strict)

    base = float(doc.get("base") or 0)
    if base <= 0:
        return  # validator only fires when base is set; base.reqd is enforced by property setter

    ss = salary_structure or frappe.get_doc("Salary Structure", doc.get("salary_structure"))
    earning_amounts = {}
    for row in ss.earnings:
        comp = row.salary_component
        if comp == basic_component:
            earning_amounts[comp] = base
        else:
            earning_amounts[comp] = float(row.amount or 0)

    gross = sum(earning_amounts.values())
    if basic_component not in earning_amounts:
        # Structure doesn't include the basic component — skip silently
        return
    basic_amount = earning_amounts[basic_component]
    pct = compute_basic_percentage(basic_amount, gross)

    if pct_min <= pct <= pct_max:
        return

    msg = (
        f"Basic must be between {pct_min:.0f}% and {pct_max:.0f}% of gross "
        f"(currently {pct:.2f}%). "
        f"Basic={basic_amount:,.2f}, Gross={gross:,.2f}."
    )
    if strict:
        frappe.throw(msg)
    else:
        frappe.msgprint(msg, alert=True, indicator="orange")
```

- [ ] **Step 4: Run test, verify pass**

```bash
bench --site ramzunited run-tests --app ramz_hr --module ramz_hr.tests.test_basic_pct
```
Expected: all 5 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz/apps/ramz_hr
git add ramz_hr/overrides/salary_structure_assignment.py ramz_hr/tests/test_basic_pct.py
git commit -m "feat: add Salary Structure Assignment Basic% validator (50-70)"
```

---

## Task 14: Wire `install.py` + `hooks.py`

**Files:**
- Create: `apps/ramz_hr/ramz_hr/install.py`
- Modify: `apps/ramz_hr/ramz_hr/hooks.py`

- [ ] **Step 1: Create the orchestrator**

Create `apps/ramz_hr/ramz_hr/install.py`:

```python
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
```

- [ ] **Step 2: Wire `hooks.py`**

Open `apps/ramz_hr/ramz_hr/hooks.py` and append the following at the end of the file (after any existing commented-out blocks):

```python
# ---------------------------------------------------------------------------
# Ramz HR — active wiring
# ---------------------------------------------------------------------------

after_install = "ramz_hr.install.after_install"
after_migrate = "ramz_hr.install.after_migrate"

doc_events = {
    "Employee": {
        "validate":     "ramz_hr.countries.saudi.validators.validate_employee",
        "after_insert": "ramz_hr.countries.saudi.leave_types.auto_assign_leave_policy",
    },
    "Salary Structure Assignment": {
        "validate": "ramz_hr.overrides.salary_structure_assignment.validate_basic_percentage",
    },
}

fixtures = [
    {"dt": "Custom Field", "filters": [["module", "=", "Ramz HR"]]},
    {"dt": "Property Setter", "filters": [["module", "=", "Ramz HR"]]},
]
```

- [ ] **Step 3: Migrate, then run the full test suite**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz
bench --site ramzunited clear-cache
bench --site ramzunited migrate
bench --site ramzunited run-tests --app ramz_hr
```
Expected: all tests pass, including:
- `TestInstall` (6 tests, all passing with install via `after_migrate`)
- `TestEmployeeValidators` (12)
- `TestLeaveSetup` + `TestAutoAssignLeavePolicy` (11, including the 2 that were pending from Task 12)
- `TestBasicPercentage` (5)
- `TestCountrySeam` (3)

**Total: ~37 test cases passing.**

- [ ] **Step 4: Commit**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz/apps/ramz_hr
git add ramz_hr/install.py ramz_hr/hooks.py
git commit -m "feat: wire install.py orchestrator + hooks.py (after_install, after_migrate, doc_events)"
```

---

## Task 15: Idempotency verification — migrate twice

**Files:** (no code changes — verification task)

- [ ] **Step 1: Record current seed counts**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz
bench --site ramzunited console <<'PY'
import frappe
print("Leave Types:", frappe.db.count("Leave Type"))
print("Salary Components:", frappe.db.count("Salary Component"))
print("Medical Insurance Class:", frappe.db.count("Medical Insurance Class"))
print("Holiday Lists:", frappe.db.count("Holiday List"))
print("Leave Policies:", frappe.db.count("Leave Policy"))
PY
```
Record the numbers.

- [ ] **Step 2: Migrate again**

```bash
bench --site ramzunited migrate
```
Should complete without errors.

- [ ] **Step 3: Verify counts are unchanged**

```bash
bench --site ramzunited console <<'PY'
import frappe
print("Leave Types:", frappe.db.count("Leave Type"))
print("Salary Components:", frappe.db.count("Salary Component"))
print("Medical Insurance Class:", frappe.db.count("Medical Insurance Class"))
print("Holiday Lists:", frappe.db.count("Holiday List"))
print("Leave Policies:", frappe.db.count("Leave Policy"))
PY
```
Expected: same numbers as Step 1. No duplicates.

- [ ] **Step 4: Run full test suite once more**

```bash
bench --site ramzunited run-tests --app ramz_hr
```
Expected: all tests still pass.

- [ ] **Step 5: Commit a README note (if counts matched — no file changes expected otherwise)**

If all checks pass, this task has no commit. If you found drift, fix the offending seeder's idempotency check, commit, and re-run the task.

---

## Task 16: Update README with install instructions

**Files:**
- Modify: `apps/ramz_hr/README.md`

- [ ] **Step 1: Replace README content**

Overwrite `apps/ramz_hr/README.md`:

```markdown
# Ramz HR

FrappeHR customization for Ramz United — Saudi Arabia HR policy (Phase 1).
Architected for multi-country extension (UAE, Qatar, India as drop-in modules).

## Phase 1 scope

- Employee master fields: Iqama, Contract Type, Probation, Air Ticket, Medical Insurance Class, IBAN
- 11 Leave Types (Annual, Casual, Sick ×3 tiers, Marriage, Paternity, Maternity, Bereavement, Hajj, Unpaid)
- "Ramz Saudi Standard" Leave Policy + Leave Period auto-seeded for current year
- "Saudi Holidays YYYY" Holiday List (National Day, Founding Day, Eid placeholders, Fri/Sat off)
- Salary Components: Basic, Housing Allowance, Transportation Allowance
- "Ramz Saudi Standard" Salary Structure template
- Basic 50–70% validation on Salary Structure Assignment
- Country-abstraction seam ready for UAE/Qatar/India

## Install

```bash
bench get-app https://github.com/exvas/ramz_hr
bench --site <site> install-app ramz_hr
```

## Configuration

All runtime toggles are on the `Ramz HR Settings` Single doctype (Desk → Search "Ramz HR Settings"):

- Country (drives country-module dispatch)
- Auto-assign Leave Policy on Employee create (on/off)
- Basic % min/max bounds (default 50/70)
- Basic % strict mode (throw vs warn)
- Casual Leave default days (PDF range 3–7)
- Iqama expiry reminder days (reserved for Phase 2 scheduler)

## Testing

```bash
bench --site <site> run-tests --app ramz_hr
```

## Roadmap

See [docs/superpowers/specs/](docs/superpowers/specs/) for the full Phase 1 design
and Phase 2–4 roadmap (GOSI + carry-forward, EOSB per Articles 84/85, approval workflow).

## License

MIT
```

- [ ] **Step 2: Commit**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz/apps/ramz_hr
git add README.md
git commit -m "docs: update README with Phase 1 install and configuration"
```

---

## Task 17: Push to GitHub

- [ ] **Step 1: Push all Phase 1 commits**

```bash
cd /Users/sammishthundiyil/frappe-bench-kenz/apps/ramz_hr
git push origin develop
```

- [ ] **Step 2: Verify on GitHub**

Open https://github.com/exvas/ramz_hr/commits/develop and confirm all ~16 commits are present.

---

## Final checklist — Phase 1 shipped

- [ ] `Ramz HR Settings` Single doctype with 10 fields
- [ ] `Medical Insurance Class` lookup doctype + 5 seeded rows
- [ ] 9 custom fields on Employee (+ 3 section breaks + 2 column breaks)
- [ ] 3 property setters (Employee.nationality.reqd, Employee.date_of_joining.reqd, SSA.base.reqd)
- [ ] 11 Leave Types with correct flags (carry_forward, is_lwp, is_ppl, applicable_for_gender, is_earned_leave)
- [ ] "Ramz Saudi Standard" Leave Policy with 10 allocations (Unpaid excluded)
- [ ] "Saudi <YYYY>" Leave Period for current year
- [ ] "Saudi Holidays <YYYY>" Holiday List (Founding Day, National Day, Eid placeholders, Fri+Sat off)
- [ ] 3 Salary Components (Basic, Housing, Transport) + "Ramz Saudi Standard" Structure
- [ ] Employee validators (Iqama format, Iqama expiry presence, IBAN format, probation auto-compute)
- [ ] Salary Structure Assignment Basic% validator (strict/warn toggle)
- [ ] Employee.after_insert auto-assign Leave Policy
- [ ] Country-abstraction seam (`COUNTRY_REGISTRY` + `get_active_country_module()`)
- [ ] install.py + hooks.py wired
- [ ] ~37 test cases passing
- [ ] README updated
- [ ] All commits pushed to `origin/develop`
