"""Keep the payroll app in the "payroll" database and every other app out of it (B.6)."""

PAYROLL_APP = "payroll"
PAYROLL_DB = "payroll"


class PayrollRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label == PAYROLL_APP:
            return PAYROLL_DB
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == PAYROLL_APP:
            return PAYROLL_DB
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # No relations across databases: both payroll or both not payroll.
        return (obj1._meta.app_label == PAYROLL_APP) == (obj2._meta.app_label == PAYROLL_APP)

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == PAYROLL_APP:
            return db == PAYROLL_DB
        return db != PAYROLL_DB
