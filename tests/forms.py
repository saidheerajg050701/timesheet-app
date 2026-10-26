"""POST data for the timesheet entry rows (Phase 5b form), shared by the integration tests."""


def work(day, start, end, project=None, category="PROJECT", reason="Feature development"):
    return {
        "date": day.isoformat(),
        "category": category,
        "project": str(project.pk) if project else "",
        "start": start,
        "end": end,
        "reason": reason,
    }


def brk(day, start, end):
    return work(day, start, end, category="BREAK", reason="Lunch break")


def leave(day, hours, category="PTO", reason="Vacation"):
    return {"date": day.isoformat(), "category": category, "hours": hours, "reason": reason}


def form(*rows, action="save", **extra):
    data = {"action": action, **extra}
    for index, row in enumerate(rows):
        data.update({f"entry-{index}-{key}": value for key, value in row.items()})
    return data


def grid_post(grid):
    """A weekly grid as the browser posts it back: every row key and slot (D-107)."""
    data = {"action": "save", "grid-row": [r.key for r in grid.rows]}
    for row in grid.rows:
        for cell in row.cells:
            for s in cell.slots:
                data.update({
                    f"entry-{s.index}-date": s.work_date, f"entry-{s.index}-category": s.category,
                    f"entry-{s.index}-project": s.project, f"entry-{s.index}-start": s.start,
                    f"entry-{s.index}-end": s.end, f"entry-{s.index}-hours": s.hours,
                    f"entry-{s.index}-reason": s.reason,
                })  # fmt: skip
    return data
