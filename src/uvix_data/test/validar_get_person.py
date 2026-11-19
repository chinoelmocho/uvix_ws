#!/usr/bin/python3
"""Validación de extremo a extremo de /uvix/get_person (M1-05).

Arranca el ejecutable instalado con ``ros2 run`` sobre una base SQLite
temporal con personas ficticias y lo consulta desde este proceso con un
cliente rclpy persistente. Nunca toca la base habitual
(~/.local/share/uvix/uvix.sqlite3): el script aborta si la ruta efectiva
no queda dentro del directorio temporal.

Requisitos: haber hecho ``source`` del install que contiene uvix_data y
uvix_interfaces. Uso:

    python3 src/uvix_data/test/validar_get_person.py [--domain 77] [--conservar]

Sale con código 0 solo si todos los casos pasan.
"""
import argparse
import json
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time

PERSONAS = [
    # person_id, display_name, role, active  (datos ficticios)
    ("prueba_staff_01", "Cuidadora Ficticia", 2, True),
    ("prueba_paciente_02", "Residente Ficticio", 1, False),
]

DJANGO_PREAMBULO = (
    "import os;"
    "os.environ.setdefault('DJANGO_SETTINGS_MODULE','uvix_data_project.settings');"
    "import django;django.setup();"
)


class Validador:
    def __init__(self, domain, tmp):
        self.tmp = tmp
        self.db = os.path.join(tmp, "datos", "uvix_prueba.sqlite3")
        self.env = dict(os.environ)
        # Django y ros2_django suelen estar en el "user site" (pip --user);
        # se fija antes de cambiar HOME para no perderlos.
        self.env.setdefault("PYTHONUSERBASE", os.path.expanduser("~/.local"))
        self.env.update({
            "ROS_DOMAIN_ID": str(domain),
            "UVIX_DATA_DB": self.db,
            # Defensa adicional: si la versión instalada ignora UVIX_DATA_DB,
            # la ruta por defecto (Path.home()) también cae en el temporal.
            "HOME": os.path.join(tmp, "home"),
            "ROS_LOG_DIR": os.path.join(tmp, "ros_log"),
            "PYTHONUNBUFFERED": "1",
        })
        os.makedirs(self.env["HOME"], exist_ok=True)
        self.resultados = []
        self.proc = None
        self.log_path = None
        self._n_log = 0

    # ---------- utilidades ----------
    def py(self, codigo, db=None, check=True):
        env = dict(self.env)
        if db:
            env["UVIX_DATA_DB"] = db
        r = subprocess.run(
            [sys.executable, "-c", DJANGO_PREAMBULO + codigo],
            cwd=self.tmp, env=env, capture_output=True, text=True)
        if check and r.returncode != 0:
            raise RuntimeError(f"Fallo al ejecutar Django:\n{r.stderr}")
        return r

    def ruta_efectiva(self, db=None):
        out = self.py(
            "from django.conf import settings;"
            "print(settings.DATABASES['default']['NAME'])", db=db)
        return os.path.realpath(out.stdout.strip())

    def migrar(self, db=None):
        env = dict(self.env)
        if db:
            env["UVIX_DATA_DB"] = db
        return subprocess.run(
            [sys.executable, "-m", "django", "migrate", "--noinput",
             "--settings=uvix_data_project.settings"],
            cwd=self.tmp, env=env, capture_output=True, text=True)

    def sembrar(self):
        filas = ",".join(repr(p) for p in PERSONAS)
        self.py(
            "from people.models import Person;"
            f"[Person.objects.create(person_id=a,display_name=b,role=c,active=d) for a,b,c,d in [{filas}]];"
            "print(Person.objects.count())")

    def arrancar(self, db=None):
        env = dict(self.env)
        if db:
            env["UVIX_DATA_DB"] = db
        self._n_log += 1
        self.log_path = os.path.join(self.tmp, f"nodo_{self._n_log}.log")
        log = open(self.log_path, "w")
        # Sesión propia: las señales se envían al grupo como haría la terminal.
        self.proc = subprocess.Popen(
            ["ros2", "run", "uvix_data", "uvix_data_node"],
            cwd=self.tmp, env=env, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True)
        return self.proc

    def log(self):
        with open(self.log_path) as f:
            return f.read()

    def nodo_pid(self):
        """PID del proceso Python del nodo (hijo de ``ros2 run``)."""
        try:
            with open(f"/proc/{self.proc.pid}/task/{self.proc.pid}/children") as f:
                hijos = f.read().split()
            return int(hijos[0]) if hijos else None
        except OSError:
            return None

    def detener(self, sig=signal.SIGINT, timeout=10.0, solo_nodo=False):
        """Ctrl+C de terminal = señal al grupo. ``solo_nodo`` envía la señal
        solo al proceso del nodo (como ros2 launch o systemd); ``ros2 run``
        devuelve entonces el código de salida real del nodo."""
        if self.proc is None or self.proc.poll() is not None:
            return self.proc.returncode if self.proc else None
        pid = self.nodo_pid() if solo_nodo else None
        if pid:
            os.kill(pid, sig)
        else:
            os.killpg(self.proc.pid, sig)
        try:
            return self.proc.wait(timeout)
        except subprocess.TimeoutExpired:
            os.killpg(self.proc.pid, signal.SIGKILL)
            self.proc.wait()
            return "colgado(SIGKILL)"

    def registrar(self, caso, esperado, observado, ok, estado=None):
        estado = estado or ("PASÓ" if ok else "FALLÓ")
        self.resultados.append(
            {"caso": caso, "esperado": esperado, "observado": observado, "estado": estado})
        print(f"[{estado}] {caso}\n    esperado: {esperado}\n    observado: {observado}", flush=True)


def describir(resp):
    if resp is None:
        return "sin respuesta (timeout)"
    p = resp.person
    return (f"status={resp.status} found={resp.found} person_id={p.person_id!r} display_name={p.display_name!r} "
            f"role={p.role} active={p.active} preferences={len(p.preferences)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", type=int, default=77)
    ap.add_argument("--conservar", action="store_true", help="no borrar el temporal")
    ap.add_argument("--timeout", type=float, default=3.0, help="timeout por llamada (s)")
    args = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix="uvix_m105_")
    v = Validador(args.domain, tmp)
    print(f"Temporal: {tmp}\nROS_DOMAIN_ID={args.domain} "
          f"RMW_IMPLEMENTATION={os.environ.get('RMW_IMPLEMENTATION', '(por defecto)')}", flush=True)

    os.environ["ROS_DOMAIN_ID"] = str(args.domain)
    import rclpy
    from uvix_interfaces.msg import Person
    from uvix_interfaces.srv import GetPerson

    rclpy.init()
    cli_node = rclpy.create_node("validador_get_person")
    cli = cli_node.create_client(GetPerson, "/uvix/get_person")

    def esperar_servicio(t=20.0):
        return cli.wait_for_service(timeout_sec=t)

    def llamar(pid):
        req = GetPerson.Request()
        req.person_id = pid
        fut = cli.call_async(req)
        rclpy.spin_until_future_complete(cli_node, fut, timeout_sec=args.timeout)
        if not fut.done():
            cli.remove_pending_request(fut)
            return None
        return fut.result()

    try:
        # ---- 0. Ruta efectiva antes de migrar ----
        ruta = v.ruta_efectiva()
        dentro = ruta.startswith(os.path.realpath(tmp) + os.sep)
        v.registrar("Ruta efectiva de la base dentro del temporal",
                    f"bajo {tmp}", f"{ruta} (UVIX_DATA_DB respetada: {ruta == os.path.realpath(v.db)})",
                    dentro)
        if not dentro:
            print("ABORTO: la base efectiva no es la temporal; no se migra nada.")
            return 2

        r = v.migrar()
        v.registrar("Migraciones sobre base vacía", "migrate termina con código 0",
                    f"código {r.returncode}", r.returncode == 0)
        v.sembrar()

        # ---- 1. Arranque y casos funcionales ----
        v.arrancar()
        ok = esperar_servicio()
        v.registrar("Arranque con ros2 run (fuera del repo)", "servicio disponible en <20 s",
                    "disponible" if ok else "no apareció\n" + v.log(), ok)

        resp = llamar("prueba_staff_01")
        v.registrar("Persona activa",
                    "found=True, id/nombre/rol=2 correctos, active=True",
                    describir(resp),
                    resp is not None and resp.found and resp.person.person_id == "prueba_staff_01"
                    and resp.person.display_name == "Cuidadora Ficticia"
                    and resp.person.role == Person.ROLE_STAFF and resp.person.active)

        resp = llamar("prueba_paciente_02")
        v.registrar("Persona desactivada",
                    "found=True, conserva id/nombre/rol=1, active=False",
                    describir(resp),
                    resp is not None and resp.found and resp.person.person_id == "prueba_paciente_02"
                    and resp.person.display_name == "Residente Ficticio"
                    and resp.person.role == Person.ROLE_PATIENT and not resp.person.active)

        resp = llamar("no_existe_999")
        v.registrar("Identificador inexistente",
                    "status=NOT_FOUND(1), found=False, role=ROLE_UNKNOWN(0)", describir(resp),
                    resp is not None and not resp.found and resp.person.role == Person.ROLE_UNKNOWN
                    and resp.status == GetPerson.Response.STATUS_NOT_FOUND)

        resp = llamar("prueba_staff_01")
        v.registrar("preferences de una persona sin preferencias guardadas",
                    "lista vacía (comportamiento genérico)",
                    f"{len(resp.person.preferences)} elementos" if resp else "sin respuesta",
                    resp is not None and len(resp.person.preferences) == 0)

        # ---- 2. Cierre normal y reinicio ----
        rc = v.detener(signal.SIGINT)
        log = v.log()
        v.registrar("Cierre con Ctrl+C (SIGINT al grupo)",
                    "código 0 y sin traceback",
                    f"código {rc}; traceback={'Traceback' in log}",
                    rc == 0 and "Traceback" not in log)

        v.arrancar()
        ok = esperar_servicio()
        resp = llamar("prueba_staff_01") if ok else None
        v.registrar("Reinicio recupera el mismo registro",
                    "found=True, mismos datos tras reiniciar", describir(resp),
                    resp is not None and resp.found and resp.person.display_name == "Cuidadora Ficticia"
                    and resp.person.role == Person.ROLE_STAFF and resp.person.active)

        rc = v.detener(signal.SIGTERM, solo_nodo=True)
        log = v.log()
        v.registrar("Cierre con SIGTERM al proceso del nodo",
                    "código 0 y sin traceback",
                    f"código {rc}; traceback={'Traceback' in log}",
                    rc == 0 and "Traceback" not in log)

        # ---- 3. Base sin migraciones (archivo inexistente y archivo vacío) ----
        for variante in ("inexistente", "vacía"):
            caso = f"Base sin migraciones (archivo {variante})"
            db_vacia = os.path.join(tmp, "datos", f"sin_migrar_{variante[:3]}.sqlite3")
            os.makedirs(os.path.dirname(db_vacia), exist_ok=True)
            if variante == "vacía":
                open(db_vacia, "w").close()
            ruta2 = v.ruta_efectiva(db=db_vacia)
            if ruta2 != os.path.realpath(db_vacia):
                v.registrar(caso, "nodo no responde found=False",
                            f"la versión instalada no permite elegir otra base ({ruta2})",
                            False, estado="NO EJECUTADA")
                continue
            v.arrancar(db=db_vacia)
            disp = esperar_servicio(8.0)
            time.sleep(0.5)
            vivo = v.proc.poll() is None
            resp = llamar("prueba_staff_01") if (disp and vivo) else None
            time.sleep(1.0)
            rc = v.proc.poll()
            log = v.log()
            msg_claro = "migrate" in log
            v.registrar(caso,
                        "no ofrece el servicio ni responde found=False; log claro y código ≠0",
                        f"servicio_disponible={disp and vivo}; respuesta={describir(resp)}; "
                        f"código={rc}; menciona 'migrate'={msg_claro}; traceback={'Traceback' in log}",
                        resp is None and rc not in (None, 0) and msg_claro)
            v.detener(signal.SIGINT)

        # ---- 4. Error de almacenamiento en marcha ----
        v.arrancar()
        esperar_servicio()
        con = sqlite3.connect(ruta)
        con.execute("ALTER TABLE people_person RENAME TO people_person_oculta")
        con.commit()
        resp = llamar("prueba_staff_01")
        time.sleep(0.5)
        vivo = v.proc.poll() is None
        log = v.log()
        v.registrar("Error de almacenamiento en marcha (tabla inaccesible)",
                    "status=UNAVAILABLE(2), nunca NOT_FOUND; error en el log; el nodo sigue vivo",
                    f"respuesta={describir(resp)}; nodo_vivo={vivo}; "
                    f"log menciona registro no disponible={'no disponible' in log}",
                    resp is not None and resp.status == GetPerson.Response.STATUS_UNAVAILABLE
                    and not resp.found and vivo and "no disponible" in log)
        con.execute("ALTER TABLE people_person_oculta RENAME TO people_person")
        con.commit()
        con.close()
        resp = llamar("prueba_staff_01")
        v.registrar("Recuperación tras el error de almacenamiento",
                    "el mismo nodo vuelve a responder status=OK", describir(resp),
                    resp is not None and resp.status == GetPerson.Response.STATUS_OK and resp.found)
        rc = v.detener(signal.SIGINT)
        v.registrar("Cierre tras el error", "código 0", f"código {rc}", rc == 0)

    finally:
        v.detener(signal.SIGINT)
        cli_node.destroy_node()
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
