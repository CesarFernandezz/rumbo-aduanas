# tests/test_api_server.py
import os                                             # para setear variables de entorno antes de importar
os.environ["LOGIIA_SKIP_TRAIN"] = "1"                 # evita que el startup entrene el modelo real en tests
from fastapi.testclient import TestClient             # cliente de pruebas de FastAPI
import api_server                                     # importa el modulo del sidecar (raiz del proyecto)
from api_server import app                            # la instancia FastAPI a probar

client = TestClient(app)                              # cliente HTTP simulado sobre la app

def test_health_devuelve_estado():                    # verifica que /health responde con un estado
    r = client.get("/health")                         # llamada GET a /health
    assert r.status_code == 200                       # debe responder 200 OK
    assert "estado" in r.json()                       # el JSON debe incluir la clave 'estado'

def test_landed_cost_calcula_cif_y_total():           # valida la matematica del landed cost real del backend
    r = client.post("/landed-cost", json={            # envia los parametros financieros
        "fob": 10000, "flete": 1500, "seguro": 300,   # base FOB + flete + seguro
        "arancel": 12, "tasa": 1, "iva": 16, "gastos": 0,  # porcentajes de impuestos y gastos locales
    })
    d = r.json()                                       # respuesta con el desglose
    assert round(d["cif"], 2) == 11800.0               # CIF = 10000 + 1500 + 300
    assert d["landed_cost"] > d["cif"]                 # el total debe superar al CIF (por impuestos)
