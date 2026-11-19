"""Catálogo inicial de operaciones solicitables y concesiones por rol.

Es la forma reproducible de cargar el catálogo: cualquier base nueva o
existente lo recibe con ``migrate``. Los datos están congelados aquí a
propósito (una migración no debe depender del código vivo). Es idempotente:
si una fila ya existe no se duplica ni se modifica.

Las operaciones que se añadan después se registran con el admin o con
``Capability.objects.create``; STAFF solo las obtiene con una concesión
expresa (RolePermission) y ADMIN puede solicitarlas de inmediato.
"""
from django.db import migrations

PATIENT, STAFF = 1, 2

# code, nombre, categoría (solo descriptiva), descripción
OPERACIONES = [
    # --- Las siete operaciones acordadas para STAFF ---
    ("deliver_item", "Enviar un encargo a una persona", "encargo",
     "MissionSpec.TYPE_DELIVER_ITEM. 'Encargo' es la categoría; se autoriza esta operación concreta."),
    ("reminder_round", "Programar recordatorios para un grupo", "recordatorio",
     "MissionSpec.TYPE_REMINDER_ROUND. Siempre para un grupo en horarios establecidos (P2). "
     "El recordatorio individual de un paciente es personal_reminder."),
    ("find_person", "Búsqueda física de una persona", "busqueda",
     "El robot recorre zonas para localizar a una persona. Sin tipo de misión todavía."),
    ("operational_report", "Informe operativo de pacientes o de una ronda", "informe",
     "Visitas realizadas, avisos entregados, personas no localizadas. Sin datos clínicos."),
    ("socialize_zone", "Socializar con pacientes en una zona", "social",
     "Orden de personal para ir a una zona a conversar o animar. Distinta de dance/chat pedidos por un paciente."),
    ("dispense_medication", "Tarea de dispensación de medicamentos para un grupo", "medicacion",
     "Solo autorización con datos ficticios en M1. Sin dispensación real, dosis ni decisiones clínicas. "
     "Distinta de dispense_vitamins."),
    ("list_patients", "Buscar y listar pacientes en el registro", "registro",
     "Resumen autorizado del registro (person_id, nombre, rol, activo). No incluye notas restringidas "
     "ni mediciones, que requerirían un permiso propio. Independiente de find_person."),
    # --- Tipos de MissionSpec ya documentados que una persona puede pedir ---
    ("attend_help_request", "Pedir ayuda", "emergencia",
     "MissionSpec.TYPE_ATTEND_HELP_REQUEST. Nunca se deniega (seguridad primero), "
     "aunque la identidad o el registro no se confirmen."),
    ("personal_reminder", "Recordatorio individual", "recordatorio",
     "MissionSpec.TYPE_PERSONAL_REMINDER. Un paciente pide que se le recuerde algo a él o a otra "
     "persona (P3). Un solo destinatario, sin grupo."),
    ("dance", "Bailar", "social", "MissionSpec.TYPE_DANCE."),
    ("chat", "Conversar", "social", "MissionSpec.TYPE_CHAT."),
    ("dispense_vitamins", "Dispensar vitaminas", "cuidado", "MissionSpec.TYPE_DISPENSE_VITAMINS."),
    # --- Administración ---
    ("enroll_face", "Alta facial guiada", "administracion",
     "Autoriza EnrollFace. Sin concesiones iniciales: solo ADMIN."),
]

SIETE_STAFF = ["deliver_item", "reminder_round", "find_person", "operational_report",
               "socialize_zone", "dispense_medication", "list_patients"]

CONCESIONES = (
    # STAFF: las siete acordadas + lo documentado (cuidado y todo lo de paciente)
    [(STAFF, c) for c in SIETE_STAFF]
    + [(STAFF, c) for c in ("dispense_vitamins", "attend_help_request", "dance", "chat",
                            "personal_reminder")]
    # PATIENT: reglas documentadas en uvix_interfaces/README.md §1.2. Los
    # recordatorios de grupo (reminder_round) no; el suyo es personal_reminder.
    + [(PATIENT, c) for c in ("attend_help_request", "dance", "chat", "personal_reminder")]
)


def cargar(apps, schema_editor):
    Capability = apps.get_model("people", "Capability")
    RolePermission = apps.get_model("people", "RolePermission")
    for code, name, category, description in OPERACIONES:
        Capability.objects.get_or_create(
            code=code, defaults={"name": name, "category": category, "description": description})
    for role, code in CONCESIONES:
        RolePermission.objects.get_or_create(role=role, capability=Capability.objects.get(code=code))


def descargar(apps, schema_editor):
    Capability = apps.get_model("people", "Capability")
    Capability.objects.filter(code__in=[o[0] for o in OPERACIONES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("people", "0003_capability_rolepermission"),
    ]

    operations = [
        migrations.RunPython(cargar, descargar),
    ]
