#!/usr/bin/python3
"""Validación de extremo a extremo: preferencias, /uvix/check_permission y
/uvix/enroll_face (issue #60, M1-05).

Procesos separados, todos sobre una base SQLite temporal y un ROS_DOMAIN_ID
de prueba:

- ``identidad_ficticia.py``: proveedor ficticio de /uvix/get_request_identity.
- ``ros2 run uvix_data uvix_data_node``: nodo instalado (GetPerson + CheckPermission).
- ``ros2 run uvix_data uvix_enroll_face_sim``: alta facial simulada.
- Este proceso: cliente rclpy.

Nunca toca la base habitual: aborta si la ruta efectiva no está en el temporal.
Uso (con el install cargado):

    python3 src/uvix_data/test/validar_permisos.py [--domain 79] [--conservar]
"""
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from validar_get_person import Validador  # noqa: E402

SIETE = ["deliver_item", "reminder_round", "find_person", "operational_report",
         "socialize_zone", "dispense_medication", "list_patients"]

PERSONAS = [  # person_id, display_name, role, active (ficticias)
    ("prueba_admin_01", "Admin Ficticio", 3, True),
    ("prueba_staff_juan", "Juan Ficticio", 2, True),
    ("prueba_staff_baja", "Personal de Baja", 2, False),
    ("prueba_paciente_maria", "María Ficticia", 1, True),
    ("prueba_paciente_ana", "Ana Ficticia", 1, True),
    ("prueba_paciente_beto", "Beto Ficticio", 1, True),
    ("prueba_paciente_lenta", "Lenta Ficticia", 1, True),
    ("prueba_paciente_mala", "Mala Calidad", 1, True),
    ("prueba_paciente_corta", "Captura Corta", 1, True),
]
PREFERENCIAS = [
    ("prueba_paciente_ana", "language", "es"), ("prueba_paciente_ana", "speech_rate", "slow"),
    ("prueba_paciente_ana", "form_of_address", "usted"),
    ("prueba_paciente_ana", "favorite_activity", "baile"),
    ("prueba_paciente_beto", "language", "en"), ("prueba_paciente_beto", "favorite_activity", "ajedrez"),
]

V, C_, U = 2, 1, 0
IDENTIDADES = {f"r-staff-{op}": {"person_id": "prueba_staff_juan", "status": V} for op in SIETE}
IDENTIDADES.update({
    "r-admin-desconocida": {"person_id": "prueba_admin_01", "status": V},
    "r-baja": {"person_id": "prueba_staff_baja", "status": V},
    "r-cand-entrega": {"person_id": "prueba_staff_juan", "status": C_},
    "r-cand-ayuda": {"person_id": "prueba_paciente_maria", "status": C_},
    "r-vencida": {"person_id": "prueba_staff_juan", "status": V, "ttl_s": -5},
    "r-desconocida": {"person_id": "", "status": U},
    "r-juan-entrega-maria": {"person_id": "prueba_staff_juan", "status": V},
    "r-maria-entrega-juan": {"person_id": "prueba_paciente_maria", "status": V},
    "r-admin-8": {"person_id": "prueba_admin_01", "status": V},
    "r-staff-8a": {"person_id": "prueba_staff_juan", "status": V},
    "r-staff-8b": {"person_id": "prueba_staff_juan", "status": V},
    "r-staff-8c": {"person_id": "prueba_staff_juan", "status": V},
    "r-staff-enroll": {"person_id": "prueba_staff_juan", "status": V},
    **{f"r-admin-enroll-{i}": {"person_id": "prueba_admin_01", "status": V} for i in range(1, 6)},
})
MUESTRAS = {
    "prueba_paciente_mala": [0.3, 0.2, 0.4, 0.1, 0.2, 0.3],
    "prueba_paciente_corta": [0.95, None],
    "prueba_paciente_lenta": [0.95] * 30,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", type=int, default=79)
    ap.add_argument("--conservar", action="store_true")
    args = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix="uvix_m105_perm_")
    v = Validador(args.domain, tmp)
    procs = {}
    print(f"Temporal: {tmp}\nROS_DOMAIN_ID={args.domain} "
          f"RMW_IMPLEMENTATION={os.environ.get('RMW_IMPLEMENTATION', '(por defecto)')}", flush=True)

    def lanzar(nombre, cmd):
        log = open(os.path.join(tmp, f"{nombre}.log"), "w")
        procs[nombre] = subprocess.Popen(cmd, cwd=tmp, env=v.env, stdout=log,
                                         stderr=subprocess.STDOUT, start_new_session=True)

    def parar(nombre):
        p = procs.get(nombre)
        if p is None or p.poll() is not None:
            return p.returncode if p else None
        os.killpg(p.pid, signal.SIGINT)
        try:
            return p.wait(10)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            return "colgado(SIGKILL)"

    def leer_log(nombre):
        with open(os.path.join(tmp, f"{nombre}.log")) as f:
            return f.read()

    os.environ["ROS_DOMAIN_ID"] = str(args.domain)
    import rclpy
    from rclpy.action import ActionClient
    from uvix_interfaces.action import EnrollFace
    from uvix_interfaces.srv import CheckPermission, GetPerson

    rclpy.init()
    cn = rclpy.create_node("validador_permisos")
    cli_gp = cn.create_client(GetPerson, "/uvix/get_person")
    cli_cp = cn.create_client(CheckPermission, "/uvix/check_permission")
    cli_ef = ActionClient(cn, EnrollFace, "/uvix/enroll_face")
    R = CheckPermission.Response
    ER = EnrollFace.Result

    def esperar(fut, t):
        rclpy.spin_until_future_complete(cn, fut, timeout_sec=t)
        return fut.result() if fut.done() else None

    def get_person(pid):
        return esperar(cli_gp.call_async(GetPerson.Request(person_id=pid)), 3.0)

    def check(rid, op):
        return esperar(cli_cp.call_async(CheckPermission.Request(request_id=rid, operation=op)), 6.0)

    def desc(r):
        return "sin respuesta" if r is None else (
            f"allowed={r.allowed} code={r.code} persona={r.evaluated_person_id or '-'} "
            f"rol={r.evaluated_role}")

    def enroll(pid, rid, cancelar_tras_s=None, requeridas=5):
        goal = EnrollFace.Goal(person_id=pid, request_id=rid,
                               consent_ref="consentimiento-ficticio-001", samples_required=requeridas)
        gh = esperar(cli_ef.send_goal_async(goal), 5.0)
        if gh is None or not gh.accepted:
            return None
        res_fut = gh.get_result_async()
        if cancelar_tras_s is not None:
            fin = time.monotonic() + cancelar_tras_s
            while time.monotonic() < fin:
                rclpy.spin_once(cn, timeout_sec=0.05)
            esperar(gh.cancel_goal_async(), 5.0)
        r = esperar(res_fut, 15.0)
        return r.result if r else None

    def plantillas():
        out = v.py("from people.models import FaceTemplate;"
                   "print(','.join(sorted(t.person.person_id+':'+t.status "
                   "for t in FaceTemplate.objects.all())))")
        return out.stdout.strip()

    try:
        ruta = v.ruta_efectiva()
        dentro = ruta.startswith(os.path.realpath(tmp) + os.sep)
        v.registrar("Ruta efectiva de la base dentro del temporal", f"bajo {tmp}", ruta, dentro)
        if not dentro:
            print("ABORTO: la base efectiva no es la temporal.")
            return 2
        r = v.migrar()
        v.registrar("Migraciones 0001-0005 sobre base vacía", "código 0",
                    f"código {r.returncode}", r.returncode == 0)
        v.py("from people.models import Person, PersonPreference;"
             f"[Person.objects.create(person_id=a,display_name=b,role=c,active=d) for a,b,c,d in {PERSONAS!r}];"
             f"[PersonPreference.objects.create(person=Person.objects.get(person_id=p),key=k,value=x) "
             f"for p,k,x in {PREFERENCIAS!r}]")
        with open(os.path.join(tmp, "identidades.json"), "w") as f:
            json.dump(IDENTIDADES, f)
        with open(os.path.join(tmp, "muestras.json"), "w") as f:
            json.dump(MUESTRAS, f)

        lanzar("identidad", [sys.executable, os.path.join(AQUI, "identidad_ficticia.py"),
                             os.path.join(tmp, "identidades.json")])
        lanzar("uvix_data", ["ros2", "run", "uvix_data", "uvix_data_node"])
        lanzar("enroll", ["ros2", "run", "uvix_data", "uvix_enroll_face_sim", "--ros-args",
                          "-p", "sim_periodo_s:=0.2", "-p", f"sim_muestras_file:={os.path.join(tmp, 'muestras.json')}"])
        ok = (cli_gp.wait_for_service(timeout_sec=20) and cli_cp.wait_for_service(timeout_sec=20)
              and cli_ef.wait_for_server(timeout_sec=20))
        v.registrar("Nodos instalados disponibles (ros2 run, otro proceso)",
                    "get_person, check_permission y enroll_face en <20 s",
                    "disponibles" if ok else "no aparecieron", ok)
        if not ok:
            return 1

        # ---- GetPerson con preferencias ----
        ana, beto, juan = get_person("prueba_paciente_ana"), get_person("prueba_paciente_beto"), \
            get_person("prueba_staff_juan")
        prefs = {n: {kv.key: kv.value for kv in r.person.preferences} if r else None
                 for n, r in (("ana", ana), ("beto", beto), ("juan", juan))}
        v.registrar("GetPerson: cada persona recibe solo sus preferencias",
                    "ana 4 propias, beto 2 propias, juan 0", json.dumps(prefs, ensure_ascii=False),
                    prefs == {"ana": {"language": "es", "speech_rate": "slow", "form_of_address": "usted",
                                      "favorite_activity": "baile"},
                              "beto": {"language": "en", "favorite_activity": "ajedrez"}, "juan": {}})
        r = get_person("no_existe_999")
        v.registrar("GetPerson: inexistente", "found=False role=0",
                    f"found={r.found} role={r.person.role}" if r else "sin respuesta",
                    r is not None and not r.found and r.person.role == 0)

        # ---- CheckPermission ----
        res = {op: check(f"r-staff-{op}", op) for op in SIETE}
        v.registrar("STAFF verificado: las siete operaciones", "allowed=True code=0 en las 7",
                    "; ".join(f"{op}:{desc(x)}" for op, x in res.items()),
                    all(x is not None and x.allowed and x.code == R.CODE_ALLOWED for x in res.values()))
        casos = [
            ("Operación desconocida (ADMIN)", "r-admin-desconocida", "abrir_puertas", R.CODE_UNKNOWN_OPERATION, False),
            ("Usuario desactivado", "r-baja", "chat", R.CODE_PERSON_INACTIVE, False),
            ("Identidad candidata para una entrega", "r-cand-entrega", "deliver_item", R.CODE_IDENTITY_NOT_VERIFIED, False),
            ("Excepción de ayuda con identidad candidata", "r-cand-ayuda", "attend_help_request", R.CODE_ALLOWED_CANDIDATE_HELP, True),
            ("Identidad vencida", "r-vencida", "deliver_item", R.CODE_IDENTITY_EXPIRED, False),
            ("Identidad desconocida", "r-desconocida", "attend_help_request", R.CODE_IDENTITY_NOT_VERIFIED, False),
            ("Petición sin verificación", "r-no-existe", "chat", R.CODE_IDENTITY_NOT_VERIFIED, False),
        ]
        for nombre, rid, op, code, allowed in casos:
            x = check(rid, op)
            v.registrar(f"CheckPermission: {nombre}", f"allowed={allowed} code={code}", desc(x),
                        x is not None and x.allowed == allowed and x.code == code)
        x = check("r-juan-entrega-maria", "deliver_item")
        y = check("r-maria-entrega-juan", "deliver_item")
        v.registrar("Se evalúa al solicitante, no al destinatario",
                    "Juan->María: permitido evaluando a Juan; María->Juan: denegado evaluando a María",
                    f"{desc(x)} | {desc(y)}",
                    x is not None and y is not None and x.allowed and x.evaluated_person_id == "prueba_staff_juan"
                    and not y.allowed and y.evaluated_person_id == "prueba_paciente_maria"
                    and y.code == R.CODE_NOT_AUTHORIZED)

        # ---- Octava operación (escrita por otro proceso en la misma base) ----
        v.py("from people.models import Capability;"
             "Capability.objects.create(code='prueba_octava_operacion', name='Octava (ficticia)')")
        a, s1 = check("r-admin-8", "prueba_octava_operacion"), check("r-staff-8a", "prueba_octava_operacion")
        v.py("from people.models import Capability, RolePermission;"
             "RolePermission.objects.create(role=2, capability=Capability.objects.get(code='prueba_octava_operacion'))")
        s2 = check("r-staff-8b", "prueba_octava_operacion")
        v.py("from people.models import RolePermission;"
             "RolePermission.objects.filter(role=2, capability__code='prueba_octava_operacion').delete()")
        s3 = check("r-staff-8c", "prueba_octava_operacion")
        v.registrar("Octava operación: ADMIN inmediato; STAFF solo con concesión",
                    "admin 0; staff 10 -> concesión 0 -> revocación 10",
                    f"admin {desc(a)} | staff {desc(s1)} | concedida {desc(s2)} | revocada {desc(s3)}",
                    None not in (a, s1, s2, s3) and a.code == 0 and s1.code == 10
                    and s2.code == 0 and s3.code == 10)

        # ---- EnrollFace simulado ----
        ok_r = enroll("prueba_paciente_ana", "r-admin-enroll-1")
        mala = enroll("prueba_paciente_mala", "r-admin-enroll-2")
        corta = enroll("prueba_paciente_corta", "r-admin-enroll-3")
        canc = enroll("prueba_paciente_lenta", "r-admin-enroll-4", cancelar_tras_s=0.7, requeridas=20)
        staff = enroll("prueba_paciente_beto", "r-staff-enroll")

        def d(x):
            return "sin resultado" if x is None else (
                f"code={x.result_code} enrolled={x.enrolled} muestras={x.samples_accepted} "
                f"template={'sí' if x.template_id else 'no'}")
        v.registrar("EnrollFace: alta correcta", "RESULT_ENROLLED, template_id", d(ok_r),
                    ok_r is not None and ok_r.result_code == ER.RESULT_ENROLLED and ok_r.enrolled
                    and ok_r.template_id.startswith("ftpl-"))
        v.registrar("EnrollFace: calidad insuficiente", "RESULT_LOW_QUALITY, sin alta", d(mala),
                    mala is not None and mala.result_code == ER.RESULT_LOW_QUALITY and not mala.enrolled)
        v.registrar("EnrollFace: registro incompleto (rostro perdido)", "RESULT_INCOMPLETE, sin alta",
                    d(corta), corta is not None and corta.result_code == ER.RESULT_INCOMPLETE
                    and not corta.enrolled)
        v.registrar("EnrollFace: cancelación", "RESULT_CANCELED, sin alta", d(canc),
                    canc is not None and canc.result_code == ER.RESULT_CANCELED and not canc.enrolled)
        v.registrar("EnrollFace: STAFF sin concesión enroll_face", "RESULT_NOT_AUTHORIZED", d(staff),
                    staff is not None and staff.result_code == ER.RESULT_NOT_AUTHORIZED)
        filas = plantillas()
        v.registrar("Sin altas parciales en la base", "solo prueba_paciente_ana:active", filas,
                    filas == "prueba_paciente_ana:active")
        r = get_person("prueba_paciente_ana")
        v.registrar("GetPerson no expone plantillas", "mismos 5 campos y 4 preferencias",
                    f"campos={sorted(type(r.person).get_fields_and_field_types())}" if r else "sin respuesta",
                    r is not None and set(type(r.person).get_fields_and_field_types())
                    == {"person_id", "display_name", "role", "active", "preferences"})

        # ---- Proveedor de identidad no disponible ----
        parar("identidad")
        t0 = time.monotonic()
        x = check("r-staff-deliver_item", "deliver_item")
        dt = time.monotonic() - t0
        v.registrar("Proveedor de identidad no disponible",
                    "allowed=False code=20 (sin decisión), dentro del timeout",
                    f"{desc(x)} en {dt:.1f} s",
                    x is not None and not x.allowed and x.code == R.CODE_IDENTITY_UNAVAILABLE)

        # ---- Cierre ----
        rc1, rc2 = parar("uvix_data"), parar("enroll")
        logs = leer_log("uvix_data") + leer_log("enroll")
        v.registrar("Cierre con Ctrl+C", "código 0 en ambos nodos y sin traceback",
                    f"uvix_data={rc1} enroll={rc2} traceback={'Traceback' in logs}",
                    rc1 == 0 and rc2 == 0 and "Traceback" not in logs)
    finally:
        for n in list(procs):
            parar(n)
        cn.destroy_node()
        rclpy.try_shutdown()
        with open(os.path.join(tmp, "resultados.json"), "w") as f:
            json.dump(v.resultados, f, ensure_ascii=False, indent=2)

    fallos = [r for r in v.resultados if r["estado"] != "PASÓ"]
    print(f"\nResumen: {len(v.resultados) - len(fallos)}/{len(v.resultados)} PASÓ")
    if args.conservar or fallos:
        print(f"Logs y resultados conservados en {tmp}")
    else:
        shutil.rmtree(tmp, ignore_errors=True)
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
