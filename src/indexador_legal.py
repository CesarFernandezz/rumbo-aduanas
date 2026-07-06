import os
import faiss
import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import pickle

CARPETA_GACETAS = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'gacetas')
RUTA_INDICE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'indice_legal.pkl')

def indexar_gacetas_vuce():
    """Lee las gacetas en PDF, las fragmenta y crea un índice de búsqueda vectorial."""
    if not os.path.exists(CARPETA_GACETAS):
        os.makedirs(CARPETA_GACETAS, exist_ok=True)
        print(f"📁 Se creó la carpeta en {CARPETA_GACETAS}. Coloca tus PDFs allí y vuelve a ejecutar.")
        return

    archivos_pdf = [f for f in os.listdir(CARPETA_GACETAS) if f.endswith('.pdf')]
    if not archivos_pdf:
        print("📭 No se encontraron archivos PDF en la carpeta de gacetas.")
        return

    print("🧠 Cargando modelo de lenguaje para incrustaciones (Embeddings)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    fragmentos_texto = []
    
    print(f"📄 Procesando {len(archivos_pdf)} gacetas oficiales...")
    for archivo in archivos_pdf:
        ruta_pdf = os.path.join(CARPETA_GACETAS, archivo)
        reader = PdfReader(ruta_pdf)
        
        for num_pagina, pagina in enumerate(reader.pages):
            texto = pagina.extract_text()
            if not texto:
                continue
                
            # Dividir el texto de la página en párrafos o artículos estimando ~500 caracteres
            parrafos = texto.split("\n\n")
            for p in parrafos:
                p_limpio = p.strip().replace("\n", " ")
                if len(p_limpio) > 50:  # Evitar líneas vacías o basura
                    # Guardamos el texto junto con la fuente para la cita legal
                    fragmentos_texto.append({
                        "texto": p_limpio,
                        "fuente": f"{archivo} (Pág. {num_pagina + 1})"
                    })

    if not fragmentos_texto:
        print("⚠️ No se pudo extraer texto válido de los PDF.")
        return

    # Convertir los fragmentos de texto a vectores matemáticos
    print(f"⚡ Vectorizando {len(fragmentos_texto)} fragmentos legales...")
    textos_puros = [f["texto"] for f in fragmentos_texto]
    embeddings = model.encode(textos_puros, show_progress_bar=True)
    
    # Crear el índice de búsqueda FAISS
    dimension = embeddings.shape[1]
    indice_faiss = faiss.IndexFlatL2(dimension)
    indice_faiss.add(np.array(embeddings).astype('float32'))
    
    # Guardar el índice y los textos estructurados en el disco
    data_indexada = {
        "indice": indice_faiss,
        "fragmentos": fragmentos_texto
    }
    
    with open(RUTA_INDICE, 'wb') as f:
        pickle.dump(data_indexada, f)
        
    print(f"-> [ÉXITO] Base de conocimiento legal unificada y guardada en {RUTA_INDICE}")

if __name__ == "__main__":
    indexar_gacetas_vuce()