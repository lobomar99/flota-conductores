"""
App Web Móvil para Conductores - Control de Flota (v3.0 - Diseño de Tarjetas Visuales)
- Acceso seguro mediante PIN protegido en Streamlit Secrets
- Credenciales de Supabase protegidas
- Tarjetas visuales por vehículo con alertas claras de ITV, Próx. Revisión, Ruedas y Frenos
"""

import streamlit as st
import psycopg2
import datetime

# --- CONFIGURACIÓN DE PÁGINA MÓVIL ---
st.set_page_config(
    page_title="Flota - Panel Conductor",
    page_icon="🚛",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CONTROL DE ACCESO (PIN LEÍDO DESDE SECRETS) ---
PIN_ACCESO_CORRECTO = st.secrets.get("PIN_ACCESO", "0000") if hasattr(st, "secrets") else "0000"

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown("<br>", unsafe_allow_html=True)
    st.title("🚛 Control de Flota - Conductor")
    st.caption("Introduce tu PIN para acceder al panel rápido")
    
    with st.form("form_login_seguro"):
        pin_ingresado = st.text_input("PIN de Acceso:", type="password", max_chars=8)
        btn_entrar = st.form_submit_button("Entrar", type="primary", use_container_width=True)
        
        if btn_entrar:
            if pin_ingresado == str(PIN_ACCESO_CORRECTO):
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("⚠️ PIN incorrecto.")
    st.stop()

# --- CONEXIÓN A SUPABASE ---
def get_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

def iso_a_ddmmyyyy(fecha_iso):
    if not fecha_iso or fecha_iso in ["En curso", "Pendiente", "-", "YYYY-MM-DD"]:
        return fecha_iso
    try:
        dt = datetime.datetime.strptime(fecha_iso.strip(), "%Y-%m-%d")
        return dt.strftime("%d-%m-%Y")
    except Exception:
        return fecha_iso

# --- FUNCIONES DE CARGA ---
def cargar_datos_completos():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # Vehículos
        c.execute("SELECT matricula, tipo, conductor, km, itv, seguro, aseguradora, prox_mant_km, prox_mant_fecha, intervalo_km, estado, bastidor FROM vehiculos ORDER BY matricula ASC;")
        vehiculos = [{
            "matricula": r[0], "tipo": r[1], "conductor": r[2], "km": r[3],
            "itv": r[4], "seguro": r[5], "aseguradora": r[6], "prox_mant_km": r[7], 
            "prox_mant_fecha": r[8], "intervalo_km": r[9], "estado": r[10], "bastidor": r[11] if r[11] else "-"
        } for r in c.fetchall()]

        # Taller (para extraer último cambio de ruedas y frenos)
        c.execute("SELECT orden, fecha_in, matricula, taller, trabajos, km, coste, tipo_registro, tipo_operacion_preventiva FROM taller ORDER BY orden DESC;")
        taller = [{
            "orden": r[0], "fecha_in": r[1], "matricula": r[2], "taller": r[3],
            "trabajos": r[4], "km": r[5], "coste": r[6], "tipo_registro": r[7], "tipo_operacion_preventiva": r[8]
        } for r in c.fetchall()]

        conn.close()
        return vehiculos, taller
    except Exception as e:
        st.error(f"Error de conexión con la nube: {e}")
        return [], []
    finally:
        if conn:
            conn.close()

# --- INTERFAZ PRINCIPAL MÓVIL ---
st.title("🚛 Estado de la Flota")
st.caption("Vista rápida para conductores (Ruedas, Frenos, ITV y Revisiones)")

vehiculos, taller = cargar_datos_completos()

if not vehiculos:
    st.warning("No hay vehículos disponibles o sin conexión.")
    if st.button("🔄 Recargar"):
        st.rerun()
    st.stop()

# --- RENDERIZADO EN TARJETAS VISUALES ---
for v in vehiculos:
    mat = v["matricula"]
    
    # Calcular estado visual general y colores
    estado_ico = "🟢" if v["estado"] == "Operativo" else ("🟡" if v["estado"] == "En Taller" else "🔴")
    
    # Buscar últimos mantenimientos de ruedas y frenos para este vehículo
    ult_ruedas = "Sin registro"
    ult_frenos = "Sin registro"
    for t in taller:
        if t["matricula"] == mat:
            op = t.get("tipo_operacion_preventiva", "")
            trab = t.get("trabajos", "")
            f_reg = iso_a_ddmmyyyy(t.get("fecha_in", ""))
            if ("Neumáticos" in op or "Neumáticos" in trab) and ult_ruedas == "Sin registro":
                ult_ruedas = f"{f_reg} ({t['km']:,} km)"
            if ("Freno" in op or "Pastillas" in trab) and ult_frenos == "Sin registro":
                ult_frenos = f"{f_reg} ({t['km']:,} km)"

    # Tarjeta tipo Expander muy limpia y visual
    with st.expander(f"{estado_ico} [{mat}] - {v['tipo']} ({v['km']:,} km)"):
        st.markdown(f"**Nº Bastidor / Chasis:** `{v['bastidor']}`")
        st.markdown(f"**Conductor Habitual:** {v['conductor'] or 'Sin asignar'}")
        
        st.markdown("---")
        
        # Métricas clave en columnas compactas para móvil
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Próxima ITV", iso_a_ddmmyyyy(v["itv"]))
            st.markdown(f"🛞 **Ruedas:** {ult_ruedas}")
        with col2:
            km_faltantes = v["prox_mant_km"] - v["km"]
            st.metric("Próx. Revisión", f"{km_faltantes:,} km", delta=f"Obj: {v['prox_mant_km']:,}")
            st.markdown(f"🛑 **Frenos:** {ult_frenos}")

        st.markdown("---")
        
        # Botones de acción rápida dentro de la tarjeta
        if st.button(f"📝 Actualizar Km / Estado ({mat})", key=f"btn_km_{mat}", use_container_width=True):
            st.session_state[f"edit_{mat}"] = True

        # Sección desplegable si pulsa el botón de actualizar
        if st.session_state.get(f"edit_{mat}", False):
            with st.form(f"form_upd_{mat}"):
                nuevo_km = st.number_input("Nuevos Kilómetros:", min_value=0, value=int(v["km"]), step=100)
                nuevo_est = st.selectbox("Estado Operativo:", ["Operativo", "En Taller", "Parado Averiado"], index=["Operativo", "En Taller", "Parado Averiado"].index(v["estado"]) if v["estado"] in ["Operativo", "En Taller", "Parado Averiado"] else 0)
                
                if st.form_submit_button("💾 Guardar Cambios", type="primary", use_container_width=True):
                    try:
                        conn = get_connection()
                        c = conn.cursor()
                        c.execute("UPDATE vehiculos SET km = %s, estado = %s WHERE matricula = %s;", (nuevo_km, nuevo_est, mat))
                        conn.commit()
                        conn.close()
                        st.success("¡Actualizado con éxito!")
                        st.session_state[f"edit_{mat}"] = False
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Error al guardar: {ex}")

st.markdown("---")
st.caption("Materiales de Construcción Francisco López Archilla E Hijos S.L. • Sincronizado con Supabase")
