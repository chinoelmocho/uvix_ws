"""Pruebas unitarias del callback de /uvix/get_person (sin ROS en marcha).

Django crea una base de prueba en memoria; la base habitual no se toca.
Requiere haber hecho ``source`` del install con uvix_interfaces:

    python3 -m django test people --settings=uvix_data_project.settings
"""
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.utils import DatabaseError
from django.test import TestCase, TransactionTestCase
from uvix_interfaces.msg import Person as PersonMsg
from uvix_interfaces.srv import GetPerson

from .models import Person, PersonPreference
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

    def test_persona_sin_preferencias_devuelve_lista_vacia(self):
        # Sin filas en PersonPreference: comportamiento genérico (lista vacía).
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


# ---------------------------------------------------------------------------
# Etapa 1: preferencias de interacción
# ---------------------------------------------------------------------------

def como_dict(resp):
    return {kv.key: kv.value for kv in resp.person.preferences}


class PreferenciasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Dos personas ficticias con preferencias distintas.
        ana = Person.objects.create(person_id="prueba_paciente_ana", display_name="Ana Ficticia",
                                    role=Person.Role.PATIENT, active=True)
        beto = Person.objects.create(person_id="prueba_paciente_beto", display_name="Beto Ficticio",
                                     role=Person.Role.PATIENT, active=True)
        for p, k, v in [(ana, "language", "es"), (ana, "speech_rate", "slow"),
                        (ana, "form_of_address", "usted"), (ana, "favorite_activity", "baile"),
                        (beto, "language", "en"), (beto, "favorite_activity", "ajedrez")]:
            PersonPreference.objects.create(person=p, key=k, value=v)

    def test_cada_persona_recibe_solo_sus_preferencias(self):
        ana = como_dict(consultar("prueba_paciente_ana"))
        beto = como_dict(consultar("prueba_paciente_beto"))
        self.assertEqual(ana, {"language": "es", "speech_rate": "slow",
                               "form_of_address": "usted", "favorite_activity": "baile"})
        self.assertEqual(beto, {"language": "en", "favorite_activity": "ajedrez"})

    def test_orden_estable_por_clave(self):
        claves = [kv.key for kv in consultar("prueba_paciente_ana").person.preferences]
        self.assertEqual(claves, sorted(claves))

    def test_clave_no_permitida_no_sale_por_get_person(self):
        # Una fila escrita fuera del admin con una clave no admitida
        # (las choices no se imponen en la base) nunca se publica.
        ana = Person.objects.get(person_id="prueba_paciente_ana")
        PersonPreference.objects.bulk_create([PersonPreference(person=ana, key="role", value="3")])
        self.assertNotIn("role", como_dict(consultar("prueba_paciente_ana")))
        # El rol tampoco cambia: las preferencias no conceden permisos.
        self.assertEqual(consultar("prueba_paciente_ana").person.role, PersonMsg.ROLE_PATIENT)

    def test_misma_clave_dos_veces_se_rechaza(self):
        ana = Person.objects.get(person_id="prueba_paciente_ana")
        with self.assertRaises(IntegrityError), transaction.atomic():
            PersonPreference.objects.create(person=ana, key="language", value="en")

    def test_validacion_de_valores(self):
        ana = Person.objects.get(person_id="prueba_paciente_ana")
        with self.assertRaises(ValidationError):
            PersonPreference(person=ana, key="speech_rate", value="rapidisimo").full_clean()
        with self.assertRaises(ValidationError):
            PersonPreference(person=ana, key="password", value="x").full_clean()


# ---------------------------------------------------------------------------
# Etapa 2: catálogo de operaciones y CheckPermission
# ---------------------------------------------------------------------------

from uvix_interfaces.msg import IdentityVerification as IV  # noqa: E402
from uvix_interfaces.srv import CheckPermission  # noqa: E402

from .models import Capability, RolePermission  # noqa: E402
from .permisos import (ProveedorFicticio, ProveedorNoDisponible,  # noqa: E402
                       evaluar)

C = CheckPermission.Response
AHORA = 1_795_000_000 * 10**9          # instante fijo de las pruebas (ns)
VIGENTE = AHORA + 60 * 10**9           # valid_until dentro de 60 s
VENCIDA = AHORA - 1 * 10**9

SIETE = ["deliver_item", "reminder_round", "find_person", "operational_report",
         "socialize_zone", "dispense_medication", "list_patients"]


class PermisosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Personas ficticias.
        for pid, nombre, rol, activa in [
                ("prueba_admin_01", "Admin Ficticio", Person.Role.ADMIN, True),
                ("prueba_staff_juan", "Juan Ficticio", Person.Role.STAFF, True),
                ("prueba_paciente_maria", "María Ficticia", Person.Role.PATIENT, True),
                ("prueba_staff_baja", "Personal de Baja", Person.Role.STAFF, False),
                ("prueba_admin_baja", "Admin de Baja", Person.Role.ADMIN, False),
                ("prueba_sin_rol", "Sin Rol", Person.Role.UNKNOWN, True)]:
            Person.objects.create(person_id=pid, display_name=nombre, role=rol, active=activa)

    def setUp(self):
        self.prov = ProveedorFicticio()
        self.n = 0

    def pedir(self, person_id, operation, status=IV.IDENTITY_VERIFIED, valid_until=VIGENTE,
              proveedor=None):
        """Registra en el proveedor ficticio quién hizo la petición y la evalúa."""
        self.n += 1
        rid = f"req-prueba-{self.n:04d}"
        if person_id is not None:
            self.prov.agregar(rid, person_id, status, valid_until)
        return evaluar(rid, operation, proveedor or self.prov, AHORA)

    # --- catálogo inicial ---
    def test_catalogo_inicial_cargado_por_migracion(self):
        codigos = set(Capability.objects.values_list("code", flat=True))
        self.assertTrue(set(SIETE) <= codigos)
        for tipo in ("deliver_item", "reminder_round", "attend_help_request",
                     "dance", "chat", "dispense_vitamins"):
            self.assertIn(tipo, codigos)

    def test_concesion_duplicada_se_rechaza(self):
        cap = Capability.objects.get(code="deliver_item")
        with self.assertRaises(IntegrityError), transaction.atomic():
            RolePermission.objects.create(role=Person.Role.STAFF, capability=cap)

    def test_no_se_concede_a_admin_ni_a_unknown(self):
        cap = Capability.objects.create(code="prueba_otra", name="Otra")
        for rol in (Person.Role.ADMIN, Person.Role.UNKNOWN):
            with self.assertRaises(IntegrityError), transaction.atomic():
                RolePermission.objects.create(role=rol, capability=cap)

    # --- STAFF / ADMIN / PATIENT ---
    def test_staff_puede_las_siete(self):
        for op in SIETE:
            r = self.pedir("prueba_staff_juan", op)
            self.assertEqual((r.allowed, r.code), (True, C.CODE_ALLOWED), op)
            self.assertEqual(r.evaluated_role, PersonMsg.ROLE_STAFF)

    def test_admin_puede_todo_lo_registrado(self):
        for op in Capability.objects.values_list("code", flat=True):
            self.assertTrue(self.pedir("prueba_admin_01", op).allowed, op)

    def test_paciente_reglas_documentadas(self):
        for op in ("attend_help_request", "dance", "chat", "reminder_round"):
            self.assertTrue(self.pedir("prueba_paciente_maria", op).allowed, op)
        for op in ("deliver_item", "find_person", "operational_report", "socialize_zone",
                   "dispense_medication", "list_patients", "dispense_vitamins", "enroll_face"):
            r = self.pedir("prueba_paciente_maria", op)
            self.assertEqual((r.allowed, r.code), (False, C.CODE_NOT_AUTHORIZED), op)

    def test_rol_desconocido_no_puede_nada(self):
        r = self.pedir("prueba_sin_rol", "chat")
        self.assertEqual((r.allowed, r.code), (False, C.CODE_NOT_AUTHORIZED))

    def test_enroll_face_solo_admin(self):
        self.assertTrue(self.pedir("prueba_admin_01", "enroll_face").allowed)
        self.assertEqual(self.pedir("prueba_staff_juan", "enroll_face").code, C.CODE_NOT_AUTHORIZED)

    # --- octava operación: concesión y revocación ---
    def test_octava_operacion_admin_inmediato_staff_con_concesion(self):
        cap = Capability.objects.create(code="prueba_octava_operacion", name="Octava (ficticia)")
        self.assertEqual(self.pedir("prueba_admin_01", cap.code).code, C.CODE_ALLOWED)
        self.assertEqual(self.pedir("prueba_staff_juan", cap.code).code, C.CODE_NOT_AUTHORIZED)
        concesion = RolePermission.objects.create(role=Person.Role.STAFF, capability=cap)
        self.assertEqual(self.pedir("prueba_staff_juan", cap.code).code, C.CODE_ALLOWED)
        concesion.delete()
        self.assertEqual(self.pedir("prueba_staff_juan", cap.code).code, C.CODE_NOT_AUTHORIZED)

    # --- operación desconocida y categoría ---
    def test_operacion_desconocida_rechazada_incluso_admin(self):
        r = self.pedir("prueba_admin_01", "abrir_puertas")
        self.assertEqual((r.allowed, r.code), (False, C.CODE_UNKNOWN_OPERATION))

    def test_categoria_encargo_no_es_operacion(self):
        # Se autoriza la operación concreta (deliver_item), nunca la categoría.
        self.assertEqual(self.pedir("prueba_staff_juan", "encargo").code, C.CODE_UNKNOWN_OPERATION)

    # --- usuario desactivado ---
    def test_desactivados_no_autorizan(self):
        for pid in ("prueba_staff_baja", "prueba_admin_baja"):
            r = self.pedir(pid, "chat")
            self.assertEqual((r.allowed, r.code), (False, C.CODE_PERSON_INACTIVE), pid)
        self.assertTrue(Person.objects.filter(person_id="prueba_staff_baja").exists())

    # --- identidad candidata, desconocida, vencida, ausente ---
    def test_candidata_no_basta_para_operaciones_normales(self):
        r = self.pedir("prueba_admin_01", "deliver_item", status=IV.IDENTITY_CANDIDATE)
        self.assertEqual((r.allowed, r.code), (False, C.CODE_IDENTITY_NOT_VERIFIED))

    def test_excepcion_de_ayuda_con_candidata(self):
        r = self.pedir("prueba_paciente_maria", "attend_help_request", status=IV.IDENTITY_CANDIDATE)
        self.assertEqual((r.allowed, r.code), (True, C.CODE_ALLOWED_CANDIDATE_HELP))
        self.assertEqual(r.identity_status, IV.IDENTITY_CANDIDATE)

    def test_excepcion_de_ayuda_no_salta_vencimiento_ni_desconocida(self):
        r = self.pedir("prueba_paciente_maria", "attend_help_request",
                       status=IV.IDENTITY_CANDIDATE, valid_until=VENCIDA)
        self.assertEqual(r.code, C.CODE_IDENTITY_EXPIRED)
        r = self.pedir("", "attend_help_request", status=IV.IDENTITY_UNKNOWN)
        self.assertEqual(r.code, C.CODE_IDENTITY_NOT_VERIFIED)

    def test_identidad_vencida(self):
        r = self.pedir("prueba_staff_juan", "deliver_item", valid_until=VENCIDA)
        self.assertEqual((r.allowed, r.code), (False, C.CODE_IDENTITY_EXPIRED))

    def test_sin_verificacion_para_la_peticion(self):
        r = self.pedir(None, "deliver_item")
        self.assertEqual((r.allowed, r.code), (False, C.CODE_IDENTITY_NOT_VERIFIED))

    def test_verificado_pero_no_registrado(self):
        r = self.pedir("no_registrado_999", "chat")
        self.assertEqual((r.allowed, r.code), (False, C.CODE_PERSON_NOT_FOUND))

    def test_peticion_incompleta(self):
        self.assertEqual(evaluar("", "chat", self.prov, AHORA).code, C.CODE_INVALID_REQUEST)
        self.assertEqual(evaluar("req-x", "", self.prov, AHORA).code, C.CODE_INVALID_REQUEST)

    # --- proveedor o almacenamiento no disponibles ---
    def test_proveedor_no_disponible_no_es_denegacion(self):
        r = self.pedir("prueba_admin_01", "chat", proveedor=ProveedorNoDisponible())
        self.assertEqual((r.allowed, r.code), (False, C.CODE_IDENTITY_UNAVAILABLE))
        self.assertGreaterEqual(r.code, 20)

    def test_almacenamiento_no_disponible(self):
        with connection.cursor() as cur:
            cur.execute("ALTER TABLE people_capability RENAME TO people_capability_oculta")
        try:
            r = self.pedir("prueba_admin_01", "chat")
        finally:
            with connection.cursor() as cur:
                cur.execute("ALTER TABLE people_capability_oculta RENAME TO people_capability")
        self.assertEqual((r.allowed, r.code), (False, C.CODE_STORAGE_UNAVAILABLE))

    # --- se evalúa al solicitante, no al destinatario ---
    def test_juan_pide_entrega_para_maria_se_evalua_a_juan(self):
        r = self.pedir("prueba_staff_juan", "deliver_item")
        self.assertEqual((r.allowed, r.evaluated_person_id), (True, "prueba_staff_juan"))
        # Al revés: María (paciente) pide una entrega para Juan -> se evalúa a María.
        r = self.pedir("prueba_paciente_maria", "deliver_item")
        self.assertEqual((r.allowed, r.evaluated_person_id, r.code),
                         (False, "prueba_paciente_maria", C.CODE_NOT_AUTHORIZED))

    def test_identidad_de_otra_peticion_no_vale(self):
        # El proveedor devuelve una verificación con otro request_id: se ignora.
        ident = self.prov.agregar("req-ajena", "prueba_admin_01", IV.IDENTITY_VERIFIED, VIGENTE)
        self.prov._v["req-propia"] = ident
        self.assertEqual(evaluar("req-propia", "chat", self.prov, AHORA).code,
                         C.CODE_IDENTITY_NOT_VERIFIED)

    def test_preferencias_no_conceden_permisos(self):
        maria = Person.objects.get(person_id="prueba_paciente_maria")
        PersonPreference.objects.bulk_create([PersonPreference(person=maria, key="role", value="3")])
        self.assertEqual(self.pedir("prueba_paciente_maria", "list_patients").code,
                         C.CODE_NOT_AUTHORIZED)


# ---------------------------------------------------------------------------
# Etapa 3: FaceTemplate y EnrollFace simulado
# ---------------------------------------------------------------------------

from uvix_interfaces.action import EnrollFace  # noqa: E402

from .enrolamiento import EnrolamientoSimulado  # noqa: E402
from .models import FaceTemplate  # noqa: E402

ER = EnrollFace.Result


class EnrollFaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Person.objects.create(person_id="prueba_admin_01", display_name="Admin Ficticio",
                              role=Person.Role.ADMIN, active=True)
        Person.objects.create(person_id="prueba_staff_juan", display_name="Juan Ficticio",
                              role=Person.Role.STAFF, active=True)
        Person.objects.create(person_id="prueba_paciente_ana", display_name="Ana Ficticia",
                              role=Person.Role.PATIENT, active=True)
        Person.objects.create(person_id="prueba_paciente_baja", display_name="Baja Ficticia",
                              role=Person.Role.PATIENT, active=False)

    def setUp(self):
        # Autorización real (evaluar) con proveedor de identidad ficticio.
        self.prov = ProveedorFicticio()
        self.prov.agregar("req-admin", "prueba_admin_01", IV.IDENTITY_VERIFIED, VIGENTE)
        self.prov.agregar("req-staff", "prueba_staff_juan", IV.IDENTITY_VERIFIED, VIGENTE)
        self.nucleo = EnrolamientoSimulado(lambda rid: evaluar(rid, "enroll_face", self.prov, AHORA))

    def alta(self, person_id="prueba_paciente_ana", muestras=(0.95,) * 5, request_id="req-admin",
             consent="consentimiento-ficticio-001", cancelar_tras=None):
        g = EnrollFace.Goal(person_id=person_id, request_id=request_id, consent_ref=consent)
        vistas = []

        def fuente():
            for q in muestras:
                vistas.append(q)
                yield q
        cancelado = (lambda: cancelar_tras is not None and len(vistas) > cancelar_tras)
        return self.nucleo.ejecutar(g, fuente(), cancelado=cancelado)

    def test_alta_correcta_crea_una_plantilla_activa(self):
        r = self.alta()
        self.assertEqual((r.result_code, r.enrolled, r.samples_accepted), (ER.RESULT_ENROLLED, True, 5))
        t = FaceTemplate.objects.get(template_id=r.template_id)
        self.assertEqual(t.person.person_id, "prueba_paciente_ana")
        self.assertEqual((t.status, t.enrolled_by, t.model_version, t.source),
                         ("active", "prueba_admin_01", r.model_version, "simulated"))
        self.assertTrue(t.embedding_ref.startswith("ficticio://"))

    def test_varias_plantillas_por_persona(self):
        self.alta()
        self.alta()
        self.assertEqual(FaceTemplate.objects.filter(person__person_id="prueba_paciente_ana").count(), 2)

    def test_calidad_insuficiente_no_crea_plantilla(self):
        r = self.alta(muestras=(0.95, 0.3, 0.2, 0.4, 0.1, 0.95))
        self.assertEqual((r.result_code, r.enrolled, r.template_id), (ER.RESULT_LOW_QUALITY, False, ""))
        self.assertEqual(FaceTemplate.objects.count(), 0)

    def test_cancelacion_no_crea_plantilla(self):
        r = self.alta(cancelar_tras=2)
        self.assertEqual((r.result_code, r.enrolled), (ER.RESULT_CANCELED, False))
        self.assertEqual(FaceTemplate.objects.count(), 0)

    def test_cancelacion_tras_la_ultima_muestra_no_crea_plantilla(self):
        r = self.alta(cancelar_tras=4)  # se cancela justo antes de guardar
        self.assertEqual(r.result_code, ER.RESULT_CANCELED)
        self.assertEqual(FaceTemplate.objects.count(), 0)

    def test_registro_incompleto_no_crea_plantilla(self):
        r = self.alta(muestras=(0.95, 0.95))               # la captura termina antes
        self.assertEqual((r.result_code, r.enrolled), (ER.RESULT_INCOMPLETE, False))
        r = self.alta(muestras=(0.95, None, 0.95))         # rostro perdido
        self.assertEqual(r.result_code, ER.RESULT_INCOMPLETE)
        self.assertEqual(FaceTemplate.objects.count(), 0)

    def test_sin_consentimiento_o_sin_permiso_o_persona_invalida(self):
        self.assertEqual(self.alta(consent="  ").result_code, ER.RESULT_NO_CONSENT)
        self.assertEqual(self.alta(request_id="req-staff").result_code, ER.RESULT_NOT_AUTHORIZED)
        self.assertEqual(self.alta(request_id="req-sin-identidad").result_code,
                         ER.RESULT_NOT_AUTHORIZED)
        self.assertEqual(self.alta(person_id="no_existe").result_code, ER.RESULT_PERSON_NOT_FOUND)
        self.assertEqual(self.alta(person_id="prueba_paciente_baja").result_code,
                         ER.RESULT_PERSON_INACTIVE)
        self.assertEqual(FaceTemplate.objects.count(), 0)

    def test_autorizacion_no_disponible(self):
        nucleo = EnrolamientoSimulado(lambda rid: None)
        g = EnrollFace.Goal(person_id="prueba_paciente_ana", request_id="r", consent_ref="c")
        self.assertEqual(nucleo.ejecutar(g, iter([0.95] * 5)).result_code, ER.RESULT_UNAVAILABLE)

    def test_consentimiento_obligatorio_en_la_base(self):
        ana = Person.objects.get(person_id="prueba_paciente_ana")
        with self.assertRaises(IntegrityError), transaction.atomic():
            FaceTemplate.objects.create(template_id="ftpl-x", person=ana, source="simulated",
                                        consent_ref="", enrolled_by="a", request_id="r",
                                        model_name="m", model_version="v", quality=1, samples=1)

    def test_baja_revoca_y_borra_referencia(self):
        t = FaceTemplate.objects.get(template_id=self.alta().template_id)
        t.revoke("consentimiento retirado (ficticio)")
        t.refresh_from_db()
        self.assertEqual((t.status, t.embedding_ref), ("revoked", ""))
        self.assertIsNotNone(t.revoked_at)

    def test_plantillas_fuera_de_get_person(self):
        self.alta()
        r = consultar("prueba_paciente_ana")
        self.assertTrue(r.found)
        # El mensaje Person solo tiene estos campos: ninguno transporta plantillas.
        self.assertEqual(set(PersonMsg.get_fields_and_field_types()),
                         {"person_id", "display_name", "role", "active", "preferences"})
        self.assertEqual(len(r.person.preferences), 0)
        # Ni el resultado ni el feedback de EnrollFace transportan biometría.
        for campos in (EnrollFace.Result.get_fields_and_field_types(),
                       EnrollFace.Feedback.get_fields_and_field_types()):
            self.assertFalse({"embedding", "image", "embedding_ref"} & set(campos))


class MigracionCompatibleTests(TransactionTestCase):
    """Una persona creada con el esquema 0001 sigue apareciendo tras migrar."""

    # Restaura el catálogo sembrado por migración para las pruebas siguientes.
    serialized_rollback = True

    def test_persona_anterior_sigue_en_get_person_sin_preferencias(self):
        executor = MigrationExecutor(connection)
        executor.migrate([("people", "0001_initial")])
        with connection.cursor() as cur:
            cur.execute("INSERT INTO people_person (person_id, display_name, role, active) "
                        "VALUES ('prueba_antigua_01', 'Persona Antigua', 1, 1)")
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())
        r = consultar("prueba_antigua_01")
        self.assertTrue(r.found)
        self.assertEqual(r.person.display_name, "Persona Antigua")
        self.assertEqual(r.person.role, PersonMsg.ROLE_PATIENT)
        self.assertTrue(r.person.active)
        self.assertEqual(len(r.person.preferences), 0)
