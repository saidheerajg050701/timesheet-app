# HR admin guide

Directory admins (the `is_admin` flag) manage the company in **Admin** (`/admin/`); everyone else
gets "Not allowed". Admins also see everyone in **Team** and **Reports**, and approve people who
have no manager (e.g. the CEO) — see the [manager guide](manager.md). Every change you make is
written to the audit log with your name. Nothing can be deleted: deactivate instead.

## Employees

**Admin → Directory → Employees.**
- **Add / edit** an employee: code, email, names, job title, team, manager, location, hire date,
  expected weekly hours, and the **Payroll** and **Admin** flags. The person's login follows the
  directory: email, admin rights and active status are kept in step on every save.
- **Deactivate / Reactivate:** select people in the list and choose the action. Deactivate asks
  for the end date (today by default) and logs the person out. Their history stays, and their
  submitted weeks can still be approved and paid.
- **Reset password** (on the employee's page): type a temporary password; the person must choose
  a new one at their next login. Any login lockout is cleared.
- **Import CSV / Export CSV** (on the employee list): export uses the same columns as import, so
  you can edit the file and import it again. You always see a summary — or the errors with line
  numbers — before anything changes. (From Terminal:
  `uv run python manage.py import_employees data/your_file.csv`.)
- To give an existing directory admin their first login from Terminal:
  `uv run python manage.py createsuperuser` (asks for the employee code, e.g. EMP-0007).

## Employee pay (admins only)

On an employee's page, **Pay** shows the current pay and the history.
- **Add pay change:** **Salaried** (annual salary; the hourly rate is suggested as salary ÷ 2,080
  — use it or type your own) or **Hourly** (hourly rate), from an **effective date**.
- A change is always a **new record**, so earlier project costs keep their rate. A date in the
  past re-prices work from that day; the same date again corrects the earlier record. Every
  change is audited.
- **Import pay CSV / Export pay CSV** on the employee list (columns `employee_code`, `pay_type`,
  `annual_salary`, `hourly_rate`, `effective_from`): checked first with a summary; any error
  means nothing is imported; it only ever adds records.
- Pay is never in the normal employee CSV, on anyone's Profile, or visible to managers and
  payroll (they see hourly rates and costs in Project budget, never salaries).
- Someone listed under **Rate missing** in Project budget has no pay record for those days: add
  one here.

## Teams

**Admin → Directory → Teams:** add and edit teams (name and department).

## Projects, tasks and budgets

**Admin → Projects.**
- **Projects:** you type the name; the app assigns the next **I-code** when you save (I-001,
  I-002, … I-1000 after I-999). Codes can never be edited or reused. Clear **Active** to close a
  project — inactive projects can't be booked.
- **Allowed tasks** on a project: tick the tasks people may book to it (a new project starts with
  every active task ticked). Removing or deactivating a task that saved entries use is allowed:
  those entries keep it, you get a note saying how many, and open weeks must choose another task
  when they are saved again.
- **Budget** (USD; empty = No budget set) and **Costs count from** (empty = all time) on a
  project's page; changes are audited.
- **Tasks:** code, name, description, active, sort order. The code can't change once added;
  clear *Active* instead of deleting. The page shows how many saved entries use the task.

## Pending approvals

**Pending approvals** in the Admin header: which managers still have people to approve in a pay
period, and why (read only; also available to payroll staff).

## Read-only records

Timesheets, period approvals, change requests, payroll records and the **audit log** can be
looked at in Admin but not changed there. Timesheets change only through the app's own pages
(change requests and Approvals), so every rule and audit row applies.
