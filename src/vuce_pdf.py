import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generar_pdf_dictamen(regimen, consulta_usuario, texto_html, ruta_guardado):
    """
    Toma el dictamen HTML generado por la IA y lo convierte en un reporte PDF
    con diseño corporativo elegante listo para descargar.
    """
    # 1. Configurar el documento (Margen de 2 cm)
    doc = SimpleDocTemplate(
        ruta_guardado,
        pagesize=letter,
        rightMargin=54, leftMargin=54,
        topMargin=54, bottomMargin=54
    )
    
    # 2. Configurar la paleta de colores corporativa (Azul marino y gris ejecutivo)
    COLOR_PRIMARIO = colors.HexColor("#0f172a")  # Fondo oscuro de la app adaptado a texto institucional
    COLOR_ACCENTO = colors.HexColor("#0284c7")   # Azul brillante para resaltar
    COLOR_TEXTO = colors.HexColor("#334155")     # Gris oscuro legible para impresión
    
    # 3. Estilos de texto (ReportLab usa hojas de estilo basadas en HTML/CSS simplificado)
    styles = getSampleStyleSheet()
    
    style_titulo = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=COLOR_PRIMARIO,
        spaceAfter=6
    )
    
    style_subtitulo = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=15
    )
    
    # Estilo base para el contenido que viene de la IA
    style_cuerpo = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        textColor=COLOR_TEXTO,
        spaceAfter=10
    )
    
    # 4. Construir los elementos del PDF (La lista "Story")
    story = []
    
    # Encabezado principal del reporte
    story.append(Paragraph(f"<b>DICTAMEN DE VIABILIDAD ADUANERA (VUCE 2026)</b>", style_titulo))
    fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph(f"Reporte generado automáticamente el {fecha_actual} | Régimen: {regimen}", style_subtitulo))
    
    # Tabla resumen con la consulta del cliente
    data_resumen = [
        [Paragraph(f"<b>Operación Solicitada:</b>", style_cuerpo)],
        [Paragraph(f"<i>\"{consulta_usuario}\"</i>", ParagraphStyle('Italic', parent=style_cuerpo, textColor=colors.HexColor("#475569")))]
    ]
    tabla_resumen = Table(data_resumen, colWidths=[500])
    tabla_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('PADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,1), (-1,1), 12),
    ]))
    story.append(tabla_resumen)
    story.append(Spacer(1, 20))
    
    # 5. Procesamiento del Dictamen de la IA
    # Reemplazamos los encabezados HTML que genera la IA por estilos nativos de ReportLab para que no se desborden
    lineas = texto_html.split('\n')
    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue
            
        # Si la línea es un título primario h2 o h3 de la IA, le damos formato destacado en el PDF
        if "</h2>" in linea or "</h3>" in linea:
            # Limpiamos las etiquetas HTML para el título nativo
            texto_limpio = linea.replace("<h2>", "").replace("</h2>", "").replace("<h3>", "").replace("</h3>", "")
            # Quitar posibles estilos inline que meta la IA
            if "<h2 style=" in linea or "<h3 style=":
                texto_limpio = texto_limpio.split(">")[-1] if ">" in texto_limpio else texto_limpio
            
            story.append(Spacer(1, 10))
            story.append(Paragraph(f"<b>{texto_limpio}</b>", ParagraphStyle('HeadingIA', parent=style_cuerpo, fontSize=13, leading=16, textColor=COLOR_ACCENTO, spaceAfter=8)))
            continue
            
        # Para el resto del contenido (listas ul/li, párrafos), ReportLab procesa bien las etiquetas básicas inline <b>, <ul>, <li>
        story.append(Paragraph(linea, style_cuerpo))
    
    # 6. Escribir/Guardar el archivo físicamente
    doc.build(story)