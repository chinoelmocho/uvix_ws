from django.db.utils import DatabaseError
from uvix_interfaces.msg import KeyValue
from uvix_interfaces.msg import Person as PersonMsg
from uvix_interfaces.srv import GetPerson

from .models import PREFERENCIAS_GET_PERSON
from .models import Person as PersonModel


def get_person(request, response):
    try:
        record = PersonModel.objects.filter(person_id=request.person_id).first()
        prefs = [] if record is None else [
            KeyValue(key=p.key, value=p.value)
            for p in record.preference_set.filter(key__in=PREFERENCIAS_GET_PERSON).order_by("key")
        ]
    except DatabaseError:
        # Registro ilegible: se responde UNAVAILABLE, nunca NOT_FOUND.
        response.status = GetPerson.Response.STATUS_UNAVAILABLE
        response.found = False
        response.person.role = PersonMsg.ROLE_UNKNOWN
        return response

    if record is None:
        response.status = GetPerson.Response.STATUS_NOT_FOUND
        response.found = False
        response.person.role = PersonMsg.ROLE_UNKNOWN
        return response

    response.status = GetPerson.Response.STATUS_OK
    response.found = True
    response.person.person_id = record.person_id
    response.person.display_name = record.display_name
    response.person.role = record.role
    response.person.active = record.active
    # Solo las preferencias de esta persona y solo las claves permitidas.
    # Nunca se incluyen plantillas faciales, notas ni permisos.
    response.person.preferences = prefs
    return response
