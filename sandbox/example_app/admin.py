from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    date_hierarchy = "created"

    list_display = (
        "id",
        "__str__",
        "description",
        "billing_first_name",
        "billing_last_name",
        "created",
    )
    list_display_links = ("__str__",)
    readonly_fields = ("created", "modified")
    search_fields = ("description", "billing_first_name", "billing_last_name")
