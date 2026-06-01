import streamlit as st
from agents.agente1_atencion import procesar_mensaje
from agents.agente2_procesador import procesar_nuevo_apartado, calcular_saldo
from agents.agente3_supervisor import generar_resumen_venta, explicar_decision, validar_apartado_final
from database.db import inicializar_db, buscar_por_folio, buscar_por_telefono

# Inicializar la base de datos al arrancar
inicializar_db()

# ─── Configuración de la página ───────────────────────────────────────────────
st.set_page_config(
    page_title="Sistema ZN - Apartado de Útiles",
    page_icon="📚",
    layout="centered"
)

st.title("📚 Cuadernos ZN")
st.subheader("Sistema de Apartado de Útiles Escolares")
st.divider()

# ─── Inicializar estado de sesión ─────────────────────────────────────────────
if "historial" not in st.session_state:
    st.session_state.historial = []

if "datos_sesion" not in st.session_state:
    st.session_state.datos_sesion = {}

if "etapa" not in st.session_state:
    st.session_state.etapa = "inicio"

if "folio_actual" not in st.session_state:
    st.session_state.folio_actual = None

# ─── Mostrar historial de mensajes ────────────────────────────────────────────
for mensaje in st.session_state.historial:
    with st.chat_message(mensaje["rol"]):
        st.markdown(mensaje["contenido"])

# ─── Mensaje de bienvenida ────────────────────────────────────────────────────
if len(st.session_state.historial) == 0:
    with st.chat_message("assistant"):
        bienvenida = (
            "👋 ¡Bienvenido a Papelería ZN!\n\n"
            "Estoy aquí para ayudarte a apartar el paquete de útiles "
            "escolares de tu hijo. ¿Qué deseas hacer hoy?"
        )
        st.markdown(bienvenida)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 Hacer un nuevo apartado", use_container_width=True):
            st.session_state.etapa = "nuevo_apartado"
            st.session_state.historial.append({
                "rol": "assistant",
                "contenido": bienvenida
            })
            st.session_state.historial.append({
                "rol": "user",
                "contenido": "Quiero hacer un nuevo apartado"
            })
            st.rerun()

    with col2:
        if st.button("🔍 Consultar apartado existente", use_container_width=True):
            st.session_state.etapa = "consulta"
            st.session_state.historial.append({
                "rol": "assistant",
                "contenido": bienvenida
            })
            st.session_state.historial.append({
                "rol": "user",
                "contenido": "Quiero consultar un apartado existente"
            })
            st.rerun()

# ─── Etapa: Nuevo apartado ────────────────────────────────────────────────────
if st.session_state.etapa == "nuevo_apartado":

    if not st.session_state.datos_sesion.get("datos_completos"):
        mensaje_usuario = st.chat_input("Escribe tu mensaje aquí...")

        if mensaje_usuario:
            with st.chat_message("user"):
                st.markdown(mensaje_usuario)
            st.session_state.historial.append({
                "rol": "user",
                "contenido": mensaje_usuario
            })

            with st.spinner("Procesando..."):
                resultado = procesar_mensaje(
                    mensaje_usuario,
                    st.session_state.historial,
                    st.session_state.datos_sesion
                )

            st.session_state.datos_sesion = resultado["datos_sesion"]

            with st.chat_message("assistant"):
                st.markdown(resultado["respuesta"])
            st.session_state.historial.append({
                "rol": "assistant",
                "contenido": resultado["respuesta"]
            })

            if resultado.get("datos_completos"):
                st.session_state.datos_sesion["datos_completos"] = True

            st.rerun()

    else:
        # Datos completos — mostrar selección de pago
        st.success("✅ Datos recolectados correctamente")
        st.info(
            f"**Alumno:** {st.session_state.datos_sesion.get('nombre_alumno')}\n\n"
            f"**Grado:** {st.session_state.datos_sesion.get('grado')}\n\n"
            f"**Tutor:** {st.session_state.datos_sesion.get('nombre_tutor')}\n\n"
            f"**Teléfono:** {st.session_state.datos_sesion.get('telefono')}"
        )

        st.markdown("### 💰 Selecciona el monto de anticipo:")
        st.warning("⚠️ No se aceptan anticipos menores a $250 pesos")

        col1, col2, col3, col4 = st.columns(4)
        if "monto_seleccionado" not in st.session_state:
            st.session_state.monto_seleccionado = None

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("💵 $250", use_container_width=True):
                st.session_state.monto_seleccionado = 250
        with col2:
            if st.button("💵 $300", use_container_width=True):
                st.session_state.monto_seleccionado = 300
        with col3:
            if st.button("💵 $500", use_container_width=True):
                st.session_state.monto_seleccionado = 500
        with col4:
            if st.button("💵 $750", use_container_width=True):
                st.session_state.monto_seleccionado = 750

        if st.session_state.monto_seleccionado:
            st.markdown("### 🏦 Selecciona el tipo de pago:")
            col_a, col_b = st.columns(2)

            with col_a:
                if st.button("🏦 Transferencia bancaria", use_container_width=True):
                    with st.spinner("Registrando apartado..."):
                        resultado = procesar_nuevo_apartado(
                            st.session_state.datos_sesion,
                            st.session_state.monto_seleccionado,
                            "transferencia"
                        )
                    if resultado["exito"]:
                        st.session_state.folio_actual = resultado["folio"]
                        st.session_state.etapa = "resumen"
                    st.session_state.historial.append({
                        "rol": "assistant",
                        "contenido": resultado["mensaje"]
                    })
                    st.rerun()

            with col_b:
                if st.button("💵 Efectivo en entrega", use_container_width=True):
                    with st.spinner("Registrando apartado..."):
                        resultado = procesar_nuevo_apartado(
                            st.session_state.datos_sesion,
                            st.session_state.monto_seleccionado,
                            "efectivo"
                        )
                    if resultado["exito"]:
                        st.session_state.folio_actual = resultado["folio"]
                        st.session_state.etapa = "resumen"
                        st.session_state.monto_seleccionado = None
                    st.session_state.historial.append({
                        "rol": "assistant",
                        "contenido": resultado["mensaje"]
                    })
                    st.rerun()

# ─── Etapa: Consulta ──────────────────────────────────────────────────────────
elif st.session_state.etapa == "consulta":
    st.markdown("### 🔍 ¿Cómo deseas consultar tu apartado?")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📋 Por número de folio", use_container_width=True):
            st.session_state.etapa = "consulta_folio"
            st.rerun()
    with col2:
        if st.button("📱 Por número de teléfono", use_container_width=True):
            st.session_state.etapa = "consulta_telefono"
            st.rerun()

elif st.session_state.etapa == "consulta_folio":
    folio_input = st.text_input("Ingresa tu número de folio (ej: ZN-123456):")
    nombre_tutor_input = st.text_input("Ingresa el nombre del tutor registrado:")

    if st.button("🔍 Buscar", use_container_width=True):
        if folio_input and nombre_tutor_input:
            validacion = validar_apartado_final(folio_input.upper(), nombre_tutor_input)
            if validacion["valido"]:
                resumen = generar_resumen_venta(folio_input.upper())
                if resumen["exito"]:
                    st.success(resumen["resumen"])
                    st.session_state.folio_actual = folio_input.upper()
                    st.session_state.etapa = "resumen"
                    st.rerun()
            else:
                st.error(validacion["mensaje"])

elif st.session_state.etapa == "consulta_telefono":
    telefono_input = st.text_input("Ingresa tu número de teléfono:")
    if st.button("🔍 Buscar", use_container_width=True):
        if telefono_input:
            resultados = buscar_por_telefono(telefono_input)
            if resultados:
                for apt in resultados:
                    st.info(
                        f"**Folio:** {apt['folio']}\n\n"
                        f"**Alumno:** {apt['nombre_alumno']}\n\n"
                        f"**Grado:** {apt['grado']}\n\n"
                        f"**Estado:** {apt['estado']}"
                    )
            else:
                st.error("No se encontraron apartados con ese número de teléfono.")

# ─── Etapa: Resumen final ─────────────────────────────────────────────────────
elif st.session_state.etapa == "resumen":
    if st.session_state.folio_actual:
        resumen = generar_resumen_venta(st.session_state.folio_actual)
        if resumen["exito"]:
            st.success(resumen["resumen"])

            with st.expander("🧠 Ver inferencias del sistema experto"):
                for inf in resumen["datos"]["inferencias"]:
                    st.markdown(f"**Regla:** `{inf['regla_aplicada']}`")
                    st.markdown(f"**Descripción:** {inf['descripcion']}")
                    st.markdown(f"**Resultado:** {inf['resultado']}")
                    st.markdown(f"*Explicación:* {explicar_decision(inf['regla_aplicada'])}")
                    st.divider()

    if st.button("🏠 Volver al inicio", use_container_width=True):
        st.session_state.historial = []
        st.session_state.datos_sesion = {}
        st.session_state.etapa = "inicio"
        st.session_state.folio_actual = None
        st.rerun()

# ─── Sidebar con información ──────────────────────────────────────────────────
with st.sidebar:
    st.image("https://via.placeholder.com/150x50?text=Papelería+ZN", use_column_width=True)
    st.markdown("### 📞 Contacto")
    st.markdown("WhatsApp: 33-XXXX-XXXX")
    st.markdown("Horario: Lun-Sáb 9am-7pm")
    st.divider()
    st.markdown("### ℹ️ Información")
    st.markdown("- Anticipo mínimo: **$250**")
    st.markdown("- Grados: **1° a 6° Primaria**")
    st.markdown("- Grados: **1° a 3° Secundaria**")
    st.divider()
    st.caption("Sistema Experto ZN v1.0")