from django.contrib import admin


class ViewOnlyAdmin(admin.ModelAdmin):
    """Browse-only admin (D-26, D-87): records that change only through the app's workflows."""

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ViewOnlyInline(admin.TabularInline):
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class AuditedAdmin(admin.ModelAdmin):
    """Add and change only through an audited service; never delete (D-87, D-88).

    Subclasses set `save_service = staticmethod(...)` taking (actor, obj), and optionally
    `check_service` returning {field: [messages]}; the form runs it so rule errors appear
    next to the fields.
    """

    save_service = None
    check_service = None

    def has_delete_permission(self, request, obj=None):
        return False

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        actor, check = request.user.employee, self.check_service

        class CheckedForm(form):
            def _post_clean(self):
                super()._post_clean()  # the instance now holds the submitted values
                if check is not None and not self.errors:
                    for field, messages in check(actor, self.instance).items():
                        self.add_error(field if field in self.fields else None, messages)

        CheckedForm.__name__ = form.__name__
        return CheckedForm

    def save_model(self, request, obj, form, change):
        self.save_service(request.user.employee, obj)
