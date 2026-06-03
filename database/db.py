import sqlite3
import os

# Ruta de la base de datos
DB_PATH = os.path.join(os.path.dirname(__file__), "apartados.db")

def get_connection():
    """Retorna una conexión a la base de datos."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_db():
    """Crea las tablas si no existen."""
    conn = get_connection()
    cursor = conn.cursor()

    # Tabla de alumnos y apartados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS apartados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folio TEXT UNIQUE NOT NULL,
            nombre_alumno TEXT NOT NULL,
            grado TEXT NOT NULL,
            nombre_tutor TEXT NOT NULL,
            telefono_principal TEXT NOT NULL,
            telefono_secundario TEXT,
            estado TEXT DEFAULT 'pendiente',
            fecha_registro TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # Tabla de pagos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folio TEXT NOT NULL,
            monto REAL NOT NULL,
            tipo_pago TEXT NOT NULL,
            fase TEXT DEFAULT 'anticipo',
            fecha_pago TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (folio) REFERENCES apartados(folio)
        )
    """)

    # Tabla de log de inferencias (para el Agente 3 - Supervisor)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inferencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folio TEXT,
            regla_aplicada TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            resultado TEXT NOT NULL,
            fecha TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Base de datos inicializada correctamente.")

def generar_folio():
    """Genera un folio único para cada apartado."""
    import random
    import string
    conn = get_connection()
    cursor = conn.cursor()
    while True:
        folio = "ZN-" + "".join(random.choices(string.digits, k=6))
        cursor.execute("SELECT id FROM apartados WHERE folio = ?", (folio,))
        if not cursor.fetchone():
            conn.close()
            return folio

def registrar_apartado(nombre_alumno, grado, nombre_tutor, telefono_principal, telefono_secundario=None):
    """Registra un nuevo apartado y retorna el folio generado."""
    folio = generar_folio()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO apartados (folio, nombre_alumno, grado, nombre_tutor, telefono_principal, telefono_secundario)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (folio, nombre_alumno, grado, nombre_tutor, telefono_principal, telefono_secundario))
    conn.commit()
    conn.close()
    return folio

def registrar_pago(folio, monto, tipo_pago):
    """Registra un pago asociado a un folio."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pagos (folio, monto, tipo_pago)
        VALUES (?, ?, ?)
    """, (folio, monto, tipo_pago))
    conn.commit()
    conn.close()

def buscar_por_folio(folio):
    """Busca un apartado por su folio."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM apartados WHERE folio = ?", (folio,))
    resultado = cursor.fetchone()
    conn.close()
    return dict(resultado) if resultado else None

def buscar_por_telefono(telefono):
    """Busca apartados por número de teléfono."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM apartados 
        WHERE telefono_principal = ? OR telefono_secundario = ?
    """, (telefono, telefono))
    resultados = cursor.fetchall()
    conn.close()
    return [dict(r) for r in resultados]

def verificar_duplicado(nombre_alumno, grado):
    """Verifica duplicados ignorando espacios extra, acentos y mayúsculas."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Normalizar el nombre eliminando espacios extra
    nombre_normalizado = " ".join(nombre_alumno.lower().strip().split())
    
    cursor.execute("""
        SELECT * FROM apartados 
        WHERE LOWER(TRIM(nombre_alumno)) = ? AND LOWER(TRIM(grado)) = LOWER(TRIM(?))
    """, (nombre_normalizado, grado))
    resultado = cursor.fetchone()
    conn.close()
    return dict(resultado) if resultado else None

def registrar_inferencia(folio, regla, descripcion, resultado):
    """Guarda en el log cada inferencia realizada por los agentes."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO inferencias (folio, regla_aplicada, descripcion, resultado)
        VALUES (?, ?, ?, ?)
    """, (folio, regla, descripcion, resultado))
    conn.commit()
    conn.close()

def obtener_pagos(folio):
    """Obtiene todos los pagos de un folio."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pagos WHERE folio = ?", (folio,))
    resultados = cursor.fetchall()
    conn.close()
    return [dict(r) for r in resultados]

if __name__ == "__main__":
    inicializar_db()