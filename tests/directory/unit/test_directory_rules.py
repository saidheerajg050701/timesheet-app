from apps.directory.services.rules import creates_loop, cycle_members, in_company_domain


def test_loops_are_found():
    """Helper check: loop members only; people leading into a loop are not on it (D-89)."""
    managers = {1: None, 2: 1, 3: 2, 4: 5, 5: 6, 6: 4, 7: 4}
    assert cycle_members(managers) == {4, 5, 6}
    assert cycle_members({1: 1}) == {1}
    assert creates_loop({1: None, 2: 1, 3: 2}, 1, 3)  # the top gets a manager from below
    assert not creates_loop({1: None, 2: 1, 3: 2}, 3, 1)
    assert not creates_loop({1: None}, 1, None)


def test_company_domain(settings):
    """Helper check: emails must end in the company domain, any case (D-89)."""
    settings.COMPANY_EMAIL_DOMAIN = "yourcompany.com"  # the @ is optional in the setting
    assert in_company_domain(" Dev1@YourCompany.com ")
    assert not in_company_domain("dev1@yourcompany.com.evil.io")
    assert not in_company_domain("dev1@notyourcompany.com")
