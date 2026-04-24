# Ramz HR

FrappeHR customization for Ramz United — Saudi Arabia HR policy (Phase 1).
Architected for multi-country extension (UAE, Qatar, India as drop-in modules).

## Phase 1 scope (delivered)

- Employee master fields: Iqama / National ID, Iqama Expiry, Contract Type, Work Location, Probation, Air Ticket Eligibility, Medical Insurance Class, IBAN
- 11 Leave Types (Annual, Casual, Sick ×3 tiers, Marriage, Paternity, Maternity, Bereavement, Hajj, Unpaid)
- "Ramz Saudi Standard" Leave Policy + Leave Period auto-seeded for current year
- "Saudi Holidays YYYY" Holiday List (National Day, Founding Day, Eid placeholders, Fri + Sat off)
- Salary Components: Basic, Housing Allowance, Transportation Allowance
- "Ramz Saudi Standard" Salary Structure template
- Basic 50–70 % enforcement on Salary Structure Assignment (strict / warn toggle)
- Country-abstraction seam ready for UAE / Qatar / India

## Install

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/exvas/ramz_hr --branch develop
bench --site <site> install-app ramz_hr
```

On install, `ramz_hr` seeds all Phase 1 data (Leave Types, Holiday List, Salary Structure, etc.) and applies Custom Fields + Property Setters to the stock Employee doctype. All seeders are idempotent — subsequent `bench migrate` runs are safe.

## Configuration

All runtime toggles live on the `Ramz HR Settings` Single doctype (Desk → search "Ramz HR Settings"):

| Setting | Purpose | Default |
|---|---|---|
| Country | Drives country-module dispatch | Saudi Arabia |
| Auto-Assign Leave Policy | Creates a Leave Policy Assignment on Employee create | On |
| Default Leave Policy | Which policy to auto-assign | Ramz Saudi Standard |
| Fiscal Year Start Month | Used to seed Leave Period | 1 (January) |
| Casual Leave Days | PDF allows 3–7; configurable within that band | 7 |
| Basic Salary Component | Which Salary Component is "basic" for the 50–70 % rule | Basic |
| Basic % Minimum / Maximum | Allowed range for Basic as a share of gross | 50 / 70 |
| Strict Basic % Enforcement | On = throw on violation; Off = warn only | On |
| Iqama Reminder Days | Lead time for Iqama expiry reminders (Phase 2) | 30 |

## Testing

```bash
bench --site <site> run-tests --app ramz_hr
```

Phase 1 ships 41 tests across 5 test modules (install, employee validators, leave setup, basic %, country seam).

## Architecture

- Country-specific logic lives under `ramz_hr/countries/<country>/` (Saudi is the only populated country in Phase 1).
- `ramz_hr/countries/__init__.py` exposes `COUNTRY_REGISTRY` + `get_active_country_module()`.
- `ramz_hr/install.py` orchestrates idempotent setup on `after_install` and `after_migrate`.
- `ramz_hr/overrides/salary_structure_assignment.py` contains the Basic % validator wired via `doc_events`.

To add a new country (UAE / Qatar / India) later:

1. Drop `ramz_hr/countries/<country>/` with a `setup()` aggregator and the 5 sub-modules (`custom_fields`, `medical_insurance_class`, `holidays`, `salary_components`, `leave_types`).
2. Add an entry to `COUNTRY_REGISTRY` in `ramz_hr/countries/__init__.py`.
3. On the target site, set `Ramz HR Settings.country = "<Country Name>"` and run `bench migrate`.

Saudi code and data are untouched by each addition.

## Roadmap

- **Phase 2:** GOSI contributions (Saudi 10 % / 12 %, Expat employer-only 2 %), leave carry-forward rollover, leave encashment, Iqama expiry scheduler, 21 → 30 day tenure-based Annual Leave bump, Marriage/Paternity/Hajj validators.
- **Phase 3:** EOSB auto-calculation per Saudi Labour Law Articles 84 / 85, monthly EOSB accrual Journal Entries.
- **Phase 4:** 4-level approval workflow (Immediate Supervisor → HR Manager → Finance → CEO) via Frappe Workflow + Approval Matrix child table.

See [docs/superpowers/specs/](docs/superpowers/specs/) for the full design document and [docs/superpowers/plans/](docs/superpowers/plans/) for the Phase 1 implementation plan.

## Contributing

This app uses `pre-commit` for code formatting and linting:

```bash
cd apps/ramz_hr
pre-commit install
```

Tools: ruff, eslint, prettier, pyupgrade.

## License

MIT
