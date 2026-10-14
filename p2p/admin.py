from django.contrib import admin
from .models import Operator, Account, Order, Movement, Audit, DailySnapshot


# Read-only audit/inspection: financial writes go through the application's services.
class InspectAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


for model in [Operator, Account, Order, Movement, Audit, DailySnapshot]:
    admin.site.register(model, InspectAdmin)
