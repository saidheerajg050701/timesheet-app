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
