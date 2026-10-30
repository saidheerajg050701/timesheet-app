"""Everything worked out from the loaded rows — no database reads (D-161, D-162, D-164)."""

from types import SimpleNamespace

from analytics.services.project_report.constants import (
    NO_MANAGER,
    NO_TEAM,
    NO_TIME,
    NON_PROJECT,
    NOT_APPROVED,
    ON_LEAVE,
    ONLY_NON_PROJECT,
    OTHER_PROJECTS,
)
from analytics.services.project_report.rows import (
    DetailRow,
    GroupRow,
    PersonRow,
    ProjectReport,
)
from analytics.services.team import people_in_range
from timesheets.models import TimeEntry
from timesheets.services.calendar import effective_status
from timesheets.services.validation import CATEGORY_LABELS


def _status_of(sheets, sheet_id, status, week_start, reopen_until, now):
    if sheet_id not in sheets:
        sheet = SimpleNamespace(status=status, week_start=week_start, reopen_until=reopen_until)
        sheets[sheet_id] = effective_status(sheet, now)
    return sheets[sheet_id]


def build_report(viewer, filters, managing, managers, candidates, entries, projects, tasks, now):
    """Everything worked out from the loaded rows; no database reads."""
    allowed, wanted = filters.statuses, filters.project_ids
    sheets, rows, counted_ids = {}, {}, set()
    raw = []  # (employee id, kind, ...) per entry, before the people are known
    for sheet_id, emp_id, week, status, reopen, day, category, project_id, task_id, m in entries:
        counts = allowed is None or status in allowed
        raw.append(
            (sheet_id, emp_id, week, status, reopen, day, category, project_id, task_id, m, counts)
        )
        if counts and (
            category in NON_PROJECT
            or (category == "PROJECT" and (not wanted or project_id in wanted))
        ):
            counted_ids.add(emp_id)
    # Everyone employed in the range (inactive people only with counted hours); one's own
    # report always shows oneself.
    people = people_in_range(candidates, counted_ids, filters.starts) if managing else [viewer]
    for employee in people:
        rows[employee.pk] = PersonRow(
            employee=employee,
            team=employee.team.name if employee.team else NO_TEAM,
            department=employee.team.department if employee.team else "",
            manager=f"{employee.manager.first_name} {employee.manager.last_name}"
            if employee.manager
            else "",
            by_task={},
        )
    flags = {pk: set() for pk in rows}  # what explains a 0.00 row
    matrix, project_people, weeks, detail = {}, {}, {}, []
    for (
        sheet_id,
        emp_id,
        week,
        status,
        reopen,
        day,
        category,
        project_id,
        task_id,
        m,
        counts,
    ) in raw:
        person = rows.get(emp_id)
        if person is None:
            continue
        project, task = projects.get(project_id), tasks.get(task_id)
        is_project = category == TimeEntry.Category.PROJECT
        selected = is_project and (not wanted or project_id in wanted)
        if category in TimeEntry.LEAVE:
            if counts:
                person.leave += m
                flags[emp_id].add(ON_LEAVE)
            continue
        if not counts:
            if selected:
                flags[emp_id].add(NOT_APPROVED)
            continue
        if is_project and not selected:
            flags[emp_id].add(OTHER_PROJECTS)
            continue
        week_row = weeks.setdefault(week, [0, 0])
        if selected:
            code = task.code if task else ""
            person.project += m
            person.by_task[code] = person.by_task.get(code, 0) + m
            matrix[(project_id, code)] = matrix.get((project_id, code), 0) + m
            project_people.setdefault(project_id, set()).add(emp_id)
            week_row[0] += m
        else:
            person.non_project[category] = person.non_project.get(category, 0) + m
            flags[emp_id].add(ONLY_NON_PROJECT)
            week_row[1] += m
        status_now = _status_of(sheets, sheet_id, status, week, reopen, now)
        detail.append(
            DetailRow(
                day, week, person, project if is_project else None, task, category, m, status_now
            )
        )
    for pk, person in rows.items():
        if not person.has_hours:
            found = flags[pk]
            person.note = next(
                (
                    n
                    for n in (NOT_APPROVED, OTHER_PROJECTS, ONLY_NON_PROJECT, ON_LEAVE)
                    if n in found
                ),
                NO_TIME,
            )
    listed = sorted(rows.values(), key=lambda p: not p.has_hours)  # stable: names stay in order
    used = {code for _, code in matrix}
    task_columns = [
        t
        for t in sorted(tasks.values(), key=lambda t: (t.sort_order, t.code))
        if t.active or t.code in used
    ]
    task_columns.append(None)
    totals = {}
    for (project_id, _), minutes in matrix.items():
        totals[project_id] = totals.get(project_id, 0) + minutes
    by_project = [
        (projects[pid], minutes, len(project_people[pid]))
        for pid, minutes in sorted(totals.items(), key=lambda t: projects[t[0]].number)
    ]
    by_week = [(start, *weeks.get(start, (0, 0))) for start in filters.starts]
    non_project = [
        (CATEGORY_LABELS[c], sum(p.non_project.get(c, 0) for p in listed)) for c in NON_PROJECT
    ]
    return ProjectReport(
        viewer=viewer,
        filters=filters,
        own=not managing,
        people=listed,
        task_columns=task_columns,
        by_project=by_project,
        matrix=matrix,
        by_week=by_week,
        non_project=non_project,
        by_team=by_team(listed) if managing else [],
        by_manager=by_manager(listed, managers) if managing else [],
        detail=detail,
    )


def _add(group, person):
    group.people += 1
    group.project += person.project
    group.non_project += person.non_project_total
    group.cost += person.cost


def by_team(people):
    """[GroupRow] per directory team (as it is today), by name; "No team" last."""
    groups = {}
    for person in people:
        team = person.employee.team
        key = (team is None, team.name if team else "", team.department if team else "")
        label = f"{team.name} ({team.department})" if team else NO_TEAM
        _add(groups.setdefault(key, GroupRow(label)), person)
    return [groups[key] for key in sorted(groups)]


def by_manager(people, managers):
    """[GroupRow] per manager in the report, depth-first by name (D-162).

    "Own group" = the manager plus direct reports who manage nobody, so every person is
    counted once and the column adds up to the grand total. "Including everyone below" adds
    the groups of the managers under them (the roll-up). People whose manager is not in the
    report and who manage nobody form the last row, "No manager in this report".
    """
    in_report = {p.employee.pk: p for p in people}
    leads = {m for m in managers.values() if m is not None}
    heads = {
        pk: GroupRow(p.name, employee=p.employee) for pk, p in in_report.items() if pk in leads
    }
    orphans = GroupRow(NO_MANAGER)
    for pk, person in in_report.items():
        if pk in heads:
            _add(heads[pk], person)
        elif managers.get(pk) in heads:
            _add(heads[managers[pk]], person)
        else:
            _add(orphans, person)
    children = {}
    for pk in heads:
        children.setdefault(managers.get(pk) if managers.get(pk) in heads else None, []).append(pk)

    def by_name(pk):
        employee = heads[pk].employee
        return (employee.last_name, employee.first_name, employee.employee_code)

    ordered, seen = [], set()

    def visit(pk, depth):
        row = heads[pk]
        seen.add(pk)  # bad data such as A→B→A never loops (like reporting_tree_ids)
        row.depth = depth
        ordered.append(row)
        row.rollup_project, row.rollup_non_project = row.project, row.non_project
        row.rollup_cost = row.cost
        for child in sorted(set(children.get(pk, [])) - seen, key=by_name):
            below = visit(child, depth + 1)
            row.rollup_project += below.rollup_project
            row.rollup_non_project += below.rollup_non_project
            row.rollup_cost += below.rollup_cost
        return row

    for root in sorted(children.get(None, []), key=by_name):
        visit(root, 0)
    for pk in sorted(set(heads) - seen, key=by_name):  # a loop with no top: start anywhere
        if pk not in seen:
            visit(pk, 0)
    if orphans.people:
        orphans.rollup_project, orphans.rollup_non_project = orphans.project, orphans.non_project
        orphans.rollup_cost = orphans.cost
        ordered.append(orphans)
    return ordered
