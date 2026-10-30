# Decisions (ADRs)

Every design decision of the app, one file each, in the order they were made. Each file
says where the decision came from, what was decided (the text as recorded), which tests check
it and which code cites it. **A decision here wins over any other text in the docs.** Later
decisions that change an earlier one say so, and the earlier file links to them.

New decision: copy the shape of the latest file, take the next number (D-175, …), add a row
below. File names are padded (`D-001-…`) so they sort; the ID itself is written as the code
and the guide write it (D-01 … D-174).

| ID | Decision | Area | From | Status |
|---|---|---|---|---|
| [D-01](D-001-test-all-sh.md) | test_all.sh | Setup | Decisions log after the spec review | Accepted |
| [D-02](D-002-custom-usermanager-with-email-login.md) | Custom UserManager with email login | Setup | Decisions log after the spec review | Accepted |
| [D-03](D-003-add-django-allowed-hosts-to-env-example.md) | Add DJANGO_ALLOWED_HOSTS to .env.example (default 127.0.0.1,localhost). | Setup | Decisions log after the spec review | Accepted |
| [D-04](D-004-every-app-uses-a-services-package.md) | Every app uses a services package | Setup | Decisions log after the spec review | Accepted |
| [D-05](D-005-git.md) | Git | Setup | Decisions log after the spec review | Accepted |
| [D-06](D-006-only-submitted-weeks-can-be-approved.md) | Only SUBMITTED weeks can be approved | Timesheet status | Decisions log after the spec review | Updated later |
| [D-07](D-007-reject-sets-both-weeks-to-reopened-with.md) | Reject sets both weeks to REOPENED with reopen_until set per D-21. | Timesheet status | Decisions log after the spec review | Accepted |
| [D-08](D-008-when-a-reopen-window-unlock-or-reject.md) | When a reopen window (unlock or reject, length per D-21) ends without resubmission,… | Timesheet status | Decisions log after the spec review | Updated later |
| [D-09](D-009-the-saturday-12-00-deadline-is-intended.md) | The Saturday 12:00 deadline is intended | Timesheet status | Decisions log after the spec review | Accepted |
| [D-10](D-010-periodapproval-is-the-source-of-truth.md) | PeriodApproval is the source of truth | Timesheet status | Decisions log after the spec review | Accepted |
| [D-11](D-011-nobody-can-ever-approve-their-own-timesheet.md) | Nobody can ever approve their own timesheet | Roles | Decisions log after the spec review | Accepted |
| [D-12](D-012-roles-add-up.md) | Roles add up | Roles | Decisions log after the spec review | Accepted |
| [D-13](D-013-keep-user-is-staff-and-is-superuser.md) | Keep User.is_staff and is_superuser in sync with Employee.is_admin, and User.is_active… | Roles | Decisions log after the spec review | Accepted |
| [D-14](D-014-auditlog-actor-becomes-nullable-plus-a-new.md) | AuditLog.actor becomes nullable, plus a new field system_actor (e.g | Audit | Decisions log after the spec review | Accepted |
| [D-15](D-015-append-only-means-snapshot-and-hours-fields.md) | "Append-only" means snapshot and hours fields never change after creation | Payroll | Decisions log after the spec review | Accepted |
| [D-16](D-016-new-catalogued-tests-continue-as-t-43.md) | New catalogued tests continue as T-43, T-44, … and are added to the B.11 table in the… | Tests | Decisions log after the spec review | Accepted |
| [D-17](D-017-every-catalogued-test-s-docstring-starts-with.md) | Every catalogued test's docstring starts with its ID, e.g | Tests | Decisions log after the spec review | Accepted |
| [D-18](D-018-project-entries-must-have-an-active-project.md) | PROJECT entries must have an active project | Data | Decisions log after the spec review | Accepted |
| [D-19](D-019-add-employee-end-date-nullable-set-on.md) | Add Employee.end_date (nullable, set on deactivation) | Data | Decisions log after the spec review | Accepted |
| [D-20](D-020-employee-email-is-the-source-of-truth.md) | Employee.email is the source of truth | Data | Decisions log after the spec review | Accepted |
| [D-21](D-021-reopen-window.md) | Reopen window | Timesheet status | Decisions log after the spec review | Accepted |
| [D-22](D-022-auditlog-actions-full-list.md) | AuditLog actions (full list) | Audit | Decisions log after the spec review | Accepted |
| [D-23](D-023-createsuperuser-refuses-employees-whose-is-admin-is.md) | createsuperuser refuses employees whose is_admin is off (in addition to unknown, not… | Setup | Version 1 (Phases 1–12) | Accepted |
| [D-24](D-024-until-phase-3-is-a-public-static.md) | Until Phase 3, / is a public static placeholder page that shows no data | Setup | Version 1 (Phases 1–12) | Accepted |
| [D-25](D-025-week-start-for-deadline-for-and-pay.md) | week_start_for, deadline_for and pay_period_for are built in Phase 2 (seed_demo needs… | Setup | Version 1 (Phases 1–12) | Accepted |
| [D-26](D-026-until-phase-11-django-admin-is-view.md) | Until Phase 11, Django Admin is view-only for every model (passwords shown only as a… | Setup | Version 1 (Phases 1–12) | Accepted |
| [D-27](D-027-seed-history-is-aligned-to-pay-periods.md) | Seed history is aligned to pay periods | Data | Version 1 (Phases 1–12) | Accepted |
| [D-28](D-028-django-axes-locks-by-account-email.md) | django-axes locks by account (email) | Login | Version 1 (Phases 1–12) | Accepted |
| [D-29](D-029-there-is-one-login-page-login-admin.md) | There is one login page, /login/. /admin/login/ redirects there (keeping ?next=) | Login | Version 1 (Phases 1–12) | Updated later |
| [D-30](D-030-menu-items-for-pages-built-in-later.md) | Menu items for pages built in later phases (Timesheets, Requests, Team, Approvals,… | Layout | Version 1 (Phases 1–12) | Accepted |
| [D-31](D-031-admins-see-team-everyone-and-approvals-their.md) | Admins see Team (everyone) and Approvals (their direct reports plus employees with no… | Roles | Version 1 (Phases 1–12) | Accepted |
| [D-32](D-032-submitting-requires-at-least-one-entry-add.md) | Submitting requires at least one entry ("Add at least one entry before submitting") | Timesheet | Version 1 (Phases 1–12) | Accepted |
| [D-33](D-033-employees-can-open-only-the-current-week.md) | Employees can open only the current week and earlier weeks | Timesheet | Version 1 (Phases 1–12) | Accepted |
| [D-34](D-034-locked-and-missed-are-worked-out-when.md) | LOCKED and "missed" are worked out when read (effective_status, week_state) | Timesheet | Version 1 (Phases 1–12) | Accepted |
| [D-35](D-035-unlimited-rows.md) | Unlimited rows | Timesheet | Version 1 (Phases 1–12) | Accepted |
| [D-36](D-036-every-row-has-a-date-category-project.md) | Every row has a date, category, project (Project work only, D-18) and a required… | Timesheet | Version 1 (Phases 1–12) | Updated later |
| [D-37](D-037-work-rows-project-work-meetings-training-other.md) | Work rows (Project work, Meetings, Training, Other) and Break rows have a start and… | Timesheet | Version 1 (Phases 1–12) | Accepted |
| [D-38](D-038-rows-with-times-on-the-same-day.md) | Rows with times on the same day must not overlap, breaks included | Timesheet | Version 1 (Phases 1–12) | Accepted |
| [D-39](D-039-new-category-break-break-time.md) | New category BREAK ("Break time") | Timesheet | Version 1 (Phases 1–12) | Accepted |
| [D-40](D-040-leave-rows-pto-sick-holiday-have-hours.md) | Leave rows (PTO, Sick, Holiday) have hours only, without start or end times. | Timesheet | Version 1 (Phases 1–12) | Accepted |
| [D-41](D-041-hours-worked-the-sum-of-work-rows.md) | Hours worked = the sum of work rows, excluding Break and leave | Timesheet | Version 1 (Phases 1–12) | Accepted |
| [D-42](D-042-the-24-hour-limit-per-day-counts.md) | The 24-hour limit per day counts work, Break and leave rows together. | Timesheet | Version 1 (Phases 1–12) | Accepted |
| [D-43](D-043-d-32-stays-and-a-week-containing.md) | D-32 stays, and a week containing only Break rows cannot be submitted either. | Timesheet | Version 1 (Phases 1–12) | Accepted |
| [D-44](D-044-timeentry-gets-start-time-end-time-and.md) | TimeEntry gets start_time, end_time and reason (renamed from notes) plus the BREAK… | Data | Version 1 (Phases 1–12) | Accepted |
| [D-45](D-045-phase-8-split-hours-excludes-break-from.md) | Phase 8 split_hours excludes Break from regular hours and overtime. | Payroll | Version 1 (Phases 1–12) | Accepted |
| [D-46](D-046-a-change-request-can-be-raised-only.md) | A change request can be raised only by the employee, on their own week, when its… | Change request | Version 1 (Phases 1–12) | Accepted |
| [D-47](D-047-requests-are-handled-by-whoever-can-approve.md) | Requests are handled by whoever can_approve the week's employee | Change request | Version 1 (Phases 1–12) | Accepted |
| [D-48](D-048-the-handler-s-note-is-optional-for.md) | The handler's note is optional for Reject, Unlock and Edit directly. | Change request | Version 1 (Phases 1–12) | Accepted |
| [D-49](D-049-edit-directly.md) | Edit directly | Change request | Version 1 (Phases 1–12) | Updated later |
| [D-50](D-050-unlock.md) | Unlock | Change request | Version 1 (Phases 1–12) | Accepted |
| [D-51](D-051-a-reopened-past-week-stays-editable-by.md) | A reopened past week stays editable by its employee until reopen_until | Timesheet | Version 1 (Phases 1–12) | Accepted |
| [D-52](D-052-is-late-is-decided-by-the-first.md) | is_late is decided by the first submission only | Timesheet | Version 1 (Phases 1–12) | Accepted |
| [D-53](D-053-payroll-hook.md) | Payroll hook | Payroll | Version 1 (Phases 1–12) | Accepted |
| [D-54](D-054-approvals-lists-the-employees-the-viewer-may.md) | /approvals/ lists the employees the viewer may approve — direct reports, plus… | Approvals | Version 1 (Phases 1–12) | Accepted |
| [D-55](D-055-flags.md) | Flags | Approvals | Version 1 (Phases 1–12) | Accepted |
| [D-56](D-056-only-weeks-with-at-least-one-employed.md) | Only weeks with at least one employed day must be SUBMITTED; a week fully outside… | Approvals | Version 1 (Phases 1–12) | Accepted |
| [D-57](D-057-reject-has-the-same-precondition-as-approve.md) | Reject has the same precondition as Approve and needs a comment | Approvals | Version 1 (Phases 1–12) | Accepted |
| [D-58](D-058-an-open-change-request-on-either-week.md) | An open change request on either week blocks Approve and Reject (and bulk approve… | Approvals | Version 1 (Phases 1–12) | Accepted |
| [D-59](D-059-unlock-on-the-approvals-page-reuses-phase.md) | Unlock on the approvals page reuses Phase 6 approvals.unlock_week | Approvals | Version 1 (Phases 1–12) | Accepted |
| [D-60](D-060-resubmitting-a-week-of-a-rejected-period.md) | Resubmitting a week of a REJECTED period sets the PeriodApproval back to PENDING… | Approvals | Version 1 (Phases 1–12) | Accepted |
| [D-61](D-061-payroll-hook-approvals-publish-payroll-period-approval.md) | Payroll hook approvals.publish_payroll_period(approval, actor, at) is called inside… | Payroll | Version 1 (Phases 1–12) | Accepted |
| [D-62](D-062-one-periodapproval-per-employee-per-period.md) | One PeriodApproval per employee per period | Data | Version 1 (Phases 1–12) | Accepted |
| [D-63](D-063-bulk-approve.md) | Bulk approve | Approvals | Version 1 (Phases 1–12) | Accepted |
| [D-64](D-064-overtime-rule.md) | Overtime rule | Payroll | Version 1 (Phases 1–12) | Accepted |
| [D-65](D-065-two-databases-fixed-order.md) | Two databases, fixed order | Payroll | Version 1 (Phases 1–12) | Accepted |
| [D-66](D-066-a-payroll-record-belongs-to-one-approval.md) | A payroll record belongs to one approval decision (approved_at =… | Payroll | Version 1 (Phases 1–12) | Accepted |
| [D-67](D-067-append-only-d-15-enforced-in-code.md) | Append-only (D-15) enforced in code | Payroll | Version 1 (Phases 1–12) | Accepted |
| [D-68](D-068-export-csv-covers-all-current-records-of.md) | Export CSV covers all CURRENT records of the selected period (filters only change the… | Payroll | Version 1 (Phases 1–12) | Accepted |
| [D-69](D-069-mark-as-paid-works-per-batch.md) | Mark as paid works per batch | Payroll | Version 1 (Phases 1–12) | Accepted |
| [D-70](D-070-corrections-superseded-records-that-had-been-exported.md) | Corrections = SUPERSEDED records that had been exported or paid, shown with their… | Payroll | Version 1 (Phases 1–12) | Updated later |
| [D-71](D-071-the-snapshot-s-expected-weekly-minutes-is.md) | The snapshot's expected_weekly_minutes is that week's prorated expected minutes (D-19) | Payroll | Version 1 (Phases 1–12) | Accepted |
| [D-72](D-072-backup-db-copies-both-databases-with-sqlite.md) | backup_db copies both databases with SQLite's online backup API through a separate… | Ops | Version 1 (Phases 1–12) | Accepted |
| [D-73](D-073-seed-demo-fills-payroll-after-the-main.md) | seed_demo fills payroll after the main seed commits (publish every approved period | Data | Version 1 (Phases 1–12) | Updated later |
| [D-74](D-074-dashboard-range-the-last-n-weeks-ending.md) | Dashboard range = the last N weeks ending with the current week (N = 4, 12 or 26 | Analytics | Version 1 (Phases 1–12) | Accepted |
| [D-75](D-075-a-week-counts-when-its-deadline-has.md) | A week counts when its deadline has passed and the person was employed on at least one… | Analytics | Version 1 (Phases 1–12) | Accepted |
| [D-76](D-076-dashboard-overtime-payroll-split-hours-per-week.md) | Dashboard overtime = payroll split_hours per week (prorated expected) summed over… | Analytics | Version 1 (Phases 1–12) | Accepted |
| [D-77](D-077-the-hours-charts-use-every-saved-entry.md) | The hours charts use every saved entry in the range (drafts and the current week included) | Analytics | Version 1 (Phases 1–12) | Accepted |
| [D-78](D-078-approval-outcomes.md) | Approval outcomes | Analytics | Version 1 (Phases 1–12) | Accepted |
| [D-79](D-079-the-dashboard-is-built-by-apps-analytics.md) | The dashboard is built by apps/analytics/services/metrics.py → dashboard_for(employee,… | Analytics | Version 1 (Phases 1–12) | Accepted |
| [D-80](D-080-charts-use-the-vendored-chart-js-with.md) | Charts use the vendored Chart.js with data only through json_script | Analytics | Version 1 (Phases 1–12) | Accepted |
| [D-81](D-081-who-is-on-team-whole-tree-the.md) | Who is on /team/: whole tree = the viewer's reporting tree, or everyone for an admin | Team | Version 1 (Phases 1–12) | Accepted |
| [D-82](D-082-utilization.md) | Utilization | Team | Version 1 (Phases 1–12) | Accepted |
| [D-83](D-083-this-week-s-compliance.md) | This week's compliance | Team | Version 1 (Phases 1–12) | Accepted |
| [D-84](D-084-per-employee-table.md) | Per-employee table | Team | Version 1 (Phases 1–12) | Accepted |
| [D-85](D-085-drill-down-is-read-only.md) | Drill-down is read-only | Team | Version 1 (Phases 1–12) | Accepted |
| [D-86](D-086-performance.md) | Performance | Team | Version 1 (Phases 1–12) | Accepted |
| [D-87](D-087-d-26-ends-for-directory-data-only.md) | D-26 ends for directory data only | Admin | Version 1 (Phases 1–12) | Accepted |
| [D-88](D-088-every-admin-add-change-goes-through-apps.md) | Every Admin add/change goes through apps/directory/services/directory_admin.py… | Admin | Version 1 (Phases 1–12) | Accepted |
| [D-89](D-089-directory-safety-rules-check-employee-and-the.md) | Directory safety rules (check_employee, and the same checks in the CSV import) | Admin | Version 1 (Phases 1–12) | Accepted |
| [D-90](D-090-deactivate.md) | Deactivate | Admin | Version 1 (Phases 1–12) | Accepted |
| [D-91](D-091-password-reset-by-hr.md) | Password reset by HR | Admin | Version 1 (Phases 1–12) | Accepted |
| [D-92](D-092-employee-csv-in-admin.md) | Employee CSV in Admin | Admin | Version 1 (Phases 1–12) | Accepted |
| [D-93](D-093-admin-access.md) | Admin access | Admin | Version 1 (Phases 1–12) | Accepted |
| [D-94](D-094-e2e-tests.md) | E2E tests | Tests | Version 1 (Phases 1–12) | Accepted |
| [D-95](D-095-e2e-is-mandatory.md) | E2E is mandatory | Tests | Version 1 (Phases 1–12) | Accepted |
| [D-96](D-096-debug-off-for-daily-use.md) | DEBUG off for daily use | Hardening | Version 1 (Phases 1–12) | Accepted |
| [D-97](D-097-manage-py-check-deploy-https-only-warnings.md) | manage.py check --deploy HTTPS-only warnings do not apply | Hardening | Version 1 (Phases 1–12) | Accepted |
| [D-98](D-098-django-import-export-removed.md) | django-import-export removed | Setup | Version 1 (Phases 1–12) | Accepted |
| [D-99](D-099-known-limitations-of-version-1.md) | Known limitations of version 1 | Scope | Version 1 (Phases 1–12) | Accepted |
| [D-100](D-100-modern-ui-one-theme-stylesheet.md) | Change 1 – Modern UI: one theme stylesheet | UI | Change 1 – Modern UI | Accepted |
| [D-101](D-101-layout.md) | Layout | UI | Change 1 – Modern UI | Accepted |
| [D-102](D-102-one-status-badge-component.md) | One status badge component | UI | Change 1 – Modern UI | Accepted |
| [D-103](D-103-charts-use-the-tokens.md) | Charts use the tokens | UI | Change 1 – Modern UI | Accepted |
| [D-104](D-104-django-admin-light-branding-only.md) | Django Admin: light branding only | UI | Change 1 – Modern UI | Accepted |
| [D-105](D-105-visual-review-tool.md) | Visual review tool | UI | Change 1 – Modern UI | Accepted |
| [D-106](D-106-weekly-grid.md) | Change 2 – Weekly grid | Grid | Change 2 – Weekly grid | Accepted |
| [D-107](D-107-cells-and-slots.md) | Cells and slots | Grid | Change 2 – Weekly grid | Updated later |
| [D-108](D-108-errors-on-the-right-cell.md) | Errors on the right cell | Grid | Change 2 – Weekly grid | Accepted |
| [D-109](D-109-one-grid-component.md) | One grid component | Grid | Change 2 – Weekly grid | Accepted |
| [D-110](D-110-comfort-and-accessibility.md) | Comfort and accessibility | Grid | Change 2 – Weekly grid | Accepted |
| [D-111](D-111-weeks-run-sunday-saturday.md) | Change 3 – weeks run Sunday → Saturday | Calendar | Change 3 – Sunday-to-Saturday week | Accepted |
| [D-112](D-112-the-deadline-stays-saturday-12-00-noon.md) | The deadline stays Saturday 12:00 noon company time, now the last day of the week… | Calendar | Change 3 – Sunday-to-Saturday week | Accepted |
| [D-113](D-113-pay-periods.md) | Pay periods | Calendar | Change 3 – Sunday-to-Saturday week | Accepted |
| [D-114](D-114-working-days-stay-monday-friday.md) | Working days stay Monday–Friday | Calendar | Change 3 – Sunday-to-Saturday week | Accepted |
| [D-115](D-115-week-links-use-the-sunday.md) | Week links use the Sunday | Calendar | Change 3 – Sunday-to-Saturday week | Accepted |
| [D-116](D-116-daylight-saving.md) | Daylight saving | Calendar | Change 3 – Sunday-to-Saturday week | Accepted |
| [D-117](D-117-no-data-conversion.md) | No data conversion | Data | Change 3 – Sunday-to-Saturday week | Accepted |
| [D-118](D-118-settled-weeks.md) | Change 4 – settled weeks | Payroll | Change 4 – Automatic pay adjustments | Accepted |
| [D-119](D-119-adjustment-new-version-previous-version.md) | Adjustment = new version − previous version | Payroll | Change 4 – Automatic pay adjustments | Accepted |
| [D-120](D-120-payrolladjustment.md) | PayrollAdjustment | Payroll | Change 4 – Automatic pay adjustments | Accepted |
| [D-121](D-121-carry-forward-period.md) | Carry-forward period | Payroll | Change 4 – Automatic pay adjustments | Updated later |
| [D-122](D-122-reason.md) | Reason | Payroll | Change 4 – Automatic pay adjustments | Accepted |
| [D-123](D-123-export-csv-mark-as-paid.md) | Export, CSV, Mark as paid | Payroll | Change 4 – Automatic pay adjustments | Accepted |
| [D-124](D-124-pages.md) | Pages | Payroll | Change 4 – Automatic pay adjustments | Updated later |
| [D-125](D-125-audit-and-sync.md) | Audit and sync | Payroll | Change 4 – Automatic pay adjustments | Accepted |
| [D-126](D-126-seed.md) | Seed | Data | Change 4 – Automatic pay adjustments | Accepted |
| [D-127](D-127-easier-multiple-time-slots.md) | Change 5 – Easier multiple time slots | Grid | Change 5 – Easier multiple time slots | Updated later |
| [D-128](D-128-optional-reason-on-time-entries.md) | Change 6 – Optional reason on time entries | Timesheet | Change 6 – Optional reason on time entries | Accepted |
| [D-129](D-129-row-actions.md) | Change 7 – Row actions | Grid | Change 7 – Edit or delete a whole row | Accepted |
| [D-130](D-130-row-action-rules.md) | Change 7 – Row action rules | Grid | Change 7 – Edit or delete a whole row | Accepted |
| [D-131](D-131-static-files-are-revalidated-on-every-page.md) | Static files are revalidated on every page load | Hardening | Change 7 – Edit or delete a whole row | Accepted |
| [D-132](D-132-pay-period-register.md) | Change 8 – Pay Period Register | Payroll | Change 8 – Pay Period Register | Accepted |
| [D-133](D-133-approval-deadline-and-ready.md) | Approval deadline and READY | Payroll | Change 8 – Pay Period Register | Updated later |
| [D-134](D-134-register-lines.md) | Register lines | Payroll | Change 8 – Pay Period Register | Updated later |
| [D-135](D-135-finalize-export-mark-as-paid-downloads.md) | Finalize & export, Mark as paid, downloads | Payroll | Change 8 – Pay Period Register | Accepted |
| [D-136](D-136-carry-forward-with-registers.md) | Carry-forward with registers | Payroll | Change 8 – Pay Period Register | Accepted |
| [D-137](D-137-earlier-data-sync-seed.md) | Earlier data, sync, seed | Payroll | Change 8 – Pay Period Register | Accepted |
| [D-138](D-138-pages.md) | Pages | Payroll | Change 8 – Pay Period Register | Accepted |
| [D-139](D-139-managers-decide-every-required-person.md) | Change 9 – Managers decide every required person | Approvals | Change 9 – Managers decide everyone | Accepted |
| [D-140](D-140-edit-from-approvals.md) | Edit from Approvals | Approvals | Change 9 – Managers decide everyone | Accepted |
| [D-141](D-141-not-submitted-by-employee.md) | "Not submitted by employee" | Approvals | Change 9 – Managers decide everyone | Accepted |
| [D-142](D-142-the-register-waits-for-everyone.md) | The register waits for everyone | Payroll | Change 9 – Managers decide everyone | Accepted |
| [D-143](D-143-pending-approvals-by-manager.md) | Pending approvals by manager | Payroll | Change 9 – Managers decide everyone | Accepted |
| [D-144](D-144-seed-change-9.md) | Seed (Change 9) | Data | Change 9 – Managers decide everyone | Accepted |
| [D-145](D-145-the-secret-key-can-t-stay-the.md) | The secret key can't stay the example | Setup | README & first-run checks | Accepted |
| [D-146](D-146-seed-demo-refuses-the-example-demo-password.md) | seed_demo refuses the example DEMO_PASSWORD | Setup | README & first-run checks | Accepted |
| [D-147](D-147-doctor-sh-gives-two-answers.md) | doctor.sh gives two answers | Setup | README & first-run checks | Accepted |
| [D-148](D-148-tasks.md) | Change 10 – Tasks | Data | Change 10 – Project tasks and charge codes | Accepted |
| [D-149](D-149-allowed-tasks-per-project.md) | Allowed tasks per project | Data | Change 10 – Project tasks and charge codes | Accepted |
| [D-150](D-150-charge-code.md) | Charge code | Data | Change 10 – Project tasks and charge codes | Accepted |
| [D-151](D-151-the-entry-rule-for-tasks.md) | The entry rule for tasks | Rules | Change 10 – Project tasks and charge codes | Accepted |
| [D-152](D-152-grid-rows-per-category-project-task.md) | Grid rows per (category, project, task) | Grid | Change 10 – Project tasks and charge codes | Accepted |
| [D-153](D-153-hours-by-task-and-by-charge-code.md) | Hours by task and by charge code | Analytics | Change 10 – Project tasks and charge codes | Accepted |
| [D-154](D-154-demo-tasks-seed-demo.md) | Demo tasks (seed_demo) | Data | Change 10 – Project tasks and charge codes | Accepted |
| [D-155](D-155-project-i-codes.md) | Change 10b – Project I-codes | Data | Change 10b – Project I-codes and project search | Accepted |
| [D-156](D-156-migration-timesheets-0008-project-i-codes.md) | Migration timesheets/0008_project_i_codes | Data | Change 10b – Project I-codes and project search | Accepted |
| [D-157](D-157-project-search-box.md) | Project search box | Grid | Change 10b – Project I-codes and project search | Accepted |
| [D-158](D-158-your-recent-projects.md) | "Your recent projects" | Grid | Change 10b – Project I-codes and project search | Accepted |
| [D-159](D-159-i-codes-everywhere-from-the-start.md) | I-codes everywhere from the start | Data | Change 10b – Project I-codes and project search | Accepted |
| [D-160](D-160-reports-project-hours-who-sees-what.md) | Change 11 – Reports → Project hours: who sees what | Reports | Change 11 – Reports → Project hours | Accepted |
| [D-161](D-161-what-counts.md) | What counts | Reports | Change 11 – Reports → Project hours | Accepted |
| [D-162](D-162-by-manager-and-by-employee.md) | By manager and By employee | Reports | Change 11 – Reports → Project hours | Accepted |
| [D-163](D-163-downloads.md) | Downloads | Reports | Change 11 – Reports → Project hours | Accepted |
| [D-164](D-164-speed.md) | Speed | Reports | Change 11 – Reports → Project hours | Accepted |
| [D-165](D-165-only-the-filters-that-make-a-difference.md) | Only the filters that make a difference | Reports | Change 11b – Only the report filters that make a difference | Accepted |
| [D-166](D-166-employee-pay-is-history.md) | Change 12 – Employee pay is history | Pay | Change 12 – Employee pay, project budgets and labour cost | Accepted |
| [D-167](D-167-only-admins-see-or-change-pay.md) | Only admins see or change pay | Pay | Change 12 – Employee pay, project budgets and labour cost | Accepted |
| [D-168](D-168-project-budgets.md) | Project budgets | Data | Change 12 – Employee pay, project budgets and labour cost | Accepted |
| [D-169](D-169-cost-rules.md) | Cost rules | Costs | Change 12 – Employee pay, project budgets and labour cost | Accepted |
| [D-170](D-170-reports-project-budget-who-sees-what.md) | Reports → Project budget: who sees what | Costs | Change 12 – Employee pay, project budgets and labour cost | Accepted |
| [D-171](D-171-two-separate-downloads.md) | Two separate downloads | Costs | Change 12 – Employee pay, project budgets and labour cost | Accepted |
| [D-172](D-172-demo-pay-and-budgets.md) | Demo pay and budgets | Data | Change 12 – Employee pay, project budgets and labour cost | Accepted |
| [D-173](D-173-refactor-r1-the-code-layout.md) | Refactor R1 – the code layout | Layout | Refactor R1 – Code layout | Accepted |
| [D-174](D-174-refactor-r2-own-apps-everything-in-apps.md) | Refactor R2 – own apps; everything in apps/ | Layout | Refactor R2 – Own apps; everything in apps/ | Accepted |
