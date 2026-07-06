# tests/humo_sidecar.py
# Prueba de humo: levanta el sidecar en un subproceso, espera a que este 'listo' y verifica endpoints reales.
import subprocess                                     # para lanzar uvicorn
import sys                                            # ejecutable de python actual
import time                                           # esperas
import os                                             # rutas
import urllib.request                                 # cliente HTTP simple
import urllib.error                                   # errores HTTP
import json                                           # parseo de respuestas

RAIZ = os.path.dirname(os.path.dirname(__file__))     # raiz del proyecto (carpeta de api_server.py)

def get(ruta):                                        # helper GET que devuelve dict
    with urllib.request.urlopen("http://127.0.0.1:8000" + ruta, timeout=5) as r:  # abre la URL
        return json.loads(r.read().decode())          # parsea el JSON

def post(ruta, cuerpo):                               # helper POST con JSON
    datos = json.dumps(cuerpo).encode()               # serializa el cuerpo
    req = urllib.request.Request("http://127.0.0.1:8000" + ruta, data=datos,       # arma la peticion
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:# ejecuta
        return json.loads(r.read().decode())          # devuelve el JSON

def main():                                           # rutina principal de humo
    proc = subprocess.Popen(                          # lanza el sidecar
        [sys.executable, "-m", "uvicorn", "api_server:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=RAIZ)                                      # cwd = raiz para que resuelvan los imports
    try:
        # Espera a que el motor este 'listo' (entrena el modelo real).
        for _ in range(60):                           # hasta ~60 s
            try:
                if get("/health").get("estado") == "listo":  # consulta salud
                    break                             # listo: continua
            except Exception:                         # aun no responde
                pass
            time.sleep(1)                             # espera 1 s
        else:
            raise SystemExit("El sidecar no llego a 'listo' a tiempo")  # timeout

        # Verifica landed-cost (math conocida).
        lc = post("/landed-cost", {"fob": 10000, "flete": 1500, "seguro": 300,
                                   "arancel": 12, "tasa": 1, "iva": 16, "gastos": 0})
        assert round(lc["cif"], 2) == 11800.0, "CIF incorrecto"        # valida CIF
        # Verifica predict-eta (con el modelo real ya entrenado).
        eta = post("/predict-eta", {"origen": "Miami", "via": "Marítimo", "aduana": "La Guaira",
                                    "operador": "Maersk", "carga": "Textil y Calzado", "mes": 6})
        assert "dias_total" in eta, "Falta dias_total"                 # valida estructura
        # Verifica dashboard-summary.
        ds = get("/dashboard-summary")                # KPIs
        assert ds["registros_historicos"] > 0, "Sin registros historicos"  # valida datos
        print("HUMO OK:", {"cif": lc["cif"], "eta_total": round(eta["dias_total"], 1),
                           "historicos": ds["registros_historicos"]})  # resumen
    finally:
        proc.terminate()                              # detiene el sidecar
        try: proc.wait(timeout=5)                     # espera cierre limpio
        except Exception: proc.kill()                 # fuerza si no cierra

if __name__ == "__main__":                            # ejecucion directa
    main()                                            # corre la prueba
