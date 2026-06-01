import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
from database.db import (
    registrar_apartado,
    registrar_pago,
    verificar_duplicado,
    buscar_por_folio,
    obtener_pagos,
    registrar_inferencia
)

load_dotenv(Path(__file__).parent.parent / ".env")

cliente = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

MONTOS_VALIDOS = [250, 300, 500, 750]
ANTICIPO_MINIMO = 250

REGLAS_INFERENCIA = {
    "REGLA_MONTO_INVALIDO": "IF monto < 250 THEN rechazar pago",
    "REGLA_DUPLICADO": "IF alumno+grado ya existe THEN alertar y detener registro",
    "REGLA_GRADO_INVALIDO": "IF grado NOT IN grados_validos THEN solicitar corrección",
    "REGLA_DATOS_INCOMPLETOS": "IF datos_incompletos THEN solicitar datos faltantes",
    "REGLA_PAGO_EFECTIVO": "IF tipo_pago == efectivo THEN marcar para cobro en entrega",
    "REGLA_FOLIO_GENERADO": "IF datos_completos AND pago_valido THEN generar folio único",
}

def validar_datos_completos(datos_sesion):
    campos_requeridos = {
        "nombre_alumno": "nombre completo del alumno",
        "grado": "grado escolar",
        "nombre_tutor": "nombre del tutor",
        "telefono": "número de teléfono"
    }
    faltantes = []
    for campo, descripcion in campos_requeridos.items():
        valor = datos_sesion.get(campo)
        if not valor or valor == "null" or valor is None:
            faltantes.append(descripcion)
    return faltantes

def validar_monto(monto):
    try:
        monto_num = float(monto)
    except (ValueError, TypeError):
        return False, "El monto ingresado no es válido."
    if monto_num < ANTICIPO_MINIMO:
        registrar_inferencia(
            folio=None,
            regla="REGLA_MONTO_INVALIDO",
            descripcion=f"Monto ingresado: ${monto_num} — menor al mínimo de ${ANTICIPO_MINIMO}",
            resultado="Pago rechazado — se solicitó monto válido"
        )
        return False, f"❌ No se aceptan anticipos menores a ${ANTICIPO_MINIMO} pesos."
    if monto_num not in MONTOS_VALIDOS:
        registrar_inferencia(
            folio=None,
            regla="REGLA_MONTO_INVALIDO",
            descripcion=f"Monto ingresado: ${monto_num} — no está en la lista de montos permitidos",
            resultado="Pago rechazado — se sugirieron montos válidos"
        )
        return False, f"❌ Monto no válido. Los montos permitidos son: {', '.join([f'${m}' for m in MONTOS_VALIDOS])} pesos."
    return True, "Monto válido."

def verificar_duplicado_con_inferencia(nombre_alumno, grado):
    duplicado = verificar_duplicado(nombre_alumno, grado)
    if duplicado:
        registrar_inferencia(
            folio=duplicado.get("folio"),
            regla="REGLA_DUPLICADO",
            descripcion=f"Intento de registro duplicado: {nombre_alumno} en {grado}",
            resultado=f"Registro detenido — ya existe con folio {duplicado.get('folio')} bajo teléfono {duplicado.get('telefono_principal')}"
        )
        return duplicado
    return None

def procesar_nuevo_apartado(datos_sesion, monto, tipo_pago):
    resultado = {
        "exito": False,
        "folio": None,
        "mensaje": "",
        "inferencias": [],
        "errores": []
    }

    faltantes = validar_datos_completos(datos_sesion)
    if faltantes:
        registrar_inferencia(
            folio=None,
            regla="REGLA_DATOS_INCOMPLETOS",
            descripcion=f"Faltan datos: {', '.join(faltantes)}",
            resultado="Registro detenido — se solicitaron datos faltantes"
        )
        resultado["mensaje"] = f"❌ Faltan los siguientes datos: {', '.join(faltantes)}"
        resultado["errores"].append("datos_incompletos")
        resultado["inferencias"].append("REGLA_DATOS_INCOMPLETOS")
        return resultado

    nombre = datos_sesion.get("nombre_alumno")
    grado = datos_sesion.get("grado")
    duplicado = verificar_duplicado_con_inferencia(nombre, grado)

    if duplicado:
        resultado["mensaje"] = (
            f"⚠️ Ya existe un apartado para *{nombre}* en *{grado}*.\n"
            f"Fue registrado previamente con el folio *{duplicado.get('folio')}*.\n"
            f"¿Deseas consultar ese apartado?"
        )
        resultado["errores"].append("duplicado")
        resultado["inferencias"].append("REGLA_DUPLICADO")
        return resultado

    monto_valido, mensaje_monto = validar_monto(monto)
    if not monto_valido:
        resultado["mensaje"] = mensaje_monto
        resultado["errores"].append("monto_invalido")
        resultado["inferencias"].append("REGLA_MONTO_INVALIDO")
        return resultado

    try:
        folio = registrar_apartado(
            nombre_alumno=datos_sesion.get("nombre_alumno"),
            grado=datos_sesion.get("grado"),
            nombre_tutor=datos_sesion.get("nombre_tutor"),
            telefono_principal=datos_sesion.get("telefono"),
            telefono_secundario=datos_sesion.get("telefono_secundario")
        )
        registrar_pago(folio=folio, monto=float(monto), tipo_pago=tipo_pago)
        registrar_inferencia(
            folio=folio,
            regla="REGLA_FOLIO_GENERADO",
            descripcion=f"Datos completos y pago válido de ${monto} por {tipo_pago}",
            resultado=f"Folio {folio} generado exitosamente"
        )
        resultado["exito"] = True
        resultado["folio"] = folio
        resultado["inferencias"].append("REGLA_FOLIO_GENERADO")

        if tipo_pago == "efectivo":
            registrar_inferencia(
                folio=folio,
                regla="REGLA_PAGO_EFECTIVO",
                descripcion="Cliente eligió pago en efectivo",
                resultado="Marcado para cobro en día de entrega"
            )
            resultado["inferencias"].append("REGLA_PAGO_EFECTIVO")
            resultado["mensaje"] = (
                f"✅ ¡Apartado registrado exitosamente!\n\n"
                f"📋 *Tu folio es: {folio}*\n\n"
                f"👤 Alumno: {datos_sesion.get('nombre_alumno')}\n"
                f"📚 Grado: {datos_sesion.get('grado')}\n"
                f"💵 Pago: ${monto} en efectivo el día de la entrega\n\n"
                f"Guarda tu folio, lo necesitarás para recoger tu paquete. 📝"
            )
        else:
            resultado["mensaje"] = (
                f"✅ ¡Apartado registrado exitosamente!\n\n"
                f"📋 *Tu folio es: {folio}*\n\n"
                f"👤 Alumno: {datos_sesion.get('nombre_alumno')}\n"
                f"📚 Grado: {datos_sesion.get('grado')}\n"
                f"💰 Anticipo pagado: ${monto} por transferencia\n\n"
                f"Guarda tu folio, lo necesitarás para recoger tu paquete. 📝"
            )
    except Exception as e:
        resultado["mensaje"] = "❌ Hubo un error al guardar el registro. Por favor intenta de nuevo."
        resultado["errores"].append(str(e))

    return resultado

def calcular_saldo(folio):
    apartado = buscar_por_folio(folio)
    if not apartado:
        return None
    pagos = obtener_pagos(folio)
    total_pagado = sum(p["monto"] for p in pagos)
    registrar_inferencia(
        folio=folio,
        regla="REGLA_CALCULO_SALDO",
        descripcion=f"Total pagado hasta ahora: ${total_pagado}",
        resultado="Precio final pendiente de definir por la escuela"
    )
    return {
        "apartado": apartado,
        "pagos": pagos,
        "total_pagado": total_pagado,
        "precio_final": None,
        "saldo_pendiente": None,
        "mensaje": f"Has pagado un anticipo de ${total_pagado}. El precio final se definirá cuando la escuela publique las listas oficiales."
    }