"""Pruebas unitarias del callback de /uvix/get_person (sin ROS en marcha).

Django crea una base de prueba en memoria; la base habitual no se toca.
Requiere haber hecho ``source`` del install con uvix_interfaces:

    python3 -m django test people --settings=uvix_data_project.settings
"""
from django.db import connection
from django.db.utils import DatabaseError
from django.test import TestCase
from uvix_interfaces.msg import Person as PersonMsg
from uvix_interfaces.srv import GetPerson

from .models import Person
from .ros_services import get_person


def consultar(person_id):
    request = GetPerson.Request()
    request.person_id = person_id
    return get_person(request, GetPerson.Response())


class GetPersonTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Datos ficticios.
        Person.objects.create(person_id="prueba_staff_01", display_name="Cuidadora Ficticia",
                              role=Person.Role.STAFF, active=True)
        Person.objects.create(person_id="prueba_paciente_02", display_name="Residente Ficticio",
                              role=Person.Role.PATIENT, active=False)

    def test_persona_activa(self):
        r = consultar("prueba_staff_01")
        self.assertTrue(r.found)
        self.assertEqual(r.person.person_id, "prueba_staff_01")
        self.assertEqual(r.person.display_name, "Cuidadora Ficticia")
        self.assertEqual(r.person.role, PersonMsg.ROLE_STAFF)
        self.assertTrue(r.person.active)

    def test_persona_desactivada_conserva_identidad_y_rol(self):
        r = consultar("prueba_paciente_02")
        self.assertTrue(r.found)
        self.assertEqual(r.person.person_id, "prueba_paciente_02")
        self.assertEqual(r.person.display_name, "Residente Ficticio")
        self.assertEqual(r.person.role, PersonMsg.ROLE_PATIENT)
        self.assertFalse(r.person.active)

    def test_inexistente(self):
        r = consultar("no_existe_999")
        self.assertFalse(r.found)
        self.assertEqual(r.person.role, PersonMsg.ROLE_UNKNOWN)
        self.assertEqual(r.person.person_id, "")

    def test_id_vacio_no_encuentra(self):
        r = consultar("")
        self.assertFalse(r.found)
        self.assertEqual(r.person.role, PersonMsg.ROLE_UNKNOWN)

    def test_preferences_vacias_en_m1(self):
        # El modelo aún no almacena preferencias (UVIX-16, M4).
        self.assertEqual(len(consultar("prueba_staff_01").person.preferences), 0)

    def test_roles_del_modelo_coinciden_con_el_mensaje(self):
        self.assertEqual(Person.Role.UNKNOWN, PersonMsg.ROLE_UNKNOWN)
        self.assertEqual(Person.Role.PATIENT, PersonMsg.ROLE_PATIENT)
        self.assertEqual(Person.Role.STAFF, PersonMsg.ROLE_STAFF)
        self.assertEqual(Person.Role.ADMIN, PersonMsg.ROLE_ADMIN)

    def test_error_de_almacenamiento_no_es_found_false(self):
        # Un fallo de la base debe propagarse; nunca convertirse en found=False.
        with connection.cursor() as cur:
            cur.execute("ALTER TABLE people_person RENAME TO people_person_oculta")
        try:
            with self.assertRaises(DatabaseError):
                consultar("prueba_staff_01")
        finally:
            with connection.cursor() as cur:
                cur.execute("ALTER TABLE people_person_oculta RENAME TO people_person")
