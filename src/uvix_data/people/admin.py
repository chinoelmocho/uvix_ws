from django.contrib import admin

from .models import Capability, FaceTemplate, Person, PersonPreference, RolePermission


class PersonPreferenceInline(admin.TabularInline):
    model = PersonPreference
    extra = 0


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("person_id", "display_name", "role", "active")
    search_fields = ("person_id", "display_name")
    list_filter = ("role", "active")
    inlines = [PersonPreferenceInline]


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 0


@admin.register(Capability)
class CapabilityAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category")
    search_fields = ("code", "name")
    inlines = [RolePermissionInline]


@admin.register(FaceTemplate)
class FaceTemplateAdmin(admin.ModelAdmin):
    """Solo metadatos y baja. El alta se hace únicamente con EnrollFace."""

    list_display = ("template_id", "person", "status", "model_version", "created_at")
    list_filter = ("status", "model_version")
    readonly_fields = [f.name for f in FaceTemplate._meta.fields]
    actions = ["revocar"]

    def has_add_permission(self, request):
        return False

    @admin.action(description="Revocar (baja) las plantillas seleccionadas")
    def revocar(self, request, queryset):
        for t in queryset.filter(status=FaceTemplate.Status.ACTIVE):
            t.revoke("baja desde el admin")
