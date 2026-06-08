import streamlit as st
import pandas as pd
from database.db import get_connection

st.set_page_config(
    page_title="Admin — Sistema ZN",
    page_icon="🛠️",
    layout="wide"
)

# Ocultar sidebar completamente
st.markdown("""
    <style>
    [data-testid="stSidebar"] {display: none;}
    [data-testid="stSidebarNav"] {display: none;}
    </style>
""", unsafe_allow_html=True)

# ─── Verificar acceso ─────────────────────────────────────────────────────────
if "admin_autenticado" not in st.session_state:
    st.session_state.admin_autenticado = False

if not st.session_state.admin_autenticado:
    st.title("🔐 Acceso Administrador")
    st.markdown("Esta área es solo para personal autorizado de Papelería ZN.")

    with st.form("login_form"):
        password = st.text_input("Contraseña:", type="password")
        submit = st.form_submit_button("Entrar")

        if submit:
            if password == "admin123":
                st.session_state.admin_autenticado = True
                st.rerun()
            else:
                st.error("❌ Contraseña incorrecta")
    st.stop()

# ─── Panel principal ──────────────────────────────────────────────────────────
st.title("🛠️ Panel de Administrador — Papelería ZN")
st.caption("Acceso restringido al personal autorizado")

if st.button("🚪 Cerrar sesión y volver al inicio"):
    st.session_state.admin_autenticado = False
    st.switch_page("main.py")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Apartados",
    "💰 Pagos",
    "🧠 Inferencias",
    "📊 Resumen"
])

# ─── Tab 1: Apartados ─────────────────────────────────────────────────────────
with tab1:
    st.markdown("### Todos los apartados registrados")

    buscar = st.text_input("🔍 Buscar por alumno o folio:")

    conn = get_connection()
    if buscar:
        df = pd.read_sql_query("""
            SELECT folio, nombre_alumno, grado, nombre_tutor,
                   telefono_principal, estado, fecha_registro
            FROM apartados
            WHERE nombre_alumno LIKE ? OR folio LIKE ?
            ORDER BY fecha_registro DESC
        """, conn, params=[f"%{buscar}%", f"%{buscar}%"])
    else:
        df = pd.read_sql_query("""
            SELECT folio, nombre_alumno, grado, nombre_tutor,
                   telefono_principal, estado, fecha_registro
            FROM apartados
            ORDER BY fecha_registro DESC
        """, conn)
    conn.close()

    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.markdown(f"**Total de apartados:** {len(df)}")

        st.divider()
        st.markdown("### ✏️ Modificar un apartado")

        folio_sel = st.selectbox("Selecciona el folio a modificar:", df["folio"].tolist())

        if folio_sel:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM apartados WHERE folio = ?", (folio_sel,))
            reg = dict(cursor.fetchone())
            conn.close()

            col1, col2 = st.columns(2)
            with col1:
                nuevo_nombre = st.text_input("Nombre del alumno:", value=reg["nombre_alumno"])
                nuevo_grado = st.selectbox("Grado:", [
                    "1° primaria", "2° primaria", "3° primaria",
                    "4° primaria", "5° primaria", "6° primaria",
                    "1° secundaria", "2° secundaria", "3° secundaria"
                ], index=["1° primaria", "2° primaria", "3° primaria",
                    "4° primaria", "5° primaria", "6° primaria",
                    "1° secundaria", "2° secundaria", "3° secundaria"
                ].index(reg["grado"]) if reg["grado"] in [
                    "1° primaria", "2° primaria", "3° primaria",
                    "4° primaria", "5° primaria", "6° primaria",
                    "1° secundaria", "2° secundaria", "3° secundaria"
                ] else 0)
                nuevo_tutor = st.text_input("Nombre del tutor:", value=reg["nombre_tutor"])

            with col2:
                nuevo_telefono = st.text_input("Teléfono principal:", value=reg["telefono_principal"])
                nuevo_estado = st.selectbox("Estado:", ["pendiente", "pagado", "cancelado", "entregado"],
                    index=["pendiente", "pagado", "cancelado", "entregado"].index(reg["estado"])
                    if reg["estado"] in ["pendiente", "pagado", "cancelado", "entregado"] else 0)

            col_guardar, col_cancelar_reg = st.columns(2)
            with col_guardar:
                if st.button("💾 Guardar cambios", use_container_width=True):
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE apartados
                        SET nombre_alumno = ?, grado = ?, nombre_tutor = ?,
                            telefono_principal = ?, estado = ?
                        WHERE folio = ?
                    """, (nuevo_nombre, nuevo_grado, nuevo_tutor,
                          nuevo_telefono, nuevo_estado, folio_sel))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Apartado {folio_sel} actualizado correctamente.")
                    st.rerun()

            with col_cancelar_reg:
                if st.button("❌ Cancelar este apartado", use_container_width=True):
                    st.session_state[f"confirmar_cancelar_{folio_sel}"] = True

            if st.session_state.get(f"confirmar_cancelar_{folio_sel}", False):
                st.warning(f"⚠️ ¿Estás seguro de que deseas cancelar el apartado **{folio_sel}**?")
                col_si, col_no = st.columns(2)
                with col_si:
                    if st.button("✅ Sí, cancelar", use_container_width=True):
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("UPDATE apartados SET estado = 'cancelado' WHERE folio = ?", (folio_sel,))
                        conn.commit()
                        conn.close()
                        st.session_state[f"confirmar_cancelar_{folio_sel}"] = False
                        st.success(f"Apartado {folio_sel} cancelado.")
                        st.rerun()
                with col_no:
                    if st.button("❌ No, regresar", use_container_width=True):
                        st.session_state[f"confirmar_cancelar_{folio_sel}"] = False
                        st.rerun()

        st.divider()
        st.markdown("### 🗑️ Eliminar un apartado")
        st.caption("⚠️ Esta acción es permanente y no se puede deshacer.")

        folio_borrar = st.text_input("Escribe el folio exacto para eliminar:")
        confirmar = st.checkbox("Confirmo que quiero eliminar este registro permanentemente")

        if st.button("🗑️ Eliminar registro", use_container_width=True):
            if folio_borrar and confirmar:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM apartados WHERE folio = ?", (folio_borrar,))
                cursor.execute("DELETE FROM pagos WHERE folio = ?", (folio_borrar,))
                cursor.execute("DELETE FROM inferencias WHERE folio = ?", (folio_borrar,))
                conn.commit()
                conn.close()
                st.success(f"✅ Registro {folio_borrar} eliminado completamente.")
                st.rerun()
            elif not confirmar:
                st.error("Debes marcar la casilla de confirmación para eliminar.")
            else:
                st.error("Escribe el folio exacto para eliminar.")
    else:
        st.info("No hay apartados que coincidan con la búsqueda.")

# ─── Tab 2: Pagos ─────────────────────────────────────────────────────────────
with tab2:
    st.markdown("### Todos los pagos registrados")

    conn = get_connection()
    df_pagos = pd.read_sql_query("""
        SELECT p.folio, a.nombre_alumno, a.grado,
               p.monto, p.tipo_pago, p.fase, p.fecha_pago
        FROM pagos p
        JOIN apartados a ON p.folio = a.folio
        ORDER BY p.fecha_pago DESC
    """, conn)
    conn.close()

    if not df_pagos.empty:
        st.dataframe(df_pagos, use_container_width=True, hide_index=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            total = df_pagos["monto"].sum()
            st.metric("💵 Total recaudado", f"${total:.2f}")
        with col2:
            transferencias = df_pagos[df_pagos["tipo_pago"] == "transferencia"]["monto"].sum()
            st.metric("🏦 Por transferencia", f"${transferencias:.2f}")
        with col3:
            efectivo = df_pagos[df_pagos["tipo_pago"] == "efectivo"]["monto"].sum()
            st.metric("💵 Por efectivo", f"${efectivo:.2f}")
    else:
        st.info("No hay pagos registrados aún.")

# ─── Tab 3: Inferencias ───────────────────────────────────────────────────────
with tab3:
    st.markdown("### Log de inferencias del sistema experto")
    st.caption("Aquí se registra cada decisión tomada por los agentes")

    conn = get_connection()
    df_inf = pd.read_sql_query("""
        SELECT fecha, folio, regla_aplicada, descripcion, resultado
        FROM inferencias
        ORDER BY fecha DESC
        LIMIT 100
    """, conn)
    conn.close()

    if not df_inf.empty:
        st.dataframe(df_inf, use_container_width=True, hide_index=True)
        st.markdown(f"**Total de inferencias registradas:** {len(df_inf)}")
    else:
        st.info("No hay inferencias registradas aún.")

# ─── Tab 4: Resumen ───────────────────────────────────────────────────────────
with tab4:
    st.markdown("### Resumen general del negocio")

    conn = get_connection()
    total_apartados = pd.read_sql_query(
        "SELECT COUNT(*) as total FROM apartados", conn
    ).iloc[0]["total"]

    total_pagado = pd.read_sql_query(
        "SELECT COALESCE(SUM(monto), 0) as total FROM pagos", conn
    ).iloc[0]["total"]

    por_tipo_pago = pd.read_sql_query("""
        SELECT tipo_pago, COUNT(*) as cantidad, SUM(monto) as total
        FROM pagos
        GROUP BY tipo_pago
    """, conn)

    por_grado = pd.read_sql_query("""
        SELECT grado, COUNT(*) as cantidad
        FROM apartados
        GROUP BY grado
        ORDER BY cantidad DESC
    """, conn)

    ultimos = pd.read_sql_query("""
        SELECT folio, nombre_alumno, grado, estado, fecha_registro
        FROM apartados
        ORDER BY fecha_registro DESC
        LIMIT 5
    """, conn)
    conn.close()

    # Métricas principales
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📋 Total de apartados", total_apartados)
    with col2:
        st.metric("💰 Total recaudado", f"${total_pagado:.2f} pesos")

    st.divider()

    # Pagos por tipo
    col3, col4 = st.columns(2)
    with col3:
        st.markdown("#### 💳 Pagos por tipo")
        if not por_tipo_pago.empty:
            for _, row in por_tipo_pago.iterrows():
                tipo = "Transferencia" if row["tipo_pago"] == "transferencia" else "Efectivo"
                st.markdown(f"- **{tipo}:** {int(row['cantidad'])} pagos — ${row['total']:.2f}")
        else:
            st.info("Sin pagos registrados.")

    with col4:
        st.markdown("#### 📚 Apartados por grado")
        if not por_grado.empty:
            for _, row in por_grado.iterrows():
                st.markdown(f"- **{row['grado']}:** {int(row['cantidad'])} alumno(s)")
        else:
            st.info("Sin apartados registrados.")

    st.divider()

    # Últimos registros
    st.markdown("#### 🕐 Últimos 5 apartados registrados")
    if not ultimos.empty:
        st.dataframe(ultimos, use_container_width=True, hide_index=True)
    else:
        st.info("Sin registros aún.")