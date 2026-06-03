import os
import time
import sqlite3
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
from database.db import (
    buscar_por_folio,
    obtener_pagos,
    registrar_inferencia
)

load_dotenv(Path(__file__).parent.parent / ".env")

cliente = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

MODELOS = [
    "google/gemma-4-31b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "openai/gpt-oss-120b:free",
]

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "apartados.db")

def llamar_modelo(prompt):
    """Intenta con varios modelos en orden hasta que uno funcione."""
    for modelo in MODELOS:
        try:
            print(f"Intentando con modelo: {modelo}")
            respuesta = cliente.chat.completions.create(
                model=modelo,
                messages=[{"role": "user", "content": prompt}]
            )
            texto = respuesta.choices[0].message.content.strip()
            print(f"✅ Modelo {modelo} respondió correctamente")
            return texto
        except Exception as e:
            print(f"❌ Modelo {modelo} falló: {e}")
            time.sleep(1)
            continue
    return None

def obtener_inferencias(folio=None):
    """Obtiene el historial de inferencias de la base de datos."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if folio:
        cursor.execute("SELECT * FROM inferencias WHERE folio = ? ORDER BY fecha DESC", (folio,))
    else:
        cursor.execute("SELECT * FROM inferencias ORDER BY fecha DESC LIMIT 20")
    resultados = cursor.fetchall()
    conn.close()
    return [dict(r) for r in resultados]

def generar_resumen_venta(folio):
    """Genera un resumen completo de la venta usando OpenRouter."""
    apartado = buscar_por_folio(folio)
    if not apartado:
        return {
            "exito": False,
            "mensaje": f"No se encontró ningún apartado con el folio {folio}"
        }

    pagos = obtener_pagos(folio)
    inferencias = obtener_inferencias(folio)
    total_pagado = sum(p["monto"] for p in pagos)

    inferencias_texto = "\n".join([
        f"- Regla: {inf['regla_aplicada']} | {inf['descripcion']} → {inf['resultado']}"
        for inf in inferencias
    ])

    prompt = f"""
Eres el Agente Supervisor de un sistema experto de apartado de útiles escolares.
Tu trabajo es generar un resumen claro y explicar las decisiones tomadas.

DATOS DEL APARTADO:
- Folio: {apartado['folio']}
- Alumno: {apartado['nombre_alumno']}
- Grado: {apartado['grado']}
- Tutor: {apartado['nombre_tutor']}
- Teléfono: {apartado['telefono_principal']}
- Estado: {apartado['estado']}
- Fecha de registro: {apartado['fecha_registro']}

PAGOS REGISTRADOS:
{chr(10).join([f"- ${p['monto']} por {p['tipo_pago']} ({p['fase']})" for p in pagos])}
Total pagado: ${total_pagado}

INFERENCIAS Y REGLAS APLICADAS:
{inferencias_texto if inferencias_texto else "No se registraron inferencias adicionales."}

Genera un resumen estructurado que incluya:
1. Resumen del apartado
2. Explicación de cada regla que se aplicó y por qué
3. Estado actual del pedido
4. Próximos pasos para el cliente

Responde en español, de forma clara y empática.
"""

    try:
        resumen_texto = llamar_modelo(prompt)

        if not resumen_texto:
            raise Exception("Todos los modelos fallaron")

        registrar_inferencia(
            folio=folio,
            regla="REGLA_RESUMEN_GENERADO",
            descripcion=f"Agente Supervisor generó resumen para folio {folio}",
            resultado="Resumen enviado al cliente"
        )

        return {
            "exito": True,
            "folio": folio,
            "resumen": resumen_texto,
            "datos": {
                "apartado": apartado,
                "pagos": pagos,
                "total_pagado": total_pagado,
                "inferencias": inferencias
            }
        }

    except Exception as e:
        print(f"Error en generar_resumen_venta: {e}")
        return {
            "exito": False,
            "mensaje": f"Error al generar resumen: {str(e)}"
        }

def explicar_decision(regla):
    """Explica en lenguaje natural qué hace una regla específica."""
    explicaciones = {
        "REGLA_MONTO_INVALIDO": (
            "Esta regla protege al negocio y al cliente. "
            "Solo se aceptan anticipos de $250, $300, $500 o $750 pesos. "
            "Montos menores a $250 no cubren el costo mínimo del paquete."
        ),
        "REGLA_DUPLICADO": (
            "Esta regla evita cobros dobles. "
            "Si un alumno ya fue registrado (por ejemplo, por el papá), "
            "el sistema detecta el intento de registro duplicado (de la mamá) "
            "y detiene el proceso, avisando que ya existe un apartado previo."
        ),
        "REGLA_CORRECCION_GRADO": (
            "Esta regla corrige automáticamente errores de escritura en el grado. "
            "Si el padre escribe '3ro de secund' el sistema lo interpreta como "
            "'3° secundaria' para evitar confusiones en el pedido."
        ),
        "REGLA_DATOS_INCOMPLETOS": (
            "Esta regla asegura que el registro esté completo. "
            "No se genera un folio hasta tener nombre del alumno, "
            "grado, nombre del tutor y teléfono de contacto."
        ),
        "REGLA_FRUSTRACION": (
            "Esta regla detecta cuando un cliente está confundido o frustrado. "
            "Si escribe palabras como 'no entiendo' o comete 3 errores seguidos, "
            "el sistema activa un modo de ayuda más empático y detallado."
        ),
        "REGLA_FOLIO_GENERADO": (
            "Esta regla se activa cuando todos los datos son válidos y el pago es correcto. "
            "El sistema genera automáticamente un folio único (ej: ZN-847291) "
            "que sirve como comprobante oficial del apartado."
        ),
        "REGLA_PAGO_EFECTIVO": (
            "Esta regla maneja los pagos en efectivo. "
            "En lugar de requerir transferencia inmediata, "
            "el sistema marca el apartado para cobrarse el día de la entrega."
        ),
        "REGLA_CALCULO_SALDO": (
            "Esta regla calcula automáticamente cuánto debe el cliente. "
            "Suma todos los anticipos pagados y los resta del precio final "
            "cuando la escuela publica las listas oficiales."
        ),
    }
    return explicaciones.get(
        regla,
        f"La regla '{regla}' es una verificación interna del sistema experto."
    )

def validar_apartado_final(folio, nombre_tutor_confirmado):
    """Verifica la identidad del tutor antes de mostrar información."""
    apartado = buscar_por_folio(folio)
    if not apartado:
        return {"valido": False, "mensaje": "Folio no encontrado."}

    nombre_bd = apartado["nombre_tutor"].lower().strip()
    nombre_confirmado = nombre_tutor_confirmado.lower().strip()

    if nombre_bd in nombre_confirmado or nombre_confirmado in nombre_bd:
        registrar_inferencia(
            folio=folio,
            regla="REGLA_VALIDACION_TUTOR",
            descripcion=f"Tutor '{nombre_tutor_confirmado}' confirmó el apartado",
            resultado="Identidad verificada — apartado confirmado"
        )
        return {
            "valido": True,
            "mensaje": f"✅ Identidad verificada. El apartado del folio {folio} está confirmado."
        }
    else:
        registrar_inferencia(
            folio=folio,
            regla="REGLA_VALIDACION_TUTOR",
            descripcion=f"Nombre '{nombre_tutor_confirmado}' no coincide con '{apartado['nombre_tutor']}'",
            resultado="Validación fallida — datos no coinciden"
        )
        return {
            "valido": False,
            "mensaje": "❌ El nombre no coincide con el registrado. Por seguridad, no se puede mostrar la información."
        }