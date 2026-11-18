from django.contrib import admin

from .models import Person


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("person_id", "display_name", "role", "active")
    search_fields = ("person_id", "display_name")
    list_filter = ("role", "active")
