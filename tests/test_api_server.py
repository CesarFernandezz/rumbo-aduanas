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
