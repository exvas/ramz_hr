# Ramz HR — Phase 1 (Saudi) Design & Multi-Country Roadmap

**Client:** Ramz United
**App:** `ramz_hr` (fresh scaffold on `frappe-bench-kenz`)
**Target bench apps:** `frappe`, `erpnext`, `hrms` (stock HRMS v15+)
**Date:** 2026-04-24
**Author:** Sammish Thundiyil (design via Claude Code brainstorming session)
**Source document:** `Downloads/HR_Policy_Document.pdf` (Ramz United HR Policy Manual, 4 pages)

---

## 1. Context & Scope

### 1.1 Why

Ramz United requires a FrappeHR customization covering Saudi labour law and company policy: leave entitlements, EOSB (End of Service Benefits) per Articles 84/85, GOSI contributions, salary structure rules, and Saudi-specific employee master fields.

The customization must be packaged as a **single app** that can later be extended to **UAE, Qatar, and India** — with each country running on its own Frappe site.

### 1.2 Scope of this document

- **Phase 1 (this spec, detailed design):** Employee master fields, Leave Types & Saudi Holidays, Salary Structure (basic 50–70% rule).
- **Phases 2–4 (roadmap summary only):** GOSI + leave carry-forward, EOSB, approval workflow. Each gets its own spec when started.

### 1.3 Decisions already taken (closed via brainstorming dialogue)

| # | Decision | Rationale |
|---|---|---|
| D1 | **Saudi-first**, other countries later, with country-module seams from day 1. | PDF is Saudi-only and detailed; over-abstracting now risks wrong seams. |
| D2 | **Independent app** — do not depend on or fork `string_it_hr` (that app is a different UAE client's project). Crib **structural patterns** only. | Avoid entangling two clients' codebases. |
| D3 | **Separate Frappe site per country.** No runtime country switching. | Matches client's existing deployment model. |
| D4 | **Approval workflow deferred to Phase 4.** Current phases focus on data model, seed data, and calculations. | Client wants customization first, approvals last. |
| D5 | **Phase ordering:** 1 = Employee fields + Leaves + Salary | 2 = GOSI + Carry-forward | 3 = EOSB | 4 = Approval workflow. | Dependency order: later phases need fields/salary structure to exist. |
| D6 | **No Arabic / RTL UI.** English labels only in Phase 1. | Client preference. |
| D7 | **Architecture: Approach A** (Custom Fields via fixtures + country module folders + seed scripts). Rejected doctype overrides (fragile on HRMS upgrades) and pure-config-only (too much manual admin work). | Upgrade-safe, idiomatic to Frappe, easy handoff. |

### 1.4 Non-goals (Phase 1)

- No GOSI salary components or employer contribution logic.
- No EOSB auto-calculation.
- No leave carry-forward rollover job, encashment payout, or tenure-based leave bump (21 → 30 days at 5 years).
- No multi-level approval workflow. No workflow doctype wiring.
- No custom UI / Desk pages / web views.
- No Arabic translations.
- No override of stock HRMS doctype classes.
- No destructive deletion of seeded data on uninstall.

---

## 2. Architecture

### 2.1 App layout

```
ramz_hr/
├── hooks.py                         # fixtures, doc_events, scheduler_events, after_install/after_migrate
├── install.py                       # country-agnostic orchestrator
├── ramz_hr/
│   ├── doctype/
│   │   ├── ramz_hr_settings/        # Single doctype: country, basic_pct_min/max, toggles, defaults
│   │   └── medical_insurance_class/ # tiny lookup doctype (name-only)
│   ├── custom_fields.py             # country-neutral custom fields (empty in Phase 1, reserved)
│   └── property_setters.py          # country-neutral property setters (empty in Phase 1, reserved)
├── countries/
│   ├── __init__.py                  # COUNTRY_REGISTRY + get_active_country_module()
│   └── saudi/
│       ├── __init__.py              # setup() aggregator
│       ├── custom_fields.py         # Saudi Employee/Company custom fields + property setters
│       ├── validators.py            # Employee.validate handlers (Iqama, IBAN, probation)
│       ├── holidays.py              # seed "Saudi Holidays <YYYY>"
│       ├── leave_types.py           # seed 11 Leave Types + Leave Policy + Leave Period
│       ├── salary_components.py     # seed Basic/Housing/Transport + "Ramz Saudi Standard" structure
│       └── medical_insurance_class.py  # seed VIP/A+/A/B/C
├── overrides/
│   ├── __init__.py
│   └── salary_structure_assignment.py   # basic% validator
├── tests/
│   ├── test_install.py
│   ├── test_employee_validators.py
│   ├── test_leave_setup.py
│   ├── test_basic_pct.py
│   └── test_country_seam.py
├── patches.txt
└── docs/superpowers/specs/          # this document
```

### 2.2 The country-abstraction seam

`ramz_hr/countries/__init__.py`:

```python
import importlib
import frappe

COUNTRY_REGISTRY = {
    "Saudi Arabia": "ramz_hr.countries.saudi",
    # Added later as each country's rules are specified:
    # "United Arab Emirates": "ramz_hr.countries.uae",
    # "Qatar":                "ramz_hr.countries.qatar",
    # "India":                "ramz_hr.countries.india",
}


def get_active_country_module():
    country = frappe.db.get_single_value("Ramz HR Settings", "country") or "Saudi Arabia"
    if country not in COUNTRY_REGISTRY:
        frappe.throw(
            f"Country '{country}' is not implemented in ramz_hr yet. "
            f"Supported: {list(COUNTRY_REGISTRY)}"
        )
    return importlib.import_module(COUNTRY_REGISTRY[country])
```

Each country module exposes **one contract**: a `setup()` function that seeds everything for that country (fields, holidays, leave types, salary components, lookups). `install.py` calls it generically — it does not import Saudi code directly.

**To add a new country later:**
1. Drop `countries/<name>/` folder with the same 5–6 modules + `__init__.py::setup()` aggregator.
2. Add an entry to `COUNTRY_REGISTRY`.
3. On the target site, set `Ramz HR Settings.country = "<Country Name>"`.
4. Run `bench migrate`. Zero changes to other countries' code or data.

### 2.3 Install / migrate flow

`ramz_hr/install.py::after_install()` and `::after_migrate()` run the same idempotent sequence:

```
1.  Ensure "Ramz HR Settings" Single doc exists → seed defaults only for blank fields
    (never overwrite admin-set values).
2.  Sync country-neutral custom fields + property setters (empty in Phase 1).
3.  Resolve active country module via get_active_country_module().
4.  Call country_module.setup(), which in order:
      4a. custom_fields.setup()             → Employee custom fields + property setters
      4b. medical_insurance_class.setup()   → seed 5 default classes
      4c. holidays.setup()                  → seed "Saudi Holidays <current-year>" Holiday List
      4d. salary_components.setup()         → Basic/Housing/Transport + "Ramz Saudi Standard" structure
      4e. leave_types.setup()               → 11 Leave Types + Leave Policy + Leave Period
5.  frappe.db.commit().
6.  Log summary (created vs existed counts).
```

### 2.4 Idempotency contract (all seed functions)

- Existence check before insert — never duplicates.
- On existing records: patch **only blank fields** with defaults; never overwrite admin-modified values.
- Flag drift on existing records (e.g., a Leave Type has `is_lwp` changed by admin) → log a warning, do not reset.
- Deprecation: a `DEPRECATED_RECORDS` list per seeder. Records on the list are removed on migrate **only if no FK references exist**.
- Tolerant of partial previous runs — any step can be re-entered safely.

---

## 3. Phase 1 detailed design

### 3.1 `Ramz HR Settings` (Single doctype)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `country` | Select (`Saudi Arabia`) | Saudi Arabia | Drives country module dispatch. Select options expand as countries are added. |
| `auto_assign_leave_policy` | Check | 1 | Toggles Employee.after_insert auto-assignment hook. |
| `default_leave_policy` | Link → Leave Policy | Ramz Saudi Standard | Which policy to auto-assign. |
| `fiscal_year_start_month` | Int | 1 | Leave Period seeding. |
| `casual_leave_days` | Int | 7 | PDF allows 3–7; configurable within band. |
| `basic_salary_component` | Link → Salary Component | Basic | Tells the Basic% validator which component is "basic". |
| `basic_pct_min` | Float | 50 | Lower bound for basic% validation. |
| `basic_pct_max` | Float | 70 | Upper bound. |
| `basic_pct_strict` | Check | 1 | 1 = throw on violation, 0 = msgprint warning. |
| `iqama_reminder_days` | Int | 30 | Reserved — used in Phase 2 for Iqama expiry scheduler. |

### 3.2 Employee master fields (Saudi)

**New section: "Saudi Employment Details"**

| Fieldname | Label | Type | Reqd | Validation |
|---|---|---|---|---|
| `custom_iqama_number` | Iqama / National ID | Data | — | 10 digits when set. |
| `custom_iqama_expiry` | Iqama Expiry | Date | Yes if `nationality != "Saudi Arabia"` | Must be in the future at Employee creation; warn (not block) on updates. |
| `custom_contract_type` | Contract Type | Select (`\nLimited\nUnlimited`) | Yes | Used by Phase 3 EOSB formula. |
| `custom_work_location` | Work Location | Data | No | Free text in Phase 1. |
| `custom_probation_period_days` | Probation Period (Days) | Int | No | 0–180. Default 90. |
| `custom_probation_end_date` | Probation End Date | Date | No (auto) | Read-only. Auto = `date_of_joining + custom_probation_period_days`. |

**New section: "Benefits & Entitlements"**

| Fieldname | Label | Type | Notes |
|---|---|---|---|
| `custom_air_ticket_eligibility` | Air Ticket Eligibility | Select (`\nNone\nAnnual\nBiennial`) | — |
| `custom_medical_insurance_class` | Medical Insurance Class | Link → Medical Insurance Class | Dropdown; prevents free-text drift. |

**New section: "Saudi Payroll Info"**

| Fieldname | Label | Type | Validation |
|---|---|---|---|
| `custom_iban` | IBAN | Data | `^SA\d{22}$` when set. |

**Property setters on stock Employee fields:**

| Target | Change | Rationale |
|---|---|---|
| `Employee.nationality` | `reqd = 1` | EOSB/GOSI formulas branch on nationality. |
| `Employee.date_of_joining` | `reqd = 1` | EOSB service-period math. |

**`doc_events.Employee.validate`** → `ramz_hr.countries.saudi.validators.validate_employee` handles all five checks:

1. Iqama format (10 digits).
2. Iqama expiry presence when non-Saudi.
3. Iqama expiry sanity (future at create, warn if past on update).
4. IBAN format.
5. Probation end auto-compute.

### 3.3 Medical Insurance Class (new lookup doctype)

- One field: `class_name` (Data, unique).
- Autoname by field.
- Seeded on install: `VIP`, `A+`, `A`, `B`, `C`.
- Admin can add/remove via UI.

### 3.4 Leave Types (11 records)

One `Leave Type` per row. Sick leave is intentionally split 3-way — see §3.4.1.

| # | Name | Default Days | `is_carry_forward` | `is_lwp` | `is_ppl` | `fraction_of_daily_salary_per_leave` | `applicable_for_gender` | `is_earned_leave` + `earned_leave_frequency` |
|---|---|---|---|---|---|---|---|---|
| 1 | Annual Leave | 21 | 1 (`max_carry_forwarded_leaves=21`) | 0 | 0 | — | — | 1, Monthly |
| 2 | Casual Leave | 7 | 0 | 0 | 0 | — | — | 0 |
| 3 | Sick Leave - Full Pay | 30 | 0 | 0 | 0 | — | — | 0 |
| 4 | Sick Leave - 75% | 60 | 0 | 0 | 1 | 0.75 | — | 0 |
| 5 | Sick Leave - Unpaid | 30 | 0 | 1 | 0 | — | — | 0 |
| 6 | Marriage Leave | 5 | 0 | 0 | 0 | — | — | 0 |
| 7 | Paternity Leave | 3 | 0 | 0 | 0 | — | Male | 0 |
| 8 | Maternity Leave | 70 | 0 | 0 | 0 | — | Female | 0 |
| 9 | Bereavement Leave | 5 | 0 | 0 | 0 | — | — | 0 |
| 10 | Hajj Leave | 15 | 0 | 0 | 0 | — | — | 0 |
| 11 | Unpaid Leave | 0 | 0 | 1 | 0 | — | — | 0 |

Annual Leave is encashable (`allow_encashment=1`); the encashment component wiring is Phase 2.

#### 3.4.1 Rationale for 3-way sick leave split

PDF: *"30 days full pay, 60 days at 75%, 30 days unpaid."* Stock HRMS `is_ppl` supports a single `fraction_of_daily_salary_per_leave` per Leave Type, not tiered pay-rate. Options considered:

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Split into 3 Leave Types (chosen) | Simple, no custom payroll math, employees see progression, common KSA pattern. | 3 balances on the Leave UI instead of 1. | ✅ Phase 1. |
| Single "Sick Leave" + custom payroll hook reading cumulative days | 1 balance, elegant. | Custom payroll math, hidden progression. | ❌ Not Phase 1. Candidate for Phase 2 refactor if client prefers. |

### 3.5 Leave Policy: "Ramz Saudi Standard"

One seeded `Leave Policy` doc with 10 allocatable types (Unpaid excluded — on-request only):

```
Annual Leave: 21
Casual Leave: 7
Sick Leave - Full Pay: 30
Sick Leave - 75%: 60
Sick Leave - Unpaid: 30
Marriage Leave: 5
Paternity Leave: 3
Maternity Leave: 70
Bereavement Leave: 5
Hajj Leave: 15
```

Wired via `doc_events.Employee.after_insert` → `ramz_hr.countries.saudi.leave_types.auto_assign_leave_policy`. Only runs if `Ramz HR Settings.auto_assign_leave_policy == 1`. Creates a `Leave Policy Assignment` using the active `Leave Period`.

### 3.6 Leave Period

Seeded per fiscal year: `from_date = <YYYY>-01-01`, `to_date = <YYYY>-12-31`, starting month configurable via `fiscal_year_start_month`. Installer seeds the current year only. Phase 2 rollover job seeds next year in December.

### 3.7 Holiday List: "Saudi Holidays <YYYY>"

Seeded via `ramz_hr/countries/saudi/holidays.py`:

**Fixed Gregorian holidays:**
- Saudi Founding Day — Feb 22
- Saudi National Day — Sep 23

**Hijri-calculated placeholders** (best-effort Gregorian approximation for the install year):
- Eid Al-Fitr — 3 days
- Eid Al-Adha — 4 days

Admin is expected to correct Eid dates each year once the Ministry of Human Resources announces them. Install log emits a warning with the expected admin action.

**Option considered:** compute Hijri-to-Gregorian via a `hijri-converter` Python package. **Rejected** because Saudi announces official dates based on moon sighting (not astronomical calc), and the admin override is a once-per-year task.

**Weekly off:** Friday + Saturday (Saudi standard weekend since 2013) via Frappe's `get_weekly_off_date_list`.

Holiday List is linked to the Company in `after_install` only if the Company has no `default_holiday_list` set; never overwrites an existing one.

### 3.8 Salary Components (3 in Phase 1)

| Component | Abbr | Type | `depends_on_payment_days` | `amount_based_on_formula` |
|---|---|---|---|---|
| Basic | BASIC | Earning | 1 | 0 |
| Housing Allowance | HRA | Earning | 1 | 0 |
| Transportation Allowance | TA | Earning | 1 | 0 |

**Deliberately excluded from Phase 1:** Food Allowance, Other Allowance, Absence Deduction, Loan/Advance, Penalty, GOSI (employee + employer), EOSB accrual. Each is added when its logic ships (Phases 2–3). This keeps the Phase 1 Salary Slip honest — no zero-rows for features that don't work yet.

### 3.9 Salary Structure: "Ramz Saudi Standard"

- `is_active = 1`, `company = None` (global template).
- Earnings rows: Basic, Housing Allowance, Transportation Allowance. No formulas, no amounts — filled per employee in the Salary Structure Assignment.
- Deductions rows: empty in Phase 1 (GOSI joins in Phase 2).

### 3.10 Basic % validator

**Trigger:** `doc_events.Salary Structure Assignment.validate` → `ramz_hr.overrides.salary_structure_assignment.validate_basic_percentage`.

**Logic:**

```
settings = frappe.get_single("Ramz HR Settings")
basic_component = settings.basic_salary_component       # default: "Basic"
earnings = resolve_earnings(salary_structure, assignment.base)
basic_amount = earnings[basic_component]
gross = sum(earnings.values())
pct = basic_amount / gross * 100
if pct < settings.basic_pct_min or pct > settings.basic_pct_max:
    msg = f"Basic must be between {settings.basic_pct_min}% and {settings.basic_pct_max}% of gross (currently {pct:.2f}%)"
    if settings.basic_pct_strict:
        frappe.throw(msg)
    else:
        frappe.msgprint(msg, alert=True)
```

**`resolve_earnings()`** reuses HRMS's own `Salary Structure.get_data_for_eval()` and row-evaluation helpers — we do not re-implement payroll math.

**Property setter:** `Salary Structure Assignment.base.reqd = 1`. Without `base`, the validator has no anchor.

### 3.11 `doc_events` summary (Phase 1)

```python
doc_events = {
    "Employee": {
        "validate":     "ramz_hr.countries.saudi.validators.validate_employee",
        "after_insert": "ramz_hr.countries.saudi.leave_types.auto_assign_leave_policy",
    },
    "Salary Structure Assignment": {
        "validate": "ramz_hr.overrides.salary_structure_assignment.validate_basic_percentage",
    },
}
```

No `scheduler_events` in Phase 1. Those arrive with Phase 2 (Iqama expiry reminders, leave rollover).

---

## 4. Testing (Phase 1)

Run via `bench --site <site> run-tests --app ramz_hr`.

### 4.1 `test_install.py` — install correctness + idempotency
- Fresh install → asserts all seeded records exist with correct flags (11 Leave Types, 1 Leave Policy, 1 Leave Period, 1 Holiday List with Saudi National Day & Founding Day, 3 Salary Components, 1 Salary Structure, 5 Medical Insurance Class rows, `Ramz HR Settings` with defaults).
- `after_migrate()` run twice → no duplicates, no errors, no overwrites of admin-modified records.

### 4.2 `test_employee_validators.py`
- Saudi employee without valid Iqama format → fails.
- Non-Saudi employee without `custom_iqama_expiry` → fails.
- Invalid IBAN (`SA12` etc.) → fails; valid (`SA` + 22 digits) → passes.
- `date_of_joining=2026-01-01` + `custom_probation_period_days=90` → `custom_probation_end_date == 2026-04-01`.

### 4.3 `test_leave_setup.py`
- `auto_assign_leave_policy = 1` → new Employee gets a `Leave Policy Assignment`.
- `auto_assign_leave_policy = 0` → no assignment.
- `Leave Policy Assignment` uses the Saudi `Leave Period` and "Ramz Saudi Standard" policy.
- Allocations match §3.5 totals.

### 4.4 `test_basic_pct.py`
- Base=6000, Housing=2000, Transport=500 → Basic = 70.5% → **throws**.
- Base=5500, Housing=2000, Transport=500 → Basic = 68.75% → **passes**.
- `basic_pct_strict = 0` → violation becomes msgprint warning, document saves.

### 4.5 `test_country_seam.py`
- Register a temporary `countries/_test_fake/` with its own minimal `setup()`.
- Flip `Ramz HR Settings.country = "Fake"`.
- Run `after_migrate()` → fake's setup called, Saudi's not re-run.
- Proves the dispatch seam works before we actually ship UAE/Qatar/India.

---

## 5. Patterns reused from `string_it_hr`

`string_it_hr` is a UAE-specific HR extension on this bench for a different client. We do **not** depend on it, but we crib the following structural patterns (the "chassis"):

| Reused | From | Adaptation |
|---|---|---|
| `install.py` structure (`_sync_custom_fields`, `_sync_property_setters`, `_remove_deprecated`, `_seed_settings_defaults`) wired to both `after_install` and `after_migrate` | `string_it_hr/install.py` | Rename `Real Taste Settings` → `Ramz HR Settings`; add country-module dispatch after core sync. |
| `custom_fields.py` shape: `CUSTOM_FIELDS` dict + `PROPERTY_SETTERS` list + `DEPRECATED_FIELDS` list | `string_it_hr/custom_fields.py` | Field list rewritten for Saudi (Iqama, not Emirates ID). |
| `hooks.py` layout: `fixtures` / `doc_events` / `after_install` / `after_migrate` / `scheduler_events` | `string_it_hr/hooks.py` | Copy skeleton; Phase 1 content only. |
| `Employee.after_insert` → auto-assign leave policy | `string_it_hr.leave_setup.auto_assign_leave_policy` | Same hook, assigns the Saudi policy instead. |
| "Fill blanks only" settings defaults pattern | `string_it_hr.install._seed_settings_defaults` | Adopted as the idempotency contract across all seeders. |
| Monthly accrual job skeleton (title-keyed idempotent Journal Entry) | `string_it_hr/gratuity.py::monthly_gratuity_accrual` | Reused as the **shape** for Phase 3 Saudi EOSB job. Phase 1 does not ship this. |

**Not reused (UAE-specific content):** `custom_emirates_id`, `custom_labour_card_no`, `custom_labour_card_expiry`, `custom_visa_expiry`, UAE IBAN format, `custom_employer_eid`, UAE gratuity formula (21/30 days), `gratuity_exclude_uae_nationals` concept.

---

## 6. Roadmap — Phases 2, 3, 4 (summary)

Each phase gets its own spec when started.

### Phase 2 — GOSI + Leave Carry-forward (next)

- **New Employee fields:** `custom_gosi_category` (Select: Saudi National / Expat / Exempt), `custom_gosi_applicable` (auto from category), `custom_overtime_policy` (Link to new Overtime Policy doctype).
- **New Salary Components:** GOSI Employee Deduction (9% pension + 1% SANED → 10% total), GOSI Employer Contribution Type (12% Saudi / 2% expat).
- **New Salary Structure rows:** GOSI deduction, formula-driven from `custom_gosi_category`.
- **Scheduler jobs:**
  - Daily: Iqama expiry reminder (uses `iqama_reminder_days` setting already in Phase 1).
  - Monthly: Annual Leave earned-leave accrual (stock HRMS handles the math; we just ensure the policy is active).
  - Yearly (Dec): Carry-forward rollover — transfer unused Annual Leave into next year's allocation up to `max_carry_forwarded_leaves`; trigger leave encashment for balance above carry limit.
- **21 → 30 days tenure bump:** scheduler evaluates each Saudi employee's tenure at Leave Period start; if ≥5 years, bumps Annual allocation to 30.
- **Leave validators:** Marriage "once per event" (tracks completed marriage leaves on Employee); Paternity "within 7 days of birth"; Hajj "once in service".

### Phase 3 — EOSB

- **New Employee fields:** `custom_exit_reason` (Select: Employer Termination / Resignation / Contract End), `custom_last_basic_salary` (auto-snapshot at exit).
- **New doctype:** `EOSB Calculation` — captures: joining date, exit date, exit reason, contract type, last basic, last basic+fixed-allowances ("actual wage"), years of service, employer-termination entitlement (Article 84 formula), resignation reduction factor (Article 85), final payable.
- **Formulas** (implemented in `ramz_hr/countries/saudi/eosb.py`):
  - Article 84: first 5 years × ½ month × actual wage + subsequent years × 1 month × actual wage, pro-rated per-day.
  - Article 85 reductions on resignation: <2y → 0 ; 2–5y → 1/3 ; 5–10y → 2/3 ; 10+ → 1.
- **Monthly EOSB accrual** (scaffold adapted from `string_it_hr/gratuity.py`): Dr EOSB Expense / Cr EOSB Payable, idempotent by period.
- **Full & Final Settlement:** integrates with stock HRMS `Full and Final Statement` + the `EOSB Calculation`.

### Phase 4 — Approval workflow

- **Hybrid approach** (Frappe Workflow + Approval Matrix child table):
  - Frappe `Workflow` doctype with states: Draft → Supervisor Approved → HR Manager Approved → Finance Approved → CEO Approved → Posted.
  - New child doctype `Ramz Approval Matrix` attached to each approved doctype (Leave Application, EOSB Calculation, Salary Structure Assignment) — names the 4 specific approvers (overrides role-based defaults per employee/department).
  - New single doctype `Ramz Approval Rules`: matrix of (doctype × transaction-amount-threshold × required-levels), e.g., "casual leave ≤ 2 days → skip CEO".
- **Notifications:** email + desk notification at each state transition.
- **Audit log:** stock Frappe `Version` table is sufficient; optional `Ramz Approval Log` doctype for richer reporting.

### Adding UAE / Qatar / India later

For each new country (triggered when the client provides their country's HR policy details):

1. Create `countries/<country>/` with the 5 seeders (custom_fields, lookups, holidays, leave_types, salary_components) + `__init__.py::setup()`.
2. Add entry to `COUNTRY_REGISTRY`.
3. Install on the country's Frappe site with `Ramz HR Settings.country = "<Country Name>"`.
4. Extend existing doctypes (EOSB Calculation, Approval Rules, etc.) with country-specific formula branches if needed.

Saudi code and data are untouched by each addition.

---

## 7. Deliverables checklist (Phase 1)

- [ ] `Ramz HR Settings` Single doctype (10 fields per §3.1)
- [ ] `Medical Insurance Class` lookup doctype + 5 seeded rows
- [ ] 9 custom fields on Employee, 3 property setters on Employee / Salary Structure Assignment
- [ ] 11 Leave Types seeded with correct flags
- [ ] "Ramz Saudi Standard" Leave Policy with 10 allocations
- [ ] Saudi Leave Period (current fiscal year)
- [ ] "Saudi Holidays <YYYY>" Holiday List with National Day, Founding Day, Eid placeholders, Fri/Sat weekly off
- [ ] 3 Salary Components: Basic, Housing, Transport
- [ ] "Ramz Saudi Standard" Salary Structure
- [ ] 5 Employee validators (Iqama format, Iqama expiry presence, IBAN format, probation auto-compute, probation bounds)
- [ ] Salary Structure Assignment basic% validator (strict/warn toggle)
- [ ] Employee.after_insert auto-assign Leave Policy (toggleable)
- [ ] `install.py` + `hooks.py` + country dispatch
- [ ] 5 test files, ~15 test cases
- [ ] `README.md` update with install instructions

---

## 8. Open items / assumptions flagged for client confirmation

| # | Item | Assumption | Action if wrong |
|---|---|---|---|
| A1 | Casual leave default — PDF says "3–7 days" | Default to 7 (upper bound), configurable via `Ramz HR Settings.casual_leave_days`. | Change the setting default; no code change. |
| A2 | Saudi weekend is Friday + Saturday | Standard since 2013; applies to Ramz United. | Change `holidays.py` weekly_off; 1-line change. |
| A3 | Eid date accuracy | Placeholder Gregorian dates seeded, admin corrects after Ministry announcement. | Manual edit of Holiday List; no code change. |
| A4 | Which salary component counts as "Basic" for the 50–70% rule | Configured via `Ramz HR Settings.basic_salary_component = "Basic"`; can be changed if client renames. | Admin edits the setting. |
| A5 | Gender-restricted leave types (Paternity/Maternity) | Enforced via stock HRMS `applicable_for_gender`. | None — HRMS handles it. |
| A6 | Uninstall behavior | Conservative — seeded data stays in place. | Explicit cleanup scripts if client ever wants a clean teardown. |

---

## 9. References

- Saudi Labour Law (Royal Decree No. M/51): Articles 84 (EOSB base), 85 (resignation reductions), 109–113 (leave entitlements).
- Stock HRMS docs: Leave Type, Leave Policy, Leave Period, Salary Structure, Salary Structure Assignment, Holiday List.
- `string_it_hr` source (structural patterns only): `/apps/string_it_hr/string_it_hr/{install,hooks,custom_fields,gratuity,leave_setup,salary_setup}.py`.
