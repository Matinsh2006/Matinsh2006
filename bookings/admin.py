from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = [
        "full_name",
        "phone_number",
        "service",
        "date",
        "start_time",
        "status",
        "created_at",
    ]
    list_filter = ["status", "service"]
    search_fields = ["full_name", "phone_number"]
    date_hierarchy = "date"
    autocomplete_fields = ["user", "service"]
    readonly_fields = ["created_at"]
