import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from database.db import (
    verificar_duplicado,
    buscar_por_folio,
    buscar_por_telefono,
    registrar_inferencia
)

from pathlib import Path
load_dotenv(Path(__file__).parent.parent / ".env")

cliente = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

GRADOS_VALIDOS = [
    "1° primaria", "2° primaria", "3° primaria",
    "4° primaria", "5° primaria", "6° primaria",
    "1° secundaria", "2° secundaria", "3° secundaria"
]

PROMPT_SISTEMA = """
Eres un asistente virtual amable y empático de una papelería escolar llamada ZN.
Tu trabajo es ayudar a padres de familia a apartar paquetes de útiles escolares.

Reglas importantes:
1. Siempre habla en español, de forma clara y sencilla
2. Si el padre escribe con faltas de ortografía, entiéndelo igual
3. Recolecta SIEMPRE estos datos antes de continuar:
   - Nombre completo del alumno (con dos apellidos)
   - Grado escolar (1° a 6° primaria o 1° a 3° secundaria)
   - Si es el grado al que PASARÁ en el próximo ciclo
   - Nombre del tutor
   - Teléfono principal
4. Sé paciente y empático, especialmente con adultos mayores
5. 5. Si detectas frustración (palabras como "no entiendo", "ayuda", "no puedo"),
   responde con mucha calma y ofrece ayuda paso a paso. En caso de frustración
   severa, indica al cliente que puede comunicarse directamente al WhatsApp
   33-1429-6216 para atención personalizada.
Responde SIEMPRE en formato JSON con esta estructura:
{
  "mensaje": "tu respuesta al padre de familia",
  "intencion": "nuevo_apartado|consulta_folio|consulta_telefono|pago|otro",
  "datos_recolectados": {
    "nombre_alumno": null,
    "grado": null,
    "nombre_tutor": null,
    "telefono": null
  },
  "frustrado": false,
  "datos_completos": false
}
"""

def detectar_intencion(mensaje_usuario, historial=[]):
    """Usa OpenRouter para entender qué quiere el usuario."""
    try:
        historial_texto = "\n".join([
            f"{'Usuario' if m['rol'] == 'user' else 'Asistente'}: {m['contenido']}"
            for m in historial[-6:]
        ])

        prompt = f"""
{PROMPT_SISTEMA}

Historial de conversación:
{historial_texto}

Nuevo mensaje del usuario: {mensaje_usuario}

Responde SOLO con el JSON, sin texto adicional.
"""
        respuesta = cliente.chat.completions.create(
            model="google/gemma-4-31b-it:free",
            messages=[{"role": "user", "content": prompt}]
        )
        texto = respuesta.choices[0].message.content.strip()

        if texto.startswith("```"):
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]

        return json.loads(texto.strip())

    except Exception as e:
        print(f"Error en detectar_intencion: {e}")
        return {
            "mensaje": "Disculpa, tuve un problema técnico. ¿Puedes repetir tu mensaje?",
            "intencion": "otro",
            "datos_recolectados": {},
            "frustrado": False,
            "datos_completos": False
        }

def validar_grado(grado_texto):
    """Corrige y valida el grado escolar aunque venga con errores."""
    grado_lower = grado_texto.lower().strip()

    correcciones = {
        "primero": "1°", "segundo": "2°", "tercero": "3°",
        "cuarto": "4°", "quinto": "5°", "sexto": "6°",
        "1ro": "1°", "2do": "2°", "3ro": "3°",
        "4to": "4°", "5to": "5°", "6to": "6°",
        "1": "1°", "2": "2°", "3": "3°",
        "4": "4°", "5": "5°", "6": "6°",
    }

    for key, valor in correcciones.items():
        if key in grado_lower:
            grado_lower = grado_lower.replace(key, valor)

    if "secund" in grado_lower or "sec" in grado_lower:
        nivel = "secundaria"
    else:
        nivel = "primaria"

    for grado_valido in GRADOS_VALIDOS:
        if grado_valido[0:2] in grado_lower and nivel in grado_valido:
            return grado_valido

    return None

def procesar_mensaje(mensaje_usuario, historial, datos_sesion):
    """
    Función principal del Agente 1.
    Recibe el mensaje, lo procesa y retorna la respuesta.
    """
    errores_consecutivos = datos_sesion.get("errores_consecutivos", 0)

    resultado = detectar_intencion(mensaje_usuario, historial)

    datos = resultado.get("datos_recolectados", {})
    if datos.get("grado"):
        grado_validado = validar_grado(datos["grado"])
        if grado_validado:
            datos["grado"] = grado_validado
            registrar_inferencia(
                folio=None,
                regla="REGLA_CORRECCION_GRADO",
                descripcion=f"Grado ingresado: '{datos.get('grado')}' → Corregido a: '{grado_validado}'",
                resultado="Corrección aplicada automáticamente"
            )

    if resultado.get("frustrado") or errores_consecutivos >= 3:
        registrar_inferencia(
            folio=None,
            regla="REGLA_FRUSTRACION",
            descripcion=f"Usuario mostró señales de frustración o cometió {errores_consecutivos} errores seguidos",
            resultado="Activado protocolo de ayuda empática"
        )
        datos_sesion["frustracion_detectada"] = True

    intencion = resultado.get("intencion", "otro")

    if intencion == "consulta_folio":
        folio_buscar = mensaje_usuario.upper().strip()
        if folio_buscar.startswith("ZN-"):
            apartado = buscar_por_folio(folio_buscar)
            if apartado:
                registrar_inferencia(
                    folio=folio_buscar,
                    regla="REGLA_CONSULTA_FOLIO",
                    descripcion=f"Cliente consultó folio {folio_buscar}",
                    resultado="Folio encontrado - información enviada al cliente"
                )
            else:
                registrar_inferencia(
                    folio=folio_buscar,
                    regla="REGLA_FOLIO_NO_ENCONTRADO",
                    descripcion=f"Folio {folio_buscar} no existe en la base de datos",
                    resultado="Se informó al cliente que el folio no existe"
                )

    datos_sesion.update(datos)

    return {
        "respuesta": resultado.get("mensaje", "¿En qué puedo ayudarte?"),
        "intencion": intencion,
        "datos_sesion": datos_sesion,
        "datos_completos": resultado.get("datos_completos", False),
        "frustrado": resultado.get("frustrado", False)
    }