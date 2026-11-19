"""Autorización de operaciones solicitadas por personas (/uvix/check_permission).

Separación de responsabilidades:

- **Coincidencia facial / de voz**: la produce el componente de identificación
  y nunca llega aquí directamente.
- **Identidad verificada**: se obtiene SOLO del proveedor confiable
  (GetRequestIdentity) para el ``request_id`` de la petición.
- **Autorización**: role y active se leen del registro local (Person) y las
  concesiones de RolePermission. Las preferencias nunca intervienen.

El proveedor de identidad es intercambiable: ``ProveedorRos`` en el nodo,
``ProveedorFicticio`` y ``ProveedorNoDisponible`` en pruebas y demostraciones
(M1 avanza sin cámara ni voz).
"""
import threading
import time

from django.db.utils import DatabaseError
from uvix_interfaces.msg import IdentityVerification
from uvix_interfaces.msg import Person as PersonMsg
from uvix_interfaces.srv import CheckPermission, GetRequestIdentity

from .models import Capability, Person, RolePermission

R = CheckPermission.Response

# Regla de seguridad: pedir ayuda NUNCA se deniega. Da igual que la identidad
# sea candidata, desconocida o esté vencida, que la persona esté desactivada o
# no registrada, o que el proveedor de identidad o la base no respondan. La
# identidad solo se consulta para dejar constancia de quién la pidió. No es
# configurable desde la base a propósito.
OPERACION_AYUDA = "attend_help_request"  # == MissionSpec.TYPE_ATTEND_HELP_REQUEST


# ---------------------------------------------------------------------------
# Proveedores de identidad
# ---------------------------------------------------------------------------

class ProveedorIdentidad:
    """``consultar(request_id)`` devuelve un GetRequestIdentity.Response, o
    ``None`` si no se pudo consultar (servicio caído, timeout)."""

    def consultar(self, request_id):
        raise NotImplementedError


def tiempo(ns):
    from builtin_interfaces.msg import Time
    return Time(sec=int(ns // 1_000_000_000), nanosec=int(ns % 1_000_000_000))


def ns_de(t):
    return t.sec * 1_000_000_000 + t.nanosec


class ProveedorFicticio(ProveedorIdentidad):
    """Verificaciones inyectadas a mano (datos ficticios)."""

    def __init__(self):
        self._v = {}

    def agregar(self, request_id, person_id, status, valid_until_ns,
                method=IdentityVerification.METHOD_FACE, confidence=0.97):
        ident = IdentityVerification()
        ident.request_id = request_id
        ident.person_id = person_id
        ident.identity_status = status
        ident.method = method
        ident.confidence = float(confidence)
        ident.verifier = "proveedor_ficticio"
        ident.valid_until = tiempo(valid_until_ns)
        self._v[request_id] = ident
        return ident

    def consultar(self, request_id):
        resp = GetRequestIdentity.Response()
        if request_id in self._v:
            resp.found = True
            resp.identity = self._v[request_id]
        return resp


class ProveedorNoDisponible(ProveedorIdentidad):
    def consultar(self, request_id):
        return None


class ProveedorRos(ProveedorIdentidad):
    """Cliente de /uvix/get_request_identity con plazo total ``timeout_s``.

    Se llama desde un callback de servicio: el nodo debe usar un
    MultiThreadedExecutor y un callback group distinto para este cliente.
    """

    def __init__(self, node, servicio, timeout_s, callback_group):
        self.timeout_s = timeout_s
        self.cli = node.create_client(GetRequestIdentity, servicio, callback_group=callback_group)

    def consultar(self, request_id):
        limite = time.monotonic() + self.timeout_s
        if not self.cli.wait_for_service(timeout_sec=self.timeout_s):
            return None
        req = GetRequestIdentity.Request()
        req.request_id = request_id
        fut = self.cli.call_async(req)
        listo = threading.Event()
        fut.add_done_callback(lambda _f: listo.set())
        if not listo.wait(max(0.0, limite - time.monotonic())):
            self.cli.remove_pending_request(fut)
            return None
        return fut.result()


# ---------------------------------------------------------------------------
# Decisión
# ---------------------------------------------------------------------------

def _responder(resp, code, message):
    resp.allowed = code < R.CODE_NOT_AUTHORIZED
    resp.code = code
    resp.message = message
    return resp


def _evaluar_ayuda(request_id, proveedor, ahora_ns, resp):
    """Pedir ayuda: siempre allowed. CODE_ALLOWED solo si además la identidad
    está verificada, vigente, registrada, activa y con la concesión; en otro
    caso CODE_ALLOWED_HELP con el motivo en ``message``."""
    motivo = None
    ident_resp = proveedor.consultar(request_id) if request_id else None
    if ident_resp is None:
        motivo = "identidad no consultable"
    elif not ident_resp.found or not ident_resp.identity.person_id \
            or ident_resp.identity.request_id != request_id:
        motivo = "identidad desconocida"
    else:
        ident = ident_resp.identity
        resp.identity_status = ident.identity_status
        resp.evaluated_person_id = ident.person_id
        valid_until = ns_de(ident.valid_until)
        if ident.identity_status != IdentityVerification.IDENTITY_VERIFIED:
            motivo = "identidad no verificada"
        elif valid_until == 0 or ahora_ns > valid_until:
            motivo = "verificación vencida"
        else:
            try:
                persona = Person.objects.filter(person_id=ident.person_id).first()
                if persona is None:
                    motivo = "persona no registrada"
                else:
                    resp.evaluated_role = persona.role
                    if not persona.active:
                        motivo = "persona desactivada"
                    elif persona.role != Person.Role.ADMIN and not RolePermission.objects.filter(
                            role=persona.role, capability__code=OPERACION_AYUDA).exists():
                        motivo = "rol sin concesión"
            except DatabaseError:
                motivo = "registro no disponible"
    if motivo is None:
        return _responder(resp, R.CODE_ALLOWED, "Permitido")
    return _responder(resp, R.CODE_ALLOWED_HELP,
                      f"Ayuda aceptada siempre (seguridad primero): {motivo}")


def evaluar(request_id, operation, proveedor, ahora_ns, resp=None):
    """Decide si quien hizo ``request_id`` puede solicitar ``operation``.

    Pedir ayuda va por ``_evaluar_ayuda`` y nunca se deniega. Para el resto,
    orden: petición válida -> operación registrada -> identidad confiable
    -> vigencia -> registro local (existe, activo) -> rol/concesión.
    """
    resp = resp or R()
    resp.operation = operation
    resp.evaluated_role = PersonMsg.ROLE_UNKNOWN
    resp.identity_status = IdentityVerification.IDENTITY_UNKNOWN

    if operation == OPERACION_AYUDA:
        return _evaluar_ayuda(request_id, proveedor, ahora_ns, resp)

    if not request_id or not operation:
        return _responder(resp, R.CODE_INVALID_REQUEST, "request_id y operation son obligatorios")

    try:
        capability = Capability.objects.filter(code=operation).first()
    except DatabaseError as exc:
        return _responder(resp, R.CODE_STORAGE_UNAVAILABLE, f"Registro no disponible: {exc}")
    if capability is None:
        return _responder(resp, R.CODE_UNKNOWN_OPERATION, f"Operación no registrada: {operation}")

    ident_resp = proveedor.consultar(request_id)
    if ident_resp is None:
        return _responder(resp, R.CODE_IDENTITY_UNAVAILABLE,
                          "No se pudo consultar la identidad (GetRequestIdentity)")
    if not ident_resp.found:
        return _responder(resp, R.CODE_IDENTITY_NOT_VERIFIED, "Sin verificación para esta petición")
    ident = ident_resp.identity
    resp.identity_status = ident.identity_status
    if ident.request_id != request_id or not ident.person_id \
            or ident.identity_status == IdentityVerification.IDENTITY_UNKNOWN:
        return _responder(resp, R.CODE_IDENTITY_NOT_VERIFIED, "Identidad desconocida")
    resp.evaluated_person_id = ident.person_id

    if ident.identity_status == IdentityVerification.IDENTITY_CANDIDATE:
        return _responder(resp, R.CODE_IDENTITY_NOT_VERIFIED,
                          "Identidad solo candidata: no basta para esta operación")
    if ident.identity_status != IdentityVerification.IDENTITY_VERIFIED:
        return _responder(resp, R.CODE_IDENTITY_NOT_VERIFIED, "Estado de identidad no válido")

    valid_until = ns_de(ident.valid_until)
    if valid_until == 0 or ahora_ns > valid_until:
        return _responder(resp, R.CODE_IDENTITY_EXPIRED, "La verificación ha vencido")

    try:
        persona = Person.objects.filter(person_id=ident.person_id).first()
        if persona is None:
            return _responder(resp, R.CODE_PERSON_NOT_FOUND,
                              f"{ident.person_id} no está en el registro")
        resp.evaluated_role = persona.role
        if not persona.active:
            return _responder(resp, R.CODE_PERSON_INACTIVE,
                              f"{ident.person_id} está desactivada y no puede autorizar")
        if persona.role == Person.Role.ADMIN:
            concedida = True
        else:
            concedida = RolePermission.objects.filter(
                role=persona.role, capability=capability).exists()
    except DatabaseError as exc:
        return _responder(resp, R.CODE_STORAGE_UNAVAILABLE, f"Registro no disponible: {exc}")

    if not concedida:
        return _responder(resp, R.CODE_NOT_AUTHORIZED,
                          f"El rol {Person.Role(persona.role).label} no tiene {operation}")
    return _responder(resp, R.CODE_ALLOWED, "Permitido")
