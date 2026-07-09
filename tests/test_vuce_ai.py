# tests/test_vuce_ai.py — pruebas del Asesor VUCE (fallback estatico vs. respuesta de IA).
# No consumen API ni red: la IA se simula con monkeypatch.
from src import vuce_ai


def test_limpiar_html_quita_cercas_markdown():
    # El modelo a veces envuelve el HTML en ```html ... ```; debe quedar solo el HTML.
    assert vuce_ai._limpiar_html("```html\n<p>hola</p>\n```") == "<p>hola</p>"
    assert vuce_ai._limpiar_html("```\n<div>x</div>\n```") == "<div>x</div>"
    # Si no hay cercas, se devuelve igual (solo recortando espacios).
    assert vuce_ai._limpiar_html("  <p>y</p>  ") == "<p>y</p>"


def test_fallback_a_plantilla_sin_api_key(monkeypatch):
    # Sin GEMINI_API_KEY, _generar_con_ia devuelve None y se usa la plantilla estatica.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    html = vuce_ai.consultar_asesor_vuce("IMPORTACIÓN", "café en grano")
    assert "Guía de Procedimiento Aduanero" in html   # es la plantilla de respaldo
    assert "IMPORTACIÓN" in html                        # refleja el régimen pedido


def test_usa_respuesta_de_ia_cuando_esta_disponible(monkeypatch):
    # Si la IA responde, consultar_asesor_vuce debe devolver ESA respuesta (no la plantilla).
    monkeypatch.setattr(vuce_ai, "_generar_con_ia", lambda prompt: "<div>DICTAMEN_IA_ESPECIFICO</div>")
    html = vuce_ai.consultar_asesor_vuce("EXPORTACIÓN", "lámparas LED")
    assert html == "<div>DICTAMEN_IA_ESPECIFICO</div>"
    assert "Guía de Procedimiento Aduanero" not in html  # NO cayó a la plantilla


def test_generar_con_ia_sin_key_devuelve_none(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert vuce_ai._generar_con_ia("cualquier prompt") is None


def test_construir_prompt_incluye_consulta_y_regimen():
    p = vuce_ai._construir_prompt("IMPORTACIÓN", "neumáticos", "")
    assert "neumáticos" in p and "IMPORTACIÓN" in p
    assert "HTML" in p  # exige salida en HTML
