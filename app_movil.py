"""
App Web Móvil para Conductores - Control de Flota (v2.9 Adaptada)
- PIN de acceso protegido y gestionado vía Streamlit Secrets
- Credenciales de base de datos cifradas en Secrets
- Incluye visualización de Nº de Bastidor y optimización para Preventivos (Neumáticos/Frenos)
- Sincronización en tiempo real con Supabase
"""

import streamlit as st
import psycopg2
import datetime

# --- CONFIGURACIÓN DE PÁGINA MÓVIL ---
st.set_page_config(
    page_title="Flota - Móvil v2.9",
    page_icon="🚛",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CONTROL DE ACCESO (PIN LEÍDO DESDE SECRETS CIFRADOS) ---
# Si no está configurado en Secrets, por defecto pedirá '0000'
PIN_ACCESO_CORRECTO = st.secrets.get("PIN_ACCESO", "0000") if hasattr(st, "secrets") else "0000"

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown("<br>", unsafe_allow_html=True)
    st.title("🚛 Control de Flota")
    st.caption("Acceso restringido a personal autorizado (v2.9)")
    
    with st.form("form_login_seguro"):
        pin_ingresado = st.text_input("Introduce el PIN de acceso:", type="password", max_chars=8)
        btn_entrar = st.form_submit_button("Entrar al Sistema", type="primary", use_container_width=True)
        
        if btn_entrar:
            if pin_ingresado == str(PIN_ACCESO_CORRECTO):
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("⚠️ PIN incorrecto. Acceso denegado.")
    st.stop()

# --- CONEXIÓN A SUPABASE (SECRETS EN NUBE / PLANTILLA COMODÍN) ---
DEFAULT_DB_URL = "postgresql://postgres.tu_usuario:TU_PASSWORD_AQUI@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"

def get_connection():
    try:
        if hasattr(st, "secrets") and "DATABASE_URL" in st.secrets:
            return psycopg2.connect(st.secrets["DATABASE_URL"])
    except Exception:
        pass
    return psycopg2.connect(DEFAULT_DB_URL)

def iso_a_ddmmyyyy(fecha_iso):
    """Convierte AAAA-MM-DD a DD-MM-AAAA"""
    if not fecha_iso or fecha_iso in ["En curso", "Pendiente", "-", "YYYY-MM-DD"]:
        return fecha_iso
    try:
        dt = datetime.datetime.strptime(fecha_iso.strip(), "%Y-%m-%d")
        return dt.strftime("%d-%m-%Y")
    except Exception:
        return fecha_iso

# --- FUNCIONES DE BASE DE DATOS PROTEGIDAS (ACTUALIZADAS CON BASTIDOR Y PREVENTIVOS) ---
def cargar_vehiculos():
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT matricula, tipo, conductor, km, itv, seguro, aseguradora, prox_mant_km, prox_mant_fecha, intervalo_km, estado, bastidor FROM vehiculos ORDER BY matricula ASC;")
        rows = c.fetchall()
        vehiculos = []
        for r in rows:
            vehiculos.append({
                "matricula": r[0], "tipo": r[1], "conductor": r[2], "km": r[3],
                "itv": r[4], "seguro": r[5], "aseguradora": r[6], "prox_mant_km": r[7], 
                "prox_mant_fecha": r[8], "intervalo_km": r[9], "estado": r[10], "bastidor": r[11] if r[11] else "-"
            })
        return vehiculos
    except Exception as e:
        st.error(f"Error de conexión con la nube: {e}")
        return []
    finally:
        if conn:
            conn.close()

def cargar_historial_taller_vehiculo(matricula):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT orden, fecha_in, fecha_out, taller, trabajos, km, coste, factura, tipo_registro, tipo_operacion_preventiva FROM taller WHERE matricula = %s ORDER BY orden DESC;", (matricula,))
        rows = c.fetchall()
        registros = []
        for r in rows:
            registros.append({
                "orden": r[0], "fecha_in": r[1], "fecha_out": r[2], "taller": r[3],
                "trabajos": r[4], "km": r[5], "coste": r[6], "factura": r[7],
                "tipo_registro": r[8], "tipo_operacion_preventiva": r[9]
            })
        return registros
    except Exception:
        return []
    finally:
        if conn:
            conn.close()

def actualizar_vehiculo_movil(matricula, nuevos_km, nuevo_estado):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE vehiculos SET km = %s, estado = %s WHERE matricula = %s;", (nuevos_km, nuevo_estado, matricula))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error al actualizar: {e}")
        return False
    finally:
        if conn:
            conn.close()

def registrar_taller_movil(orden, fecha_in, fecha_out, matricula, taller, trabajos, km, coste, factura, tipo_registro, tipo_operacion_preventiva):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO taller (orden, fecha_in, fecha_out, matricula, taller, trabajos, km, coste, factura, tipo_registro, tipo_operacion_preventiva)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, (orden, fecha_in, fecha_out, matricula, taller, trabajos, km, coste, factura, tipo_registro, tipo_operacion_preventiva))
        
        nuevo_estado = "En Taller" if fecha_out in ["En curso", "", "Pendiente"] else "Operativo"
        c.execute("UPDATE vehiculos SET km = %s, estado = %s WHERE matricula = %s;", (km, nuevo_estado, matricula))
        
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error al registrar en taller: {e}")
        return False
    finally:
        if conn:
            conn.close()

def registrar_incidencia_movil(matricula, conductor, tipo, descripcion, urgencia):
    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        inc_id = f"INC-MOV-{datetime.datetime.now().strftime('%m%d%H%M')}"
        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        c.execute("""
            INSERT INTO incidencias (id, fecha, matricula, conductor, tipo, descripcion, urgencia, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'Pendiente');
        """, (inc_id, fecha_actual, matricula, conductor, tipo, descripcion, urgencia))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error al registrar incidencia: {e}")
        return False
    finally:
        if conn:
            conn.close()

# --- ENCABEZADO E IDENTIFICACIÓN DE VERSIÓN ---
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.title("Control de Flota")
with col_head2:
    st.markdown("<div style='text-align: right; padding-top: 15px;'><span style='background-color: #0284C7; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px;'>v2.9</span></div>", unsafe_allow_html=True)

st.caption("Panel del Conductor (Acceso Seguro 4G/5G)")

vehiculos = cargar_vehiculos()

if not vehiculos:
    st.warning("Conectando con la base de datos o sin vehículos registrados...")
    if st.button("🔄 Reintentar Conexión"):
        st.rerun()
    st.stop()

# Selector de Vehículo
lista_matriculas = [v["matricula"] for v in vehiculos]
matricula_seleccionada = st.selectbox("Selecciona tu Vehículo:", lista_matriculas)
veh_actual = next((v for v in vehiculos if v["matricula"] == matricula_seleccionada), None)

if veh_actual:
    st.markdown("---")
    st.subheader(f"Vehículo: {veh_actual['matricula']}")
    st.text(f"Modelo: {veh_actual['tipo']} | Conductor: {veh_actual['conductor']}")
    st.text(f"Nº Bastidor / Chasis: {veh_actual['bastidor']}")
    
    km_actuales = veh_actual["km"]
    prox_rev_km = veh_actual["prox_mant_km"]
    km_faltantes = prox_rev_km - km_actuales
    
    # Estado Operativo
    if veh_actual["estado"] == "En Taller":
        st.warning("🛠️ Este vehículo se encuentra actualmente **En Taller**.")
    elif veh_actual["estado"] in ["Parado Averiado", "Averiado"]:
        st.error("🔴 Vehículo marcado como **Parado / Averiado**.")
    else:
        st.success("🟢 Vehículo Operativo.")

    # Fechas y Revisiones Clave
    with st.container():
        st.markdown("#### 📅 Fechas y Revisiones Clave")
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Próxima ITV", value=iso_a_ddmmyyyy(veh_actual["itv"]))
        with col2:
            st.metric(label="Faltan para Rev. Km", value=f"{km_faltantes:,} km", delta=f"Obj: {prox_rev_km:,} km")
            
        st.caption(f"• Fecha Prevista Revisión: **{iso_a_ddmmyyyy(veh_actual['prox_mant_fecha'])}** | Intervalo: cada **{veh_actual['intervalo_km']:,} km**")

    tab1, tab2, tab3 = st.tabs(["📝 Actualizar Km", "🛠️ Gestionar Taller", "⚠️ Reportar Avería"])

    # --- PESTAÑA 1: ACTUALIZAR KM ---
    with tab1:
        st.markdown("#### Actualizar Kilometraje y Estado")
        st.info(f"Último kilometraje registrado: **{km_actuales:,} km**")
        
        with st.form("form_km_movil"):
            nuevo_km = st.number_input("Nuevos Kilómetros Actuales:", min_value=0, value=int(km_actuales), step=100)
            estados_posibles = ["Operativo", "En Taller", "Parado Averiado"]
            idx_estado = estados_posibles.index(veh_actual["estado"]) if veh_actual["estado"] in estados_posibles else 0
            nuevo_estado = st.selectbox("Estado del Vehículo:", estados_posibles, index=idx_estado)

            btn_guardar_km = st.form_submit_button("💾 Guardar Cambios en Ruta", type="primary", use_container_width=True)
            
            if btn_guardar_km:
                if nuevo_km < km_actuales:
                    st.error(f"⚠️ Error: {nuevo_km:,} km es inferior al último registro ({km_actuales:,} km).")
                else:
                    if actualizar_vehiculo_movil(matricula_seleccionada, nuevo_km, nuevo_estado):
                        st.success("¡Datos guardados con éxito en la nube!")
                        st.rerun()

    # --- PESTAÑA 2: GESTIONAR TALLER (CON SELECTOR DE NEUMÁTICOS Y FRENOS) ---
    with tab2:
        st.markdown("#### Registro de Mantenimiento / Taller")
        with st.form("form_taller_movil"):
            tipo_registro = st.selectbox("Tipo de Intervención:", ["Mantenimiento Preventivo", "Avería / Reparación (Correctivo)"])
            
            tipo_operacion_preventiva = "N/A"
            if tipo_registro == "Mantenimiento Preventivo":
                tipo_operacion_preventiva = st.selectbox("Operación Preventiva Específica:", [
                    "Revisión General / Aceite", 
                    "Cambio de Neumáticos", 
                    "Sustitución de Pastillas de Freno", 
                    "ITV", 
                    "Otros"
                ])

            t_taller = st.text_input("Nombre del Taller / Proveedor:")
            t_trabajos = st.text_area("Trabajos Realizados / Piezas sustituidas:")
            
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                t_fech_in = st.date_input("Fecha Entrada:", value=datetime.date.today())
            with col_f2:
                t_estado_rep = st.selectbox("Estado Reparación:", ["Finalizado", "En curso"])
                
            t_fech_out = datetime.date.today().strftime("%Y-%m-%d") if t_estado_rep == "Finalizado" else "En curso"
            
            col_n1, col_n2, col_n3 = st.columns(3)
            with col_n1:
                t_km = st.number_input("Km en Taller:", min_value=0, value=int(km_actuales))
            with col_n2:
                t_coste = st.number_input("Coste (€):", min_value=0.0, value=0.0, step=10.0)
            with col_n3:
                t_factura = st.text_input("Nº Factura:", value="Pendiente")

            btn_guardar_taller = st.form_submit_button("🛠️ Guardar Entrada de Taller", type="primary", use_container_width=True)
            
            if btn_guardar_taller:
                if not t_trabajos.strip() or not t_taller.strip():
                    st.error("Por favor, rellena el taller y la descripción de los trabajos.")
                elif t_km < km_actuales:
                    st.error(f"⚠️ Los kilómetros de taller ({t_km:,}) no pueden ser menores al kilometraje actual ({km_actuales:,}).")
                else:
                    pref = "MANT" if "Preventivo" in tipo_registro else "AVR"
                    orden_id = f"{pref}-MOV-{datetime.datetime.now().strftime('%m%d%H%M')}"
                    if registrar_taller_movil(orden_id, t_fech_in.strftime("%Y-%m-%d"), t_fech_out, matricula_seleccionada, t_taller, t_trabajos, t_km, t_coste, t_factura, tipo_registro, tipo_operacion_preventiva):
                        st.success("¡Reparación sincronizada con la oficina!")
                        st.rerun()

        st.markdown("---")
        st.markdown("#### Historial Reciente de Intervenciones")
        historial = cargar_historial_taller_vehiculo(matricula_seleccionada)
        if not historial:
            st.info("No hay registros previos en taller para este vehículo.")
        else:
            for h in historial:
                tipo_lbl = f"[{h['tipo_registro']}]"
                op_lbl = f" - {h['tipo_operacion_preventiva']}" if h['tipo_registro'] == "Mantenimiento Preventivo" else ""
                with st.expander(f"Orden: {h['orden']} ({iso_a_ddmmyyyy(h['fecha_in'])}) {tipo_lbl}{op_lbl}"):
                    st.markdown(f"**Trabajos:**\n{h['trabajos']}")
                    st.text(f"Taller: {h['taller']} | Km: {h['km']:,} | Coste: {h['coste']:.2f} € | Factura: {h['factura']}")
                    st.text(f"Salida: {iso_a_ddmmyyyy(h['fecha_out'])}")

    # --- PESTAÑA 3: REPORTAR AVERÍA ---
    with tab3:
        st.markdown("#### Notificar Avería o Incidencia")
        with st.form("form_incidencia_movil"):
            conductor_nombre = st.text_input("Tu Nombre / Conductor:", value=veh_actual["conductor"])
            tipo_fallo = st.selectbox("Tipo de Avería / Incidencia:", ["Motor / Mecánica", "Neumáticos / Frenos", "Luces / Eléctrico", "Otros"])
            urgencia = st.selectbox("Urgencia:", ["Baja", "Media", "Alta"])
            descripcion = st.text_area("Descripción detallada del problema:")

            btn_enviar_inc = st.form_submit_button("🚨 Enviar Aviso a la Oficina", type="primary", use_container_width=True)
            
            if btn_enviar_inc:
                if descripcion.strip() == "":
                    st.error("Por favor, introduce una descripción de la avería.")
                else:
                    if registrar_incidencia_movil(matricula_seleccionada, conductor_nombre, tipo_fallo, descripcion, urgencia):
                        st.success("¡Aviso enviado a la oficina con éxito!")
                        st.rerun()
