import pandas as pd
import numpy as np
import os

# Definir la ruta del CSV de salida de forma dinámica y segura
RUTA_SALIDA = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'historico_envios.csv')

def generar_dataset_logistico(n_muestras=5000):
    # Asegurar que la carpeta 'data/' exista en la raíz
    os.makedirs(os.path.dirname(RUTA_SALIDA), exist_ok=True)
    np.random.seed(42)  # Datos reproducibles

    origenes = ['Shanghái', 'Miami', 'Róterdam', 'Veracruz', 'Panamá']
    navieras = ['Maersk', 'MSC', 'CMA CGM']
    aerolineas = ['DHL Cargo', 'Laser Cargo', 'TAP Cargo']

    # Las 10 categorías comerciales profesionales
    tipos_carga = [
        'Tecnología y Electrónica', 'Materia Prima Industrial', 'Textil y Calzado',
        'Maquinaria y Repuestos', 'Alimentos y Perecederos', 'Fármacos y Salud',
        'Automotriz', 'Químicos y Peligrosos', 'Hogar y Construcción', 'Misceláneos y Courier'
    ]

    data = []

    for _ in range(n_muestras):
        via = np.random.choice(['Marítimo', 'Aéreo'])
        mes = np.random.randint(1, 13)
        origen = np.random.choice(origenes)
        tipo_carga = np.random.choice(tipos_carga)

        # 1. Lógica según la Vía elegida
        if via == 'Marítimo':
            aduana_destino = np.random.choice(['Puerto Cabello', 'La Guaira'])
            operador = np.random.choice(navieras)
            
            distancias = {'Shanghái': 15100, 'Miami': 1980, 'Róterdam': 7400, 'Veracruz': 2600, 'Panamá': 1050}
            distancia_km = distancias[origen]
            
            # Navegación marítima
            dias_transito = (distancia_km / (35 * 24)) + np.random.normal(2, 1) 
            dias_fondeo = np.random.exponential(scale=3.0) 
            dias_aduana = np.random.normal(loc=6.0, scale=2.0) 

        else:  # Vía Aérea ✈️
            aduana_destino = 'Maiquetía'
            operador = np.random.choice(aerolineas)
            
            distancias = {'Shanghái': 15900, 'Miami': 2100, 'Róterdam': 8050, 'Veracruz': 3150, 'Panamá': 1280}
            distancia_km = distancias[origen]
            
            # Ciclo aéreo consolidado (mínimo una semana)
            dias_consolidacion = np.random.uniform(2.0, 4.0)
            if origen in ['Miami', 'Panamá']:
                dias_vuelo = np.random.uniform(0.5, 1.2)
            else:
                dias_vuelo = np.random.uniform(2.0, 3.5)
                
            dias_transito = dias_consolidacion + dias_vuelo
            dias_fondeo = 0.0
            dias_aduana = np.random.normal(loc=4.0, scale=1.0)

        # 2. Factor de Retraso según la Categoría del Producto (SENIAT / Sanidad)
        if tipo_carga in ['Alimentos y Perecederos', 'Químicos y Peligrosos']:
            dias_aduana *= np.random.uniform(1.2, 1.5)  # Trámites más lentos por permisos
        elif tipo_carga == 'Fármacos y Salud':
            dias_aduana *= 0.8  # Despacho prioritario

        # 3. Factor de Estacionalidad Decembrina en Venezuela
        if mes in [10, 11, 12]:
            dias_aduana *= np.random.uniform(1.3, 1.7)
            if via == 'Marítimo':
                dias_fondeo *= 1.4

        # 4. Cálculo final unificado
        dias_reales_totales = dias_transito + dias_fondeo + dias_aduana
        dias_reales_totales = round(max(0.5, dias_reales_totales), 1)

        data.append([
            origen, aduana_destino, via, operador, tipo_carga, 
            mes, distancia_km, round(dias_transito, 1), round(dias_fondeo, 1), 
            round(dias_aduana, 1), dias_reales_totales
        ])

    # 5. Estructurar y guardar a disco de manera limpia
    columnas = [
        'origen', 'aduana_destino', 'via', 'operador', 'tipo_carga', 
        'mes', 'distancia_km', 'dias_transito_int', 'dias_fondeo', 
        'dias_nacionalizacion', 'dias_reales'
    ]
    df = pd.DataFrame(data, columns=columnas)
    
    try:
        df.to_csv(RUTA_SALIDA, index=False)
        print(f"-> [ÉXITO] Nuevo dataset generado correctamente en: {RUTA_SALIDA}")
        print(f"   Estructurado con las 10 categorías de importación listas para el Machine Learning.")
    except PermissionError:
        print(f"❌ [ERROR DE PERMISO] El archivo {RUTA_SALIDA} está abierto en Excel. Ciérralo e intenta de nuevo.")

if __name__ == "__main__":
    generar_dataset_logistico()