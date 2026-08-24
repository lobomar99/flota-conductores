"""
App Web Móvil de Flota - Diseño Fiel de Tarjetas Nativas
- Aspecto visual tipo tarjeta nativa con sombras y contrastes marcados
- Seguridad por PIN y secretos de Supabase protegidos
- Métricas claras de Bastidor, ITV, Próx. Revisión, Ruedas y Frenos
"""

import streamlit as st
import psycopg2
import datetime
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Flota Móvil - Panel Conductor",
    page_icon="🚛",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS CSS PARA DISEÑO PROFESIONAL DE TARJETAS ---
st.markdown("""
    <style>
    /* Fondo y tipografía general */
    .stApp {
        background-color: #F8FAFC;
    }
    
    /* Contenedor tipo Tarjeta Móvil */
    .custom-card {
        background-color: #FFFFFF;
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 20px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
    }
    
    /* Cabecera de la Tarjeta */
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
    
    /* Datos principales */
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

    /* Caja de elementos críticos (Ruedas / Frenos / ITV) */
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

    /* Botones de acción */
    div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# --- OBTENCIÓN SEGURA DE SECRETOS ---
def get_secret(key, default=""):
    if hasattr(st, "secrets") and key in st.secrets:
        return st.secrets[key]
    return os.environ.get(key, default)

PIN_ACCESO_CORRECTO = str(get_secret("PIN_ACCESO", "1234"))
DATABASE_URL = get_secret("DATABASE_URL", "")

# --- CONTROL DE ACCESO POR PIN ---
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

# --- CONEXIÓN A SUPABASE ---
def get_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL no configurada en los secretos.")
    return psycopg2.connect(DATABASE_URL)

def iso_a_ddmmyyyy(fecha_iso):
    if not fecha_iso or str(fecha_iso).strip() in ["En curso", "Pendiente", "-", "YYYY-MM-DD", "None"]:
        return "-"
    try:
        dt = datetime.datetime.strptime(str(fecha_iso).strip(), "%Y-%m-%d")
        return dt.strftime("%d-%m-%Y")
    except Exception:
        return str(fecha_iso)

# --- CARGA DE DATOS ---
def cargar_datos():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()

        # Vehículos
        c.execute("""
            SELECT matricula, tipo, conductor, km, itv, seguro, aseguradora, 
                   prox_mant_km, prox_mant_fecha, intervalo_km, estado, bastidor 
            FROM vehiculos ORDER BY matricula ASC;
        """)
        vehiculos = [{
            "matricula": r[0], "tipo": r[1], "conductor": r[2], "km": r[3],
            "itv": r[4], "seguro": r[5], "aseguradora": r[6], "prox_mant_km": r[7] or 0, 
            "prox_mant_fecha": r[8], "intervalo_km": r[9] or 0, "estado": r[10] or "Operativo", 
            "bastidor": r[11] if r[11] else "-"
        } for r in c.fetchall()]

        # Taller (ruedas y frenos)
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

# --- CABECERA SUPERIOR ---
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
    st.info("No hay vehículos cargados o no se pudo conectar.")
    st.stop()

# --- RENDERIZADO DE TARJETAS ESTILIZADAS ---
for v in vehiculos:
    mat = v["matricula"]
    estado = v["estado"]
    color_bg = "#10B981" if estado == "Operativo" else ("#F59E0B" if estado == "En Taller" else "#EF4444")

    # Extraer últimos mantenimientos de ruedas y frenos
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

    # Tarjeta HTML Visual
    km_faltantes = v["prox_mant_km"] - v["km"]
    st.markdown(f"""
        <div class="custom-card">
            <div class="card-header">
                <span class="matricula-title">🚗 {mat}</span>
                <span class="badge-estado" style="background-color: {color_bg};">{estado}</span>
            </div>
            <div class="card-row"><strong>Modelo / Tipo:</strong> {v['tipo']}</div>
            <div class="card-row"><strong>Conductor:</strong> {v['conductor'] or 'Sin asignar'}</div>
            <div class="card-row"><strong>Nº Bastidor:</strong> <span class="highlight-bastidor">{v['bastidor']}</span></div>
            <div class="critical-box">
                <div class="critical-item">📍 <strong>Kilómetros:</strong> {v['km']:,} km</div>
                <div class="critical-item">📅 <strong>Próx. ITV:</strong> {iso_a_ddmmyyyy(v['itv'])}</div>
                <div class="critical-item">🔧 <strong>Próx. Revisión:</strong> {km_faltantes:,} km faltan ({iso_a_ddmmyyyy(v['prox_mant_fecha'])})</div>
                <div class="critical-item">🛞 <strong>Últ. Cambio Ruedas:</strong> <span class="critical-value">{ult_ruedas}</span></div>
                <div class="critical-item">🛑 <strong>Últ. Sust. Frenos:</strong> <span class="critical-value">{ult_frenos}</span></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Formulario desplegable para actualizar sin romper la estética
    with st.expander(f"📝 Actualizar Km o Reportar Avería ({mat})"):
        tab1, tab2 = st.tabs(["Actualizar Km", "Reportar Avería"])
        
        with tab1:
            with st.form(f"f_km_{mat}"):
                nuevo_km = st.number_input("Kilómetros actuales:", min_value=int(v["km"]), value=int(v["km"]), step=100)
                nuevo_est = st.selectbox("Estado operativo:", ["Operativo", "En Taller", "Parado Averiado"], index=["Operativo", "En Taller", "Parado Averiado"].index(estado) if estado in ["Operativo", "En Taller", "Parado Averiado"] else 0)
                if st.form_submit_button("💾 Guardar Kilometraje", use_container_width=True):
                    try:
                        conn = get_connection()
                        c = conn.cursor()
                        c.execute("UPDATE vehiculos SET km = %s, estado = %s WHERE matricula = %s;", (nuevo_km, nuevo_est, mat))
                        conn.commit()
                        conn.close()
                        st.success("¡Kilómetros actualizados!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Error: {ex}")
                        
        with tab2:
            with st.form(f"f_av_{mat}"):
                urg = st.selectbox("Urgencia:", ["Baja", "Media", "Alta", "Urgente"], index=1)
                desc = st.text_area("Descripción de la avería:")
                if st.form_submit_button("⚠️ Enviar Aviso Urgente", use_container_width=True):
                    if not desc.strip():
                        st.warning("Indica una descripción.")
                    else:
                        try:
                            conn = get_connection()
                            c = conn.cursor()
                            inc_id = f"INC-MOV-{datetime.datetime.now().strftime('%m%d%H%M%S')}"
                            ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                            c.execute("""
                                INSERT INTO incidencias (id, fecha, matricula, conductor, tipo, descripcion, urgencia, estado)
                                VALUES (%s, %s, %s, %s, 'Avería en Ruta', %s, %s, 'Pendiente');
                            """, (inc_id, ahora, mat, v['conductor'] or "Conductor", desc.strip(), urg))
                            conn.commit()
                            conn.close()
                            st.success("¡Avería enviada a la oficina!")
                        except Exception as ex:
                            st.error(f"Error: {ex}")
