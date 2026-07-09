import os
import sys
import pickle
import numpy as np
# Carga las variables de .env (p. ej. GEMINI_API_KEY) al importar este modulo.
# python-dotenv es dependencia base; si por algun motivo faltara, no rompemos el import.
try:
    from dotenv import load_dotenv
    load_dotenv()  # busca un .env en el cwd (la raiz del proyecto) y hacia arriba; no pisa variables ya definidas
except Exception:
    pass

# Nota: sentence_transformers (que arrastra PyTorch) NO se importa aqui a proposito.
# Es una dependencia OPCIONAL y pesada; se importa de forma perezosa dentro de
# buscar_contexto_legal() solo si hay un indice de gacetas que consultar. Asi el
# Asesor VUCE arranca en cualquier PC aunque torch no este instalado o su DLL falle.

RUTA_INDICE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'indice_legal.pkl')

# Modelo de Gemini a usar (rapido y economico). Se puede sobreescribir con la variable GEMINI_MODEL.
MODELO_IA = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def buscar_contexto_legal(consulta, top_k=3):
    """Busca en el fondo el contexto de las gacetas sin alterar la salida del usuario."""
    if not os.path.exists(RUTA_INDICE):
        return ""
    try:
        # Import perezoso: trae PyTorch. Si no esta instalado o su DLL falla
        # (p.ej. [WinError 1114] al cargar c10.dll), caemos al except y devolvemos "".
        from sentence_transformers import SentenceTransformer
        with open(RUTA_INDICE, 'rb') as f:
            data = pickle.load(f)
        indice_faiss = data["indice"]
        fragmentos = data["fragmentos"]

        model = SentenceTransformer('all-MiniLM-L6-v2')
        vector_consulta = model.encode([consulta]).astype('float32')
        _, indices = indice_faiss.search(vector_consulta, top_k)

        contexto = ""
        for idx in indices[0]:
            if idx != -1 and idx < len(fragmentos):
                contexto += f"{fragmentos[idx]['texto']}\n"
        return contexto
    except Exception:
        return ""


def _limpiar_html(texto):
    """Quita las cercas de codigo Markdown (```html ... ```) que a veces envuelve el modelo."""
    t = (texto or "").strip()
    if t.startswith("```"):
        lineas = t.split("\n")
        if lineas and lineas[0].startswith("```"):   # primera linea: ```html o ```
            lineas = lineas[1:]
        if lineas and lineas[-1].strip().startswith("```"):  # ultima linea: ```
            lineas = lineas[:-1]
        t = "\n".join(lineas).strip()
    return t


def _generar_con_ia(prompt):
    """
    Pide la guia a Gemini y devuelve HTML limpio, o None si no se puede generar
    (sin GEMINI_API_KEY, sin el SDK google-genai instalado, o error de la API).
    Nunca lanza: ante cualquier fallo devuelve None para caer a la plantilla estatica.
    Registra en stderr el motivo (sin exponer la clave) para poder diagnosticar.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[vuce] Sin GEMINI_API_KEY en el entorno/.env: uso la plantilla estatica.", file=sys.stderr)
        return None
    try:
        from google import genai  # SDK google-genai (liviano, no trae torch)
    except Exception as e:
        print(f"[vuce] SDK google-genai no disponible ({e}): uso la plantilla estatica. "
              f"Instala con: pip install google-genai", file=sys.stderr)
        return None
    try:
        cliente = genai.Client(api_key=api_key)
        respuesta = cliente.models.generate_content(model=MODELO_IA, contents=prompt)
        html = _limpiar_html(getattr(respuesta, "text", "") or "")
        if not html:
            print("[vuce] La IA devolvio una respuesta vacia: uso la plantilla estatica.", file=sys.stderr)
            return None
        return html
    except Exception as e:
        # Errores tipicos: clave invalida, sin cuota, sin internet, modelo inexistente.
        print(f"[vuce] Error llamando a Gemini ({type(e).__name__}: {e}): uso la plantilla estatica.", file=sys.stderr)
        return None


def _construir_prompt(regimen, consulta_usuario, contexto_legal):
    """Arma el prompt que obliga a la IA a devolver una guia ESPECIFICA en HTML limpio."""
    prompt = (
        "Eres un asesor automatizado experto en Comercio Exterior para la VUCE y el SENIAT en Venezuela.\n"
        "Genera una guia de procedimiento aduanero ESPECIFICA para la mercancia y el regimen indicados. "
        "No des una respuesta generica: adapta los pasos, permisos y alertas al producto concreto de la consulta.\n\n"
        f"Regimen: {regimen}\n"
        f"Consulta del usuario: {consulta_usuario}\n"
    )
    if contexto_legal:
        prompt += ("\nInformacion legal de respaldo (gacetas oficiales); usala si es pertinente, "
                   "pero NO la cites textualmente ni muestres referencias del indexador:\n"
                   f"{contexto_legal}\n")
    prompt += (
        "\nFORMATO DE SALIDA (obligatorio):\n"
        "- Responde UNICAMENTE con HTML (sin Markdown, sin ```html, sin texto fuera del HTML).\n"
        "- Todo en espanol. Usa <b> para resaltar terminos clave.\n"
        "- Envuelve todo en: <div style='font-family: sans-serif; color:#cbd5e1; line-height:150%;'>...</div>\n"
        "- Estructura, adaptada al producto:\n"
        f"  <h3 style='color:#38bdf8; margin-top:0'>Guia de Procedimiento Aduanero ({regimen})</h3>\n"
        "  <p><b>Resumen de viabilidad:</b> (parrafo corto y concreto sobre esta mercancia)</p>\n"
        "  <h4 style='color:#38bdf8'>Pasos cronologicos a seguir</h4> <ol> (pasos especificos) </ol>\n"
        "  <h4 style='color:#38bdf8'>Requisitos documentales y permisos</h4> <ul> (documentos y entes: SENCAMER, sanidad, ministerios, etc. si aplican) </ul>\n"
        "  <h4 style='color:#10b981'>Alertas y consejos fiscales</h4> <ul> (impuestos, exoneraciones, riesgos) </ul>\n"
    )
    return prompt


def consultar_asesor_vuce(regimen, consulta_usuario):
    """
    Genera el dictamen como guia de pasos. Si hay una IA configurada (GEMINI_API_KEY),
    devuelve una respuesta REAL y especifica generada por Gemini; si no, cae a una
    plantilla estatica para que la app siga funcionando en cualquier PC.
    """
    # 1. Contexto legal de las gacetas en segundo plano (vacio si el RAG no esta disponible).
    contexto_legal = buscar_contexto_legal(consulta_usuario)

    # 2. Intentar generar con IA. Si algo falla, _generar_con_ia devuelve None.
    prompt = _construir_prompt(regimen, consulta_usuario, contexto_legal)
    html_ia = _generar_con_ia(prompt)
    if html_ia:
        return html_ia

    # 3. Fallback: plantilla estatica (misma salida de siempre; no rompe la app sin clave).
    return _plantilla_estatica(regimen)


def _plantilla_estatica(regimen):
    """Guia generica de respaldo cuando no hay una IA disponible. Estructura h3/h4/ol/ul compatible con el PDF."""
    return f"""
    <div style='font-family: sans-serif; color: #cbd5e1; line-height: 150%;'>
        <h3 style='color: #38bdf8; margin-top: 0; border-bottom: 1px solid #334155; padding-bottom: 8px;'> Guía de Procedimiento Aduanero ({regimen})</h3>

        <p><b>Análisis de Operación:</b> La consulta para el rubro solicitado es viable bajo el marco regulatorio vigente. A continuación, se detalla la hoja de ruta crítica para el despacho en las aduanas venezolanas.</p>

        <h4 style='color: #38bdf8; margin-bottom: 5px;'> Pasos Cronológicos a Seguir:</h4>
        <ol style='margin-top: 5px; padding-left: 20px;'>
            <li><b>Verificación Arancelaria:</b> Clasificar el producto en el Arancel de Aduanas de Venezuela para determinar los impuestos de ley (Ad-Valorem).</li>
            <li><b>Tramitación del Registro Obligatorio:</b> Gestionar los regímenes legales correspondientes ante los ministerios competentes antes del embarque.</li>
            <li><b>Transmisión de Manifiesto:</b> El operador logístico debe registrar el manifiesto de carga en el sistema SIDUNEA una vez arribe el transporte.</li>
            <li><b>Reconocimiento de la Carga:</b> Presentar la documentación ante las autoridades aduaneras para la inspección física o documental (Canal de selectividad).</li>
        </ol>

        <h4 style='color: #38bdf8; margin-bottom: 5px;'> Requisitos Documentales y Permisos:</h4>
        <ul style='margin-top: 5px; padding-left: 20px;'>
            <li><b>Documentación Comercial Base:</b> Factura Comercial Definitiva, Lista de Empaque (Packing List) y Documento de Transporte (BL o Guía Aérea).</li>
            <li><b>Permisología Especial:</b> Certificado de Origen, Registros Sanitarios (si aplica a alimentos/salud) o Constancia de Registro Nacional de Exportadores.</li>
            <li><b>Declaración de Aduana:</b> Elaboración y validación de la DUA por medio de un agente aduanal autorizado.</li>
        </ul>

        <h4 style='color: #10b981; margin-bottom: 5px;'> Alertas y Sugerencias Fiscales:</h4>
        <ul style='margin-top: 5px; padding-left: 20px; list-style-type: square;'>
            <li>Revise si el código arancelario de su mercancía califica en los apéndices de los decretos de exoneración de impuestos vigentes para mitigar costos CIF.</li>
            <li>Asegúrese de que las fechas de emisión de los permisos emitidos por entes del Estado coincidan con los plazos de zarpe para evitar multas por vencimiento en muelle.</li>
        </ul>
    </div>
    """
