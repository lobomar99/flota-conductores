"""
Panel Móvil de Control de Flota - Edición Conductores
- Tarjetas de vehículos con Bastidor, Ruedas, Frenos e ITV
- 3 Pestañas de acción: Actualizar Km, Registro de Taller y Averías
- Conexión segura a Supabase vía Secrets de Streamlit
"""

import streamlit as st
import psycopg2
import datetime
import os

# --- 1. CONFIGURACIÓN DE PÁGINA MÓVIL ---
st.set_page_config(
    page_title="Flota Móvil - Panel Conductor",
    page_icon="🚛",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 2. ESTILOS CSS PROFESIONALES ---
st.markdown("""
    <style>
    .stApp {
        background-color: #F8FAFC;
    }
    .custom-card {
        background-color: #FFFFFF;
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 12px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
    }
    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 2px solid #F1F5F9;
        padding-bottom: 10px;
        margin-bottom: 12px;
    }
    .matricula-title {
        font-size: 1.25rem;
        font-weight: 800;
        color: #1E3A8A;
        letter-spacing: 0.5px;
    }
    .badge-estado {
        font-size: 0.75rem;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 20px;
        color: white;
        text-transform: uppercase;
    }
    .card-row {
        font-size: 0.95rem;
        color: #334155;
        margin: 4px 0;
    }
    .highlight-bastidor {
        font-family: monospace;
        font-weight: 700;
        color: #0F172A;
        background: #F1F5F9;
        padding: 2px 6px;
        border-radius: 4px;
    }
    .critical-box {
        background-color: #F8FAFC;
        border-radius: 8px;
        border-left: 4px solid #0284C7;
        padding: 10px 14px;
        margin: 12px 0 6px 0;
    }
    .critical-item {
        font-size: 0.9rem;
        margin: 3px 0;
        color: #0F172A;
    }
    .critical-value {
        font-weight: 700;
        color: #0F766E;
    }
    div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. LECTURA SEGURA DE SECRETOS ---
def get_secret(key, default=""):
    if hasattr(st, "secrets") and key in st.secrets:
        return st.secrets[key]
    return os.environ.get(key, default)

PIN_ACCESO_CORRECTO = str(get_secret("PIN_ACCESO", "1234"))
DATABASE_URL = get_secret("DATABASE_URL", "")

# --- 4. CONTROL DE ACCESO POR PIN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <span style="font-size: 3rem;">🚛</span>
            <h2 style="color: #1E3A8A; margin: 5px 0;">Control de Flota</h2>
            <p style="color: #64748B; font-size: 0.9rem;">Materiales de Construcción Francisco López</p>
        </div>
    """, unsafe_allow_html=True)

    with st.form("form_pin_login"):
        pin_ingresado = st.text_input("PIN de Acceso:", type="password", max_chars=8, placeholder="Introduce el PIN")
        btn_entrar = st.form_submit_button("Entrar al Panel", type="primary", use_container_width=True)

        if btn_entrar:
            if pin_ingresado == PIN_ACCESO_CORRECTO:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("⚠️ PIN incorrecto.")
    st.stop()

# --- 5. FUNCIONES DE BASE DE DATOS SUPABASE ---
def get_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL no está configurada en los Secrets de Streamlit.")
    return psycopg2.connect(DATABASE_URL)

def iso_a_ddmmyyyy(fecha_iso):
    if not fecha_iso or str(fecha_iso).strip() in ["En curso", "Pendiente", "-", "YYYY-MM-DD", "None"]:
        return "-"
    try:
        dt = datetime.datetime.strptime(str(fecha_iso).strip(), "%Y-%m-%d")
        return dt.strftime("%d-%m-%Y")
    except Exception:
        return str(fecha_iso)

def cargar_datos():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()

        # Cargar vehículos (incluyendo columna bastidor)
        c.execute("""
            SELECT matricula, tipo, conductor, km, itv, seguro, aseguradora, 
                   prox_mant_km, prox_mant_fecha, intervalo_km, estado, bastidor 
            FROM vehiculos ORDER BY matricula ASC;
        """)
        vehiculos = [{
            "matricula": r[0], "tipo": r[1], "conductor": r[2], "km": r[3] or 0,
            "itv": r[4], "seguro": r[5], "aseguradora": r[6], "prox_mant_km": r[7] or 0, 
            "prox_mant_fecha": r[8], "intervalo_km": r[9] or 0, "estado": r[10] or "Operativo", 
            "bastidor": r[11] if r[11] else "-"
        } for r in c.fetchall()]

        # Cargar intervenciones de taller
        c.execute("""
            SELECT orden, fecha_in, matricula, taller, trabajos, km, coste, 
                   tipo_registro, tipo_operacion_preventiva 
            FROM taller ORDER BY orden DESC;
        """)
        taller = [{
            "orden": r[0], "fecha_in": r[1], "matricula": r[2], "taller": r[3],
            "trabajos": r[4], "km": r[5] or 0, "coste": r[6], "tipo_registro": r[7], 
            "tipo_operacion_preventiva": r[8]
        } for r in c.fetchall()]

        return vehiculos, taller
    except Exception as e:
        st.error(f"Error de conexión con Supabase: {e}")
        return [], []
    finally:
        if conn:
            conn.close()

# --- 6. CABECERA PRINCIPAL ---
st.markdown("""
    <div style="background-color: #1E3A8A; padding: 16px 20px; border-radius: 12px; margin-bottom: 16px; color: white;">
        <h3 style="margin: 0; color: white;">📱 Panel de Flota - Conductor</h3>
        <p style="margin: 0; font-size: 0.85rem; color: #93C5FD;">Materiales Francisco López Archilla E Hijos S.L.</p>
    </div>
""", unsafe_allow_html=True)

col_ref, col_out = st.columns([3, 1])
with col_ref:
    if st.button("🔄 Recargar Datos", use_container_width=True):
        st.rerun()
with col_out:
    if st.button("🔒 Salir", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

vehiculos, taller = cargar_datos()

if not vehiculos:
    st.info("No hay vehículos disponibles o no se ha podido conectar a la base de datos.")
    st.stop()

# --- 7. TARJETAS DE VEHÍCULOS Y ACCIONES ---
for v in vehiculos:
    mat = v["matricula"]
    estado = v["estado"]
    color_bg = "#10B981" if estado == "Operativo" else ("#F59E0B" if estado == "En Taller" else "#EF4444")

    # Extraer último registro de neumáticos y frenos
    ult_ruedas = "Sin registro"
    ult_frenos = "Sin registro"
    for t in taller:
        if t["matricula"] == mat:
            op = str(t.get("tipo_operacion_preventiva") or "")
            trab = str(t.get("trabajos") or "")
            f_reg = iso_a_ddmmyyyy(t.get("fecha_in"))
            km_t = t.get("km", 0)

            if ("Neumáticos" in op or "Neumáticos" in trab) and ult_ruedas == "Sin registro":
                ult_ruedas = f"{f_reg} ({km_t:,} km)"
            if ("Freno" in op or "Pastillas" in trab) and ult_frenos == "Sin registro":
                ult_frenos = f"{f_reg} ({km_t:,} km)"

    km_faltantes = v["prox_mant_km"] - v["km"]

    # Renderizar Tarjeta Estilizada
    st.markdown(f"""
        <div class="custom-card">
            <div class="card-header">
                <span class="matricula-title">🚗 {mat}</span>
                <span class="badge-estado" style="background-color: {color_bg};">{estado}</span>
            </div>
            <div class="card-row"><strong>Modelo:</strong> {v['tipo']} | <strong>Conductor:</strong> {v['conductor'] or 'Sin asignar'}</div>
            <div class="card-row"><strong>Nº Bastidor:</strong> <span class="highlight-bastidor">{v['bastidor']}</span></div>
            <div class="critical-box">
                <div class="critical-item">📍 <strong>Kilómetros:</strong> {v['km']:,} km</div>
                <div class="critical-item">📅 <strong>Próx. ITV:</strong> {iso_a_ddmmyyyy(v['itv'])}</div>
                <div class="critical-item">🔧 <strong>Próx. Revisión:</strong> {km_faltantes:,} km faltan ({iso_a_ddmmyyyy(v['prox_mant_fecha'])})</div>
                <div class="critical-item">🛞 <strong>Últ. Ruedas:</strong> <span class="critical-value">{ult_ruedas}</span></div>
                <div class="critical-item">🛑 <strong>Últ. Frenos:</strong> <span class="critical-value">{ult_frenos}</span></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Acordeón de Acciones
    with st.expander(f"⚙️ Registrar Acción / Avería - [{mat}]"):
        tab_km, tab_tal, tab_av = st.tabs(["📝 Actualizar Km", "🛠️ Entrada Taller", "⚠️ Reportar Avería"])

        # 1. PESTAÑA: ACTUALIZAR KM Y ESTADO
        with tab_km:
            with st.form(f"form_km_{mat}"):
                nuevo_km = st.number_input("Kilómetros actuales:", min_value=int(v["km"]), value=int(v["km"]), step=100)
                estados = ["Operativo", "En Taller", "Parado Averiado"]
                idx_est = estados.index(estado) if estado in estados else 0
                nuevo_est = st.selectbox("Estado operativo:", estados, index=idx_est)
                
                if st.form_submit_button("💾 Guardar Kilometraje", use_container_width=True):
                    try:
                        conn = get_connection()
                        c = conn.cursor()
                        c.execute("UPDATE vehiculos SET km = %s, estado = %s WHERE matricula = %s;", (nuevo_km, nuevo_est, mat))
                        conn.commit()
                        conn.close()
                        st.success("¡Kilómetros y estado actualizados!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Error al guardar: {ex}")

        # 2. PESTAÑA: REGISTRAR ENTRADA A TALLER
        with tab_tal:
            with st.form(f"form_tal_{mat}"):
                t_reg = st.selectbox("Tipo de Intervención:", ["Mantenimiento Preventivo", "Avería / Reparación (Correctivo)"])
                op_prev = st.selectbox("Operación Específica:", [
                    "Cambio de Neumáticos", 
                    "Sustitución de Pastillas de Freno", 
                    "Revisión General / Aceite y Filtros", 
                    "ITV", 
                    "Otros"
                ])
                taller_nom = st.text_input("Taller / Proveedor:", placeholder="Ej: Neumáticos Cádiar / Taller Oficial")
                trabajos = st.text_input("Trabajos realizados / Piezas:", placeholder="Ej: 4 neumáticos nuevos Michelin / Pastillas delanteras")
                coste = st.number_input("Coste (€ aprox):", min_value=0.0, value=0.0, step=10.0)
                
                if st.form_submit_button("🛠️ Guardar Registro en Taller", use_container_width=True):
                    if not taller_nom.strip() or not trabajos.strip():
                        st.warning("Completa el nombre del taller y los trabajos realizados.")
                    else:
                        try:
                            conn = get_connection()
                            c = conn.cursor()
                            hoy = datetime.date.today().isoformat()
                            pref = "MANT" if "Preventivo" in t_reg else "AVR"
                            orden_id = f"{pref}-MOV-{datetime.datetime.now().strftime('%m%d%H%M%S')}"
                            op_final = op_prev if t_reg == "Mantenimiento Preventivo" else "N/A"

                            c.execute("""
                                INSERT INTO taller (orden, fecha_in, fecha_out, matricula, taller, trabajos, km, coste, factura, estado_pago, tipo_registro, tipo_operacion_preventiva)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Pendiente', 'Pendiente', %s, %s);
                            """, (orden_id, hoy, hoy, mat, taller_nom.strip(), trabajos.strip(), v["km"], coste, t_reg, op_final))
                            
                            conn.commit()
                            conn.close()
                            st.success("¡Mantenimiento guardado e incorporado al historial!")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Error al registrar taller: {ex}")

        # 3. PESTAÑA: REPORTAR AVERÍA EN RUTA
        with tab_av:
            with st.form(f"form_av_{mat}"):
                urg = st.selectbox("Urgencia:", ["Baja", "Media", "Alta", "Urgente"], index=1)
                desc = st.text_area("Descripción detallada de la avería o anomalía:")
                
                if st.form_submit_button("⚠️ Enviar Aviso Urgente", use_container_width=True):
                    if not desc.strip():
                        st.warning("Escribe una descripción del problema antes de enviar.")
                    else:
                        try:
                            conn = get_connection()
                            c = conn.cursor()
                            inc_id = f"INC-MOV-{datetime.datetime.now().strftime('%m%d%H%M%S')}"
                            ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                            conductor_reporta = v["conductor"] if v["conductor"] else "Conductor en Ruta"

                            c.execute("""
                                INSERT INTO incidencias (id, fecha, matricula, conductor, tipo, descripcion, urgencia, estado)
                                VALUES (%s, %s, %s, %s, 'Avería en Ruta', %s, %s, 'Pendiente');
                            """, (inc_id, ahora, mat, conductor_reporta, desc.strip(), urg))
                            
                            conn.commit()
                            conn.close()
                            st.success("¡Avería enviada! Ya está registrada y visible para la oficina.")
                        except Exception as ex:
                            st.error(f"Error al enviar avería: {ex}")
