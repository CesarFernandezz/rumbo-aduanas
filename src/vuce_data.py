# Base de datos de conocimiento simplificada para la VUCE en Venezuela
NORMATIVA_VUCE = {
    "Alimentos y Bebidas": {
        "ente": "MINSALUD (SACS) / INSAI",
        "permisos": [
            "Registro Sanitario de Alimentos.",
            "Permiso de Importación Sanitario.",
            "Certificado Fitosanitario de Origen (si aplica)."
        ],
        "base_legal": "Providencia SACS y regulaciones concurrentes del MPPS.",
        "dias_promedio_tramite": 15,
        "nota_alerta": "Requiere inspección física en las zonas primarias aduaneras (puertos/aeropuertos)."
    },
    "Tecnología y Electrónicos": {
        "ente": "CONATEL / SENCAMER",
        "permisos": [
            "Certificado de Homologación (CONATEL - si maneja frecuencias/RF).",
            "Registro de Constancia de Registro de Productos (SENCAMER)."
        ],
        "base_legal": "Ley Orgánica de Telecomunicaciones / Normas COVENIN vigentes.",
        "dias_promedio_tramite": 7,
        "nota_alerta": "Dispositivos con WiFi/Bluetooth de alta potencia requieren revisión de bandas restringidas."
    },
    "Químicos y Materias Primas": {
        "ente": "MINCONTRALORÍA / RESQUIM",
        "permisos": [
            "Registro Nacional de Operadores de Sustancias Químicas Controladas.",
            "Licencia de Importación (RESQUIM)."
        ],
        "base_legal": "Ley Orgánica de Drogas / Control de Sustancias Químicas.",
        "dias_promedio_tramite": 22,
        "nota_alerta": "Sujeto a regímenes de inspección estrictos. Trámite crítico con alta tasa de demoras."
    },
    "Repuestos y Maquinaria Industrial": {
        "ente": "MIN-INDUSTRIAS / SENCAMER",
        "permisos": [
            "Constancia de No Producción Nacional o Producción Insuficiente (CNP).",
            "Certificado de Calidad SENCAMER."
        ],
        "base_legal": "Decretos de exoneración industrial y fomento de manufactura.",
        "dias_promedio_tramite": 10,
        "nota_alerta": "Verificar si la subpartida arancelaria está amparada bajo los decretos de exoneración vigentes."
    }
}

def consultar_requisitos_vuce(categoria):
    """Retorna la información legal y operativa según la categoría de la mercancía."""
    return NORMATIVA_VUCE.get(categoria, None)