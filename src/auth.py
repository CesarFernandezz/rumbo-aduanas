import sqlite3
import bcrypt
from src.database import conectar_db

def registrar_usuario(username, password, rol="User"):
    """
    Registra un nuevo usuario en la base de datos encriptando su contraseña.
    Devuelve True si el registro fue exitoso, o False si el usuario ya existe.
    """
    username = username.strip().lower()
    if not username or not password:
        return False, "El usuario y la contraseña no pueden estar vacíos."
        
    # Encriptar la contraseña usando bcrypt
    password_bytes = password.encode('utf-8')
    sal = bcrypt.gensalt()
    hash_contrasena = bcrypt.hashpw(password_bytes, sal).decode('utf-8')
    
    conn = conectar_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO usuarios (username, password_hash, rol) VALUES (?, ?, ?)",
            (username, hash_contrasena, rol)
        )
        conn.commit()
        return True, "Usuario registrado exitosamente."
    except sqlite3.IntegrityError:
        return False, "El nombre de usuario ya se encuentra registrado."
    finally:
        conn.close()

def verificar_usuario(username, password):
    """
    Verifica las credenciales de acceso contra los registros de la base de datos.
    Devuelve (True, id_usuario, rol) si es correcto, o (False, None, None) si falla.
    """
    username = username.strip().lower()
    
    conn = conectar_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id_usuario, password_hash, rol FROM usuarios WHERE username = ?", (username,))
    resultado = cursor.fetchone()
    conn.close()
    
    if resultado:
        id_usuario, hash_almacenado, rol = resultado
        # Verificar si la contraseña ingresada coincide con el hash guardado
        if bcrypt.checkpw(password.encode('utf-8'), hash_almacenado.encode('utf-8')):
            return True, id_usuario, rol
            
    return False, None, None