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

def test_token_requerido_cuando_esta_configurado():   # si hay RUMBO_TOKEN, se exige en cada peticion (menos /health)
    api_server.TOKEN_ESPERADO = "secreto-de-prueba"   # simula que main.js configuro un token
    try:
        sin = client.post("/landed-cost", json={"fob": 1000})  # peticion SIN token
        assert sin.status_code == 401                 # debe rechazarse
        con = client.post("/landed-cost", json={"fob": 1000}, headers={"X-Rumbo-Token": "secreto-de-prueba"})  # CON token
        assert con.status_code == 200                 # debe aceptarse
        salud = client.get("/health")                 # /health queda libre (el splash lo usa antes del token)
        assert salud.status_code == 200
    finally:
        api_server.TOKEN_ESPERADO = None              # restaura para no afectar otros tests

def test_landed_cost_calcula_cif_y_total():           # valida la matematica del landed cost real del backend
    r = client.post("/landed-cost", json={            # envia los parametros financieros
        "fob": 10000, "flete": 1500, "seguro": 300,   # base FOB + flete + seguro
        "arancel": 12, "tasa": 1, "iva": 16, "gastos": 0,  # porcentajes de impuestos y gastos locales
    })
    d = r.json()                                       # respuesta con el desglose
    assert round(d["cif"], 2) == 11800.0               # CIF = 10000 + 1500 + 300
    assert d["landed_cost"] > d["cif"]                 # el total debe superar al CIF (por impuestos)

def test_login_credenciales_malas_devuelve_ok_false():  # login con credenciales inexistentes
    r = client.post("/login", json={"username": "nadie_zzz", "password": "malaclave"})  # usuario que no existe
    assert r.json()["ok"] is False                       # debe rechazar el acceso

def test_login_usuario_semilla_funciona():               # el login real del admin semilla debe funcionar (no crashear)
    # Usa el context manager para disparar el evento startup -> crea/siembra la BD (admin hasheado) sin entrenar el modelo.
    with TestClient(app) as c:                            # 'with' dispara @app.on_event('startup')
        r = c.post("/login", json={"username": "admin", "password": "admin123"})  # credenciales semilla documentadas
        assert r.json()["ok"] is True                    # deben ser validas (regresion del bug de hash en texto plano)

def test_predict_eta_con_modelo_stub():               # prueba la estructura de la prediccion sin entrenar de verdad
    class ModeloFalso:                                # modelo simulado que siempre predice 10 dias
        def predict(self, X):                         # imita la interfaz .predict de sklearn
            return [10.0]                             # devuelve una lista con un valor
    class EncoderFalso:                               # encoder simulado que siempre devuelve 0
        def transform(self, v):                       # imita LabelEncoder.transform
            return [0]                                # codigo ficticio
    api_server.MOTOR["estado"] = "listo"              # marcamos el motor como listo
    api_server.MOTOR["modelos"] = {k: ModeloFalso() for k in ["total", "transito", "fondeo", "aduana"]}  # 4 modelos
    api_server.MOTOR["encoders"] = {k: EncoderFalso() for k in            # 5 encoders esperados
        ["origen", "aduana_destino", "via", "operador", "tipo_carga"]}
    r = client.post("/predict-eta", json={            # peticion de prediccion
        "origen": "Miami", "via": "Maritimo", "aduana": "La Guaira",
        "operador": "Maersk", "carga": "Textil y Calzado", "mes": 6,
    })
    d = r.json()                                       # respuesta con el desglose
    assert d["dias_total"] == 10.0                     # el modelo falso predice 10
    assert {"dias_total", "dias_transito", "dias_fondeo", "dias_aduana", "distancia_km"} <= set(d.keys())  # claves

def test_eta_historico_devuelve_lista():              # el grafico historico debe devolver una lista por operador
    r = client.get("/eta-historico", params={"origen": "Miami"})  # agregado para origen Miami
    assert r.status_code == 200                        # 200 OK
    assert isinstance(r.json(), list)                  # debe ser una lista (posiblemente vacia)

def test_vuce_pdf_genera_archivo(tmp_path):           # verifica que /vuce-pdf escribe un PDF en la ruta dada
    destino = str(tmp_path / "dictamen_test.pdf")     # ruta temporal de salida
    r = client.post("/vuce-pdf", json={               # peticion con un HTML minimo
        "regimen": "IMPORTACIÓN", "consulta": "cafe en grano",
        "html": "<h3>Guia</h3><ul><li>Paso 1</li></ul>", "ruta": destino,
    })
    assert r.json()["ok"] is True                      # debe reportar exito
    assert os.path.exists(destino)                     # el archivo PDF debe existir en disco

def test_dashboard_summary_tiene_kpis():              # el resumen del Inicio debe traer KPIs del historico
    r = client.get("/dashboard-summary")              # peticion del resumen
    d = r.json()                                       # respuesta agregada
    assert d["registros_historicos"] > 0               # el CSV tiene datos historicos
    assert "eta_promedio" in d                          # promedio general de dias reales
    assert isinstance(d["por_aduana"], list)            # distribucion por aduana (real)
    assert isinstance(d["por_via"], list)               # distribucion por via (real)
    assert "dias_transito_promedio" in d                # promedio de dias en transito (real)
    assert "dias_aduana_promedio" in d                  # promedio de dias en aduana (real)
    assert 0 <= d["pct_a_tiempo"] <= 100                # % de puntualidad, en rango valido
    assert len(d["por_mes"]) == 12                      # volumen por mes: 12 entradas (enero..diciembre)

def test_historial_devuelve_lista():                  # el historial de operaciones reales debe devolver una lista
    r = client.get("/historial?usuario=admin&limite=3")  # operaciones recientes del usuario admin
    assert r.status_code == 200                        # nunca 500 (aun si no hay filas)
    assert isinstance(r.json(), list)                  # siempre una lista (posiblemente vacia)

def test_landed_guarda_y_se_recupera_del_historial():  # el bucle real: calcular -> se guarda -> se recupera
    with TestClient(app) as c:                         # 'with' dispara startup (crea las tablas)
        c.post("/landed-cost", json={"fob": 5000, "usuario": "admin"})  # calcula un landed cost como 'admin'
        h = c.get("/historial?usuario=admin&modulo=CALCULO_FINANCIERO&limite=1").json()  # busca su ultimo calculo
        assert len(h) >= 1                             # debe existir la operacion recien guardada
        assert "Total" in h[0]["descripcion"]          # con el formato "FOB: ... | Total: ..." (dato real procesado)
