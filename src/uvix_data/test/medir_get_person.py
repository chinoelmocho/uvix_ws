#!/usr/bin/python3
"""Mediciones de recursos de /uvix/get_person (M1-05).

Arranca el nodo instalado con ``ros2 run`` sobre una base temporal con
personas ficticias (igual que validar_get_person.py) y mide sobre el
proceso Python del nodo:

- RSS (VmRSS, MiB) tras el arranque, tras la primera consulta y tras cada tanda.
- CPU en reposo (% de un núcleo) durante una ventana sin llamadas.
- Latencia de ida y vuelta (ms) vista por un cliente rclpy persistente.

Uso (con el install ya cargado con ``source``):

    python3 src/uvix_data/test/medir_get_person.py --domain 77 \
        --tandas 5 --llamadas 200 --reposo 30 --json salida.json
"""
import argparse
import json
import os
import platform
import shutil
import signal
import statistics
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validar_get_person import Validador  # noqa: E402

TICKS = os.sysconf("SC_CLK_TCK")


def rss_mib(pid):
    with open(f"/proc/{pid}/status") as f:
        for linea in f:
            if linea.startswith("VmRSS:"):
                return int(linea.split()[1]) / 1024.0
    return float("nan")


def cpu_s(pid):
    with open(f"/proc/{pid}/stat") as f:
        campos = f.read().rsplit(")", 1)[1].split()
    return (int(campos[11]) + int(campos[12])) / TICKS  # utime + stime


def cpu_reposo(pid, ventana):
    c0, t0 = cpu_s(pid), time.monotonic()
    time.sleep(ventana)
    return 100.0 * (cpu_s(pid) - c0) / (time.monotonic() - t0)


def equipo():
    modelo = "desconocido"
    try:
        with open("/proc/cpuinfo") as f:
            claves = dict(
                (k.strip().lower(), val.strip())
                for k, _, val in (linea.partition(":") for linea in f) if val)
        modelo = claves.get("model name") or claves.get("hardware") or modelo
    except OSError:
        pass
    try:
        with open("/proc/device-tree/model") as f:  # Jetson
            modelo = f.read().strip("\x00\n") + f" ({modelo})"
    except OSError:
        pass
    with open("/proc/meminfo") as f:
        mem = int(f.readline().split()[1]) / 1024 / 1024
    return {
        "cpu": modelo, "nucleos": os.cpu_count(), "ram_total_gib": round(mem, 1),
        "kernel": platform.release(), "python": platform.python_version(),
        "rmw": os.environ.get("RMW_IMPLEMENTATION", "(por defecto)"),
        "ros_distro": os.environ.get("ROS_DISTRO", "?"),
    }


def resumen(lat_ms):
    s = sorted(lat_ms)
    return {
        "n": len(s), "min": s[0], "p50": statistics.median(s),
        "p95": s[min(len(s) - 1, int(round(0.95 * (len(s) - 1))))],
        "max": s[-1], "media": statistics.fmean(s),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", type=int, default=77)
    ap.add_argument("--tandas", type=int, default=5)
    ap.add_argument("--llamadas", type=int, default=200, help="llamadas por tanda")
    ap.add_argument("--reposo", type=float, default=30.0, help="ventana de CPU en reposo (s)")
    ap.add_argument("--json", help="guardar resultados en este archivo")
    args = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix="uvix_m105_med_")
    v = Validador(args.domain, tmp)
    ruta = v.ruta_efectiva()
    if not ruta.startswith(os.path.realpath(tmp) + os.sep):
        print(f"ABORTO: la base efectiva {ruta} no es la temporal.")
        return 2
    assert v.migrar().returncode == 0
    v.sembrar()

    os.environ["ROS_DOMAIN_ID"] = str(args.domain)
    import rclpy
    from uvix_interfaces.srv import GetPerson

    rclpy.init()
    nodo_cli = rclpy.create_node("medidor_get_person")
    cli = nodo_cli.create_client(GetPerson, "/uvix/get_person")

    def llamar(person_id):
        req = GetPerson.Request()
        req.person_id = person_id
        t0 = time.perf_counter()
        fut = cli.call_async(req)
        rclpy.spin_until_future_complete(nodo_cli, fut, timeout_sec=5.0)
        dt = (time.perf_counter() - t0) * 1000.0
        if not fut.done() or not fut.result().found:
            raise RuntimeError(f"llamada fallida para {person_id}")
        return dt

    res = {"equipo": equipo(), "parametros": vars(args), "base": ruta}
    try:
        v.arrancar()
        if not cli.wait_for_service(timeout_sec=20.0):
            raise RuntimeError("el servicio no apareció:\n" + v.log())
        pid = v.nodo_pid()
        time.sleep(3.0)  # asentar tras el arranque
        res["rss_arranque_mib"] = rss_mib(pid)
        res["cpu_reposo_inicial_pct"] = cpu_reposo(pid, args.reposo)

        res["primera_llamada_ms"] = llamar("prueba_staff_01")
        res["rss_tras_primera_mib"] = rss_mib(pid)

        res["tandas"] = []
        for i in range(args.tandas):
            lat = [llamar("prueba_staff_01" if k % 2 == 0 else "prueba_paciente_02")
                   for k in range(args.llamadas)]
            t = resumen(lat)
            t["tanda"] = i + 1
            t["rss_mib"] = rss_mib(pid)
            res["tandas"].append(t)
        res["cpu_reposo_final_pct"] = cpu_reposo(pid, args.reposo)
        res["rss_final_mib"] = rss_mib(pid)
    finally:
        v.detener(signal.SIGINT)
        nodo_cli.destroy_node()
        rclpy.try_shutdown()

    eq = res["equipo"]
    print(f"Equipo: {eq['cpu']} · {eq['nucleos']} núcleos · {eq['ram_total_gib']} GiB · "
          f"kernel {eq['kernel']} · ROS {eq['ros_distro']} · {eq['rmw']}")
    print(f"RSS tras arranque:        {res['rss_arranque_mib']:.1f} MiB")
    print(f"CPU en reposo inicial:    {res['cpu_reposo_inicial_pct']:.2f} % de un núcleo "
          f"({args.reposo:.0f} s)")
    print(f"Primera llamada:          {res['primera_llamada_ms']:.2f} ms")
    print(f"RSS tras primera llamada: {res['rss_tras_primera_mib']:.1f} MiB")
    print("Tanda | n   | min ms | p50 ms | p95 ms | max ms | media ms | RSS MiB")
    for t in res["tandas"]:
        print(f"{t['tanda']:5d} | {t['n']:3d} | {t['min']:6.2f} | {t['p50']:6.2f} | "
              f"{t['p95']:6.2f} | {t['max']:6.2f} | {t['media']:8.2f} | {t['rss_mib']:.1f}")
    print(f"CPU en reposo final:      {res['cpu_reposo_final_pct']:.2f} % de un núcleo")
    print(f"RSS final:                {res['rss_final_mib']:.1f} MiB")
    if args.json:
        with open(args.json, "w") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
