import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import GradientBoostingRegressor
import os

RUTA_CSV = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'historico_envios.csv')

def entrenar_modelo_eta():
    """
    Entrena un modelo de regresión avanzada para predecir el ETA y desglosar 
    los tiempos de tránsito, fondeo y aduana según la realidad venezolana.
    """
    if not os.path.exists(RUTA_CSV):
        raise FileNotFoundError(f"No se encontró el archivo histórico en {RUTA_CSV}. Ejecuta primero generar_data_logistica.py")

    # 1. Cargar datos
    df = pd.read_csv(RUTA_CSV)

    # 2. Inicializar y aplicar LabelEncoders para las variables categóricas
    encoders = {}
    columnas_categoricas = ['origen', 'aduana_destino', 'via', 'operador', 'tipo_carga']
    
    for col in columnas_categoricas:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col])
        encoders[col] = le

    # 3. Definir características (X) y variables objetivos (y)
    # Entrenaremos modelos individuales para cumplir con el desglose del RF-04
    X = df[['origen', 'aduana_destino', 'via', 'operador', 'tipo_carga', 'mes', 'distancia_km']]
    
    y_total = df['dias_reales']
    y_transito = df['dias_transito_int']
    y_fondeo = df['dias_fondeo']
    y_aduana = df['dias_nacionalizacion']

    # 4. Dividir datos en entrenamiento y prueba
    X_train, X_test, y_train_t, y_test_t = train_test_split(X, y_total, test_size=0.2, random_state=42)
    _, _, y_train_tr, _ = train_test_split(X, y_transito, test_size=0.2, random_state=42)
    _, _, y_train_fo, _ = train_test_split(X, y_fondeo, test_size=0.2, random_state=42)
    _, _, y_train_ad, _ = train_test_split(X, y_aduana, test_size=0.2, random_state=42)

    # 5. Entrenar los modelos (Usamos Gradient Boosting por su alta precisión con variables estacionales)
    print(" -> Entrenando modelos de predicción inteligente...")
    
    modelo_total = GradientBoostingRegressor(n_estimators=100, random_state=42).fit(X_train, y_train_t)
    modelo_transito = GradientBoostingRegressor(n_estimators=50, random_state=42).fit(X_train, y_train_tr)
    modelo_fondeo = GradientBoostingRegressor(n_estimators=50, random_state=42).fit(X_train, y_train_fo)
    modelo_aduana = GradientBoostingRegressor(n_estimators=50, random_state=42).fit(X_train, y_train_ad)

    # Agrupamos los modelos en un diccionario estructurado
    modelos_expertos = {
        'total': modelo_total,
        'transito': modelo_transito,
        'fondeo': modelo_fondeo,
        'aduana': modelo_aduana
    }

    # Evaluar precisión básica en el set de prueba
    score = modelo_total.score(X_test, y_test_t)
    print(f" [+] Modelo entrenado con éxito. R² Score de precisión: {score:.2%}")

    return modelos_expertos, encoders

if __name__ == "__main__":
    entrenar_modelo_eta()