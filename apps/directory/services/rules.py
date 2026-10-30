"""Directory safety rules shared by Admin edits, actions and the CSV import (D-89, D-90)."""

from apps.directory.services.signup import company_domain


def cycle_members(managers):
    """Employee ids that sit on a reporting loop, from {employee id: manager id}."""
    on_loop = set()
    for start in managers:
        seen, current = [], start
        while current is not None and current not in seen:
            seen.append(current)
            current = managers.get(current)
        if current is not None:  # walked back into the path: everything from there loops
            on_loop |= set(seen[seen.index(current) :])
    return on_loop


def creates_loop(managers, employee_id, manager_id):
    """Would giving `employee_id` this manager put them on a reporting loop?"""
    if manager_id is None:
        return False
    return employee_id in cycle_members({**managers, employee_id: manager_id})


def in_company_domain(email):
    return email.strip().lower().endswith(company_domain())


def domain_error(email):
    return f"{email} is not a company email address (it must end in {company_domain()})."
