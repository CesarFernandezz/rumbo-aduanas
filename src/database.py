import sqlite3
import os

# Buscamos la ruta absoluta de la carpeta 'data' sin importar dónde se ejecute el script
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'logistica.db')

def conectar_db():
    """Establece conexión con SQLite y activa las llaves foráneas obligatorias."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def inicializar_tablas():
    """Crea la estructura física de la base de datos si no existe."""
    # Asegurar que la carpeta 'data' exista en el disco duro
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = conectar_db()
    cursor = conn.cursor()
    
    # -------------------------------------------------------------
    # NUEVA TABLA 1: GESTIÓN DE USUARIOS (RF-01) (Modificada con campo empresa)
    # -------------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            rol TEXT CHECK(rol IN ('User', 'Admin')) DEFAULT 'User',
            empresa TEXT, -- Nombre de la organización (Opcional)
            fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # -------------------------------------------------------------
    # NUEVA TABLA 2: ARANCEL DE ADUANAS DE VENEZUELA (RF-05, RF-06, RF-13)
    # -------------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS arancel_venezuela (
            codigo_arancelario TEXT PRIMARY KEY, -- Formato: 1234.56.78.90
            descripcion TEXT NOT NULL,
            ad_valorem REAL NOT NULL,            -- Impuesto de importación %
            tasa_servicio REAL DEFAULT 1.0,     -- Tasa aduanera %
            iva REAL DEFAULT 16.0,              -- Alícuota de IVA %
            regimenes_legales TEXT              -- Permisologías (ej. "Regimen 4: INSAI, SACS")
        )
    ''')
    
    # 3. RUTAS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rutas (
            id_ruta INTEGER PRIMARY KEY AUTOINCREMENT,
            origen TEXT NOT NULL,
            destino TEXT NOT NULL,
            via TEXT CHECK(via IN ('Marítimo', 'Aéreo', 'Terrestre')) NOT NULL,
            distancia_mn REAL,
            tiempo_estimado_teorico REAL
        )
    ''')
    
    # 4. EMBARQUES (Modificado para asociarle qué usuario maneja la carga - RF-02)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS embarques (
            id_embarque TEXT PRIMARY KEY,
            id_ruta INTEGER NOT NULL,
            id_usuario INTEGER DEFAULT 1, -- Por defecto asignado al primer usuario creado
            proveedor TEXT NOT NULL,
            estado TEXT CHECK(estado IN ('En Tránsito', 'Aduana', 'Entregado', 'Demorado')) DEFAULT 'En Tránsito',
            fecha_salida TEXT NOT NULL,
            fecha_llegada_real TEXT,
            eta_predicho REAL,
            FOREIGN KEY (id_ruta) REFERENCES rutas(id_ruta),
            FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
        )
    ''')
    
    # 5. ITEMS DEL EMBARQUE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items_embarque (
            id_item INTEGER PRIMARY KEY AUTOINCREMENT,
            id_embarque TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            codigo_arancelario TEXT NOT NULL, 
            cantidad INTEGER NOT NULL,
            precio_unitario_fob REAL NOT NULL,
            FOREIGN KEY (id_embarque) REFERENCES embarques(id_embarque) ON DELETE CASCADE,
            FOREIGN KEY (codigo_arancelario) REFERENCES arancel_venezuela(codigo_arancelario)
        )
    ''')
    
    # 6. LANDED COST
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS landed_cost (
            id_costo INTEGER PRIMARY KEY AUTOINCREMENT,
            id_embarque TEXT UNIQUE NOT NULL,
            valor_fob_total REAL NOT NULL,          
            flete_internacional REAL DEFAULT 0.0,
            seguro_internacional REAL DEFAULT 0.0,
            aranceles_aduanales REAL DEFAULT 0.0,     
            gastos_portuarios REAL DEFAULT 0.0,
            transporte_local REAL DEFAULT 0.0,
            costo_total_landed REAL GENERATED ALWAYS AS (
                valor_fob_total + flete_internacional + seguro_internacional + 
                aranceles_aduanales + gastos_portuarios + transporte_local
            ) STORED,
            FOREIGN KEY (id_embarque) REFERENCES embarques(id_embarque) ON DELETE CASCADE
        )
    ''')

    # 7. HISTORIAL DE TRÁNSITO
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS eventos_transito (
            id_evento INTEGER PRIMARY KEY AUTOINCREMENT,
            id_embarque TEXT NOT NULL,
            hito TEXT NOT NULL, 
            fecha_hito TEXT NOT NULL,
            comentario TEXT,
            FOREIGN KEY (id_embarque) REFERENCES embarques(id_embarque) ON DELETE CASCADE
        )
    ''')
    
    # 8. HISTORIAL DEL CHATBOT VUCE (Modificado para guardar por Usuario - RF-02)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial_chat (
            id_mensaje INTEGER PRIMARY KEY AUTOINCREMENT,
            id_usuario TEXT NOT NULL, -- Cambiado a TEXT para mapear directo con self.usuario_actual alternativamente
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            rol TEXT CHECK(rol IN ('user', 'assistant')) NOT NULL,
            contenido TEXT NOT NULL
        )
    ''')

    # 9. NUEVA TABLA AUDITORÍA RAPIDA: Para estimaciones de calculadoras sueltas sin crear un embarque formal
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial_operaciones_rapidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            modulo TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("-> ¡Base de datos local y tablas actualizadas con éxito!")
    
    # Inyectar datos iniciales automáticamente
    precargar_datos_semilla()


def precargar_datos_semilla():
    """Inyecta registros básicos para pruebas (Un administrador y códigos arancelarios comunes)."""
    conn = conectar_db()
    cursor = conn.cursor()
    
    # 1. Crear usuarios de prueba por defecto si no hay ninguno. Las contraseñas se guardan HASHEADAS con bcrypt
    #    (nunca en texto plano), igual que las de los usuarios registrados desde la app.
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        import bcrypt  # cifrado de contraseñas
        hash_admin = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')   # hash del admin de prueba
        hash_cons = bcrypt.hashpw('pyme123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')     # hash del consultor de prueba
        cursor.execute("INSERT INTO usuarios (username, password_hash, rol, empresa) VALUES ('admin', ?, 'Admin', 'Aduana Central')", (hash_admin,))
        cursor.execute("INSERT INTO usuarios (username, password_hash, rol, empresa) VALUES ('consultor', ?, 'User', 'Logistica Pyme C.A.')", (hash_cons,))
        print("   [+] Usuarios semilla agregados (admin/consultor) con contraseñas hasheadas")

    # 2. Cargar subpartidas comunes del Arancel de Aduanas de Venezuela para pruebas
    items_arancel = [
        ('0901.11.10.00', 'Café en grano verde (Arábica), sin descafeinar, para siembra', 15.0, 1.0, 16.0, 'Régimen 4: Permiso del Ministerio de Agricultura (INSAI)'),
        ('1801.00.19.00', 'Cacao en grano, entero o partido, crudo (Calidad Superior Fino de Aroma)', 20.0, 1.0, 16.0, 'Régimen 4 y 7: Certificado Fitosanitario INSAI y Licencia de Exportación Min-Comercio'),
        ('3901.10.00.00', 'Polietileno de densidad inferior a 0.94 (Materia prima plástica en pellets)', 5.0, 1.0, 16.0, 'Régimen 12: Registro de Operadores de Sustancias Químicas Controladas (RESQUIMC)'),
        ('6403.91.90.00', 'Calzado de cuero con puntera de metal (Zapatos de seguridad industrial)', 20.0, 1.0, 16.0, 'Régimen 3: Constancia de Registro de Productos Nacionales (SENCAMER)'),
        ('8471.30.12.00', 'Máquinas automáticas para tratamiento o procesamiento de datos, portátiles (Laptops)', 0.0, 1.0, 16.0, 'Sin restricciones de régimen legal especial')
    ]
    
    try:
        cursor.executemany('''
            INSERT OR IGNORE INTO arancel_venezuela (codigo_arancelario, descripcion, ad_valorem, tasa_servicio, iva, regimenes_legales)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', items_arancel)
        conn.commit()
        print("   [+] Subpartidas arancelarias venezolanas precargadas.")
    except Exception as e:
        print(f"Error cargando semillas: {e}")
    finally:
        conn.close()


def guardar_en_historial(usuario, modulo, descripcion):
    """Inserta una nueva fila de auditoría vinculada al usuario activo en las calculadoras."""
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO historial_operaciones_rapidas (username, modulo, descripcion)
            VALUES (?, ?, ?)
        ''', (usuario, modulo, descripcion))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ [DB ERROR] No se pudo escribir en el historial rápido: {e}")
        return False

if __name__ == "__main__":
    inicializar_tablas()