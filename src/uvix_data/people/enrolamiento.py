"""Alta facial guiada SIMULADA (contrato EnrollFace, issue #60).

No hay cámara ni modelo: las "muestras" son valores de calidad ficticios
(``float`` 0..1, o ``None`` = rostro perdido). La captura real se integrará
después en el componente de identificación con el mismo contrato.

Garantía principal: la fila FaceTemplate solo se crea al final, dentro de una
transacción y después de comprobar por última vez la cancelación. Una
operación cancelada, de calidad insuficiente o incompleta no deja ninguna
plantilla, y menos aún una confirmada.
"""
import uuid

from django.db import transaction
from django.db.utils import DatabaseError
from uvix_interfaces.action import EnrollFace
from uvix_interfaces.srv import CheckPermission

from .models import FaceTemplate, Person

R = EnrollFace.Result
F = EnrollFace.Feedback

MODEL_NAME = "rostros_simulado"
MODEL_VERSION = "sim-0.1.0"
OPERACION = "enroll_face"


class EnrolamientoSimulado:
    def __init__(self, autorizar, umbral_calidad=0.8, max_rechazos=3, muestras_por_defecto=5):
        """``autorizar(request_id)`` -> CheckPermission.Response o None si no responde."""
        self.autorizar = autorizar
        self.umbral = umbral_calidad
        self.max_rechazos = max_rechazos
        self.muestras_por_defecto = muestras_por_defecto

    def ejecutar(self, goal, fuente, cancelado=lambda: False, feedback=lambda fb: None):
        res = R()
        res.model_version = MODEL_VERSION
        requeridas = goal.samples_required or self.muestras_por_defecto

        def fin(code, detail, aceptadas=0):
            res.result_code = code
            res.enrolled = code == R.RESULT_ENROLLED
            res.samples_accepted = aceptadas
            res.detail = detail
            return res

        if not goal.consent_ref.strip():
            return fin(R.RESULT_NO_CONSENT, "Falta la referencia de consentimiento")

        # Autorizar antes de mirar el registro: no se revela si la persona existe.
        feedback(F(stage=F.STAGE_AUTHORIZING, samples_required=requeridas))
        auth = self.autorizar(goal.request_id)
        if auth is None or auth.code >= CheckPermission.Response.CODE_IDENTITY_UNAVAILABLE:
            return fin(R.RESULT_UNAVAILABLE, "CheckPermission no disponible")
        if not auth.allowed:
            return fin(R.RESULT_NOT_AUTHORIZED, f"Alta no autorizada (code {auth.code})")

        try:
            persona = Person.objects.filter(person_id=goal.person_id).first()
        except DatabaseError as exc:
            return fin(R.RESULT_UNAVAILABLE, f"Registro no disponible: {exc}")
        if persona is None:
            return fin(R.RESULT_PERSON_NOT_FOUND, f"{goal.person_id} no está registrada")
        if not persona.active:
            return fin(R.RESULT_PERSON_INACTIVE, f"{goal.person_id} está desactivada")

        aceptadas, rechazos, calidades = 0, 0, []
        feedback(F(stage=F.STAGE_WAITING_FACE, samples_required=requeridas,
                   instruction="Mire a la cámara"))
        for calidad in fuente:
            if cancelado():
                return fin(R.RESULT_CANCELED, "Cancelada por el cliente; sin alta", aceptadas)
            if calidad is None:
                return fin(R.RESULT_INCOMPLETE, "Rostro perdido antes de terminar", aceptadas)
            if calidad >= self.umbral:
                aceptadas += 1
                calidades.append(calidad)
                instruccion = "Muy bien, siga así"
            else:
                rechazos += 1
                instruccion = "Acérquese y mire de frente"
                if rechazos > self.max_rechazos:
                    return fin(R.RESULT_LOW_QUALITY,
                               f"{rechazos} muestras bajo el umbral {self.umbral}", aceptadas)
            feedback(F(stage=F.STAGE_CAPTURING, samples_accepted=aceptadas,
                       samples_required=requeridas, last_quality=float(calidad),
                       instruction=instruccion))
            if aceptadas >= requeridas:
                break
        else:
            return fin(R.RESULT_INCOMPLETE,
                       f"Captura terminada con {aceptadas}/{requeridas} muestras", aceptadas)

        if cancelado():
            return fin(R.RESULT_CANCELED, "Cancelada antes de guardar; sin alta", aceptadas)
        feedback(F(stage=F.STAGE_SAVING, samples_accepted=aceptadas, samples_required=requeridas))
        template_id = f"ftpl-{uuid.uuid4()}"
        try:
            with transaction.atomic():
                FaceTemplate.objects.create(
                    template_id=template_id, person=persona,
                    source=FaceTemplate.Source.SIMULATED, consent_ref=goal.consent_ref,
                    enrolled_by=auth.evaluated_person_id, request_id=goal.request_id,
                    model_name=MODEL_NAME, model_version=MODEL_VERSION,
                    quality=sum(calidades) / len(calidades), samples=aceptadas,
                    embedding_ref=f"ficticio://{template_id}")
        except DatabaseError as exc:
            return fin(R.RESULT_UNAVAILABLE, f"No se pudo guardar: {exc}", aceptadas)
        res.template_id = template_id
        return fin(R.RESULT_ENROLLED, "Alta confirmada", aceptadas)
