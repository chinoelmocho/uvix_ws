from django.db import models
from ros2_django.models import RosModel
from ros2_django import fields


class Person(RosModel):
    class Role(models.IntegerChoices):
        UNKNOWN = 0, "Desconocido"
        PATIENT = 1, "Paciente"
        STAFF = 2, "Personal"
        ADMIN = 3, "Administrador"


    # Identificador interno utilizado por los servicios genéricos.
    id = fields.RosBigAutoField(primary_key=True)

    # Identificador de la persona utilizado por UVIX.
    person_id = fields.RosCharField(
        max_length=64,
        unique=True,
    )

    display_name = fields.RosCharField(max_length=120)

    role = fields.RosIntegerField(
        choices=Role.choices,
        default=0,
    )

    active = fields.RosBooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=[0, 1, 2, 3]),
                name="people_person_valid_role",
            ),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.person_id})"


# ---------------------------------------------------------------------------
# Preferencias de interacción
# ---------------------------------------------------------------------------

# Claves admitidas y valores válidos (None = texto libre corto).
# Solo personalizan la interacción: ningún módulo las usa para autorizar.
PREFERENCIAS_INTERACCION = {
    "language": ("es", "en"),                  # idioma de la conversación
    "speech_rate": ("slow", "normal", "fast"),  # velocidad de la voz del robot
    "form_of_address": ("tu", "usted"),         # forma de trato
    "favorite_activity": None,                  # p. ej. "baile", "ajedrez"
}

# Claves que GetPerson puede devolver en Person.preferences. Una clave que no
# esté aquí (p. ej. escrita a mano en la base) nunca sale por ROS.
PREFERENCIAS_GET_PERSON = frozenset(PREFERENCIAS_INTERACCION)


class PersonPreference(models.Model):
    """Preferencia de interacción de una persona (una fila por clave)."""

    person = models.ForeignKey(
        Person, on_delete=models.CASCADE, related_name="preference_set")
    key = models.CharField(
        max_length=32, choices=[(k, k) for k in PREFERENCIAS_INTERACCION])
    value = models.CharField(max_length=64)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["person", "key"], name="people_pref_unique_person_key"),
        ]
        ordering = ["person", "key"]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.key not in PREFERENCIAS_INTERACCION:
            raise ValidationError({"key": f"Clave no admitida: {self.key!r}"})
        validos = PREFERENCIAS_INTERACCION[self.key]
        if validos is not None and self.value not in validos:
            raise ValidationError({"value": f"Valores válidos para {self.key}: {', '.join(validos)}"})

    def __str__(self):
        return f"{self.person.person_id}.{self.key}={self.value}"


# ---------------------------------------------------------------------------
# Catálogo de operaciones solicitables y permisos por rol
# ---------------------------------------------------------------------------

class Capability(models.Model):
    """Operación que una persona puede SOLICITAR al robot (p. ej. deliver_item).

    No confundir con las capacidades técnicas de docs/m1_capacidades.yaml
    (percepción, voz, rostros...), que describen qué sabe hacer el sistema.
    Cuando la operación coincide con un MissionSpec.TYPE_*, el código es el
    mismo texto. ``category`` es solo descriptiva: nunca se autoriza por
    categoría, siempre por el código concreto.
    """

    code = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=32, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.code


class RolePermission(models.Model):
    """Concesión expresa de una operación a un rol.

    ADMIN no necesita concesiones (puede solicitar cualquier operación
    registrada); por eso solo se admiten PATIENT y STAFF.
    """

    role = models.IntegerField(choices=Person.Role.choices)
    capability = models.ForeignKey(
        Capability, on_delete=models.CASCADE, related_name="grants")
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["role", "capability"], name="people_roleperm_unique"),
            models.CheckConstraint(
                condition=models.Q(role__in=[Person.Role.PATIENT, Person.Role.STAFF]),
                name="people_roleperm_role_grantable"),
        ]
        ordering = ["role", "capability__code"]

    def __str__(self):
        return f"{Person.Role(self.role).label}: {self.capability.code}"


# ---------------------------------------------------------------------------
# Plantillas faciales (registro interno; nunca sale por GetPerson ni topics)
# ---------------------------------------------------------------------------

class FaceTemplate(models.Model):
    """Plantilla facial de una persona. Una persona tiene cero o varias.

    - Alta: solo la crea un EnrollFace que termina en RESULT_ENROLLED, en una
      transacción al final de la captura. Cancelada o incompleta = sin fila.
    - Consulta: solo el componente de identificación (mismo proceso o
      almacenamiento interno). No hay servicio ROS que la devuelva.
    - Actualización: las plantillas no se editan; se da de alta una nueva y se
      revoca la anterior (p. ej. al cambiar de modelo).
    - Baja: ``revoke()`` marca REVOKED y borra ``embedding_ref``; si se retira
      el consentimiento se eliminan las filas. Desactivar a la persona no borra
      plantillas, pero una persona inactiva no autoriza nada.

    En M1 ``embedding_ref`` es una referencia ficticia (``ficticio://...``):
    no se guarda ningún vector biométrico.
    """

    class Source(models.TextChoices):
        GUIDED_CAPTURE = "guided_capture", "Captura guiada en el robot"
        SIMULATED = "simulated", "Simulada (M1, datos ficticios)"

    class Status(models.TextChoices):
        ACTIVE = "active", "Activa"
        REVOKED = "revoked", "Revocada"

    template_id = models.CharField(max_length=64, unique=True)   # "ftpl-" + UUID
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="face_templates")
    source = models.CharField(max_length=32, choices=Source.choices)
    consent_ref = models.CharField(max_length=128)                # documento de consentimiento
    enrolled_by = models.CharField(max_length=64)                 # person_id del operador autorizado
    request_id = models.CharField(max_length=64)                  # petición EnrollFace que la creó
    model_name = models.CharField(max_length=64)
    model_version = models.CharField(max_length=32)
    quality = models.FloatField()                                 # calidad media de las muestras
    samples = models.PositiveSmallIntegerField()
    embedding_ref = models.CharField(max_length=256, blank=True)  # vacío tras la baja
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoke_reason = models.CharField(max_length=120, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~models.Q(consent_ref=""),
                                   name="people_face_consent_required"),
            models.CheckConstraint(
                condition=(models.Q(status="active", revoked_at__isnull=True)
                           | models.Q(status="revoked", revoked_at__isnull=False)),
                name="people_face_revoked_consistent"),
        ]

    def revoke(self, reason):
        from django.utils import timezone
        self.status = self.Status.REVOKED
        self.revoked_at = timezone.now()
        self.revoke_reason = reason
        self.embedding_ref = ""
        self.save(update_fields=["status", "revoked_at", "revoke_reason", "embedding_ref"])

    def __str__(self):
        return f"{self.template_id} ({self.person.person_id}, {self.status})"
