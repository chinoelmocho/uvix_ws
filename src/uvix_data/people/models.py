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
