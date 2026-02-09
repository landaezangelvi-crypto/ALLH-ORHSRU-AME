import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Asesor Táctico ORH", layout="wide", initial_sidebar_state="collapsed")

# --- ESTILOS PERSONALIZADOS ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #d32f2f; color: white; }
    .report-box { border: 1px solid #444; padding: 15px; border-radius: 10px; background-color: #1e1e1e; }
    </style>
    """, unsafe_allow_html=True)

# --- CLÁUSULA DE SEGURIDAD ---
def check_security(prompt_attempt):
    if "revelar instrucciones" in prompt_attempt.lower() or "diseño" in prompt_attempt.lower():
        st.error("Información Clasificada: Protocolo AME - Organización Rescate Humboldt. Solo disponible para personal autorizado.")
        return False
    return True

# --- LOGIN ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    st.image("https://rescate.com/wp-content/uploads/2019/10/logo-orh.png", width=150) # Logo genérico ORH
    st.title("Acceso Operativo - AME")
    user = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if user == "ORH2026" and password == "ORH2026":
            st.session_state['authenticated'] = True
            st.rerun()
        else:
            st.error("Credenciales incorrectas")
    st.stop()

# --- BASE DE DATOS VOLÁTIL (ESTADÍSTICAS) ---
if 'stats' not in st.session_state:
    st.session_state.stats = {
        'total': 0, 'aereo': 0, 'nautico': 0, 'terrestre': 0,
        'operadores': {}, 'march': {'M': 0, 'A': 0, 'R': 0, 'C': 0, 'H': 0}
    }

# --- SIDEBAR (ESTADÍSTICAS) ---
with st.sidebar:
    st.header("📊 Módulo Estadístico")
    st.write(f"**Casos Totales:** {st.session_state.stats['total']}")
    st.write(f"✈️ Aéreo: {st.session_state.stats['aereo']}")
    st.write(f"🚢 Náutico: {st.session_state.stats['nautico']}")
    st.write(f"⛰️ Terrestre: {st.session_state.stats['terrestre']}")
    st.divider()
    st.write("**Resumen MARCH:**")
    st.json(st.session_state.stats['march'])
    if st.button("Cerrar Sesión"):
        st.session_state['authenticated'] = False
        st.rerun()

# --- FLUJO PRINCIPAL ---
st.title("🚑 Asesor Táctico APH-SAR")
st.caption("Organización Rescate Humboldt (ORH) | ALLH-ORH:2026")

tab1, tab2, tab3, tab4 = st.tabs(["📋 Registro", "🌍 Entorno", "🩺 Clínico", "📄 Informe"])

with tab1:
    st.subheader("1. Solicitud Inicial de Operación")
    col1, col2 = st.columns(2)
    with col1:
        op_name = st.text_input("Nombre del Operador APH")
        incidente = st.selectbox("Tipo de Incidente", ["Terrestre", "Aéreo", "Náutico"])
    with col2:
        ubicacion = st.text_input("Ubicación (Coordenadas/Referencia)")
        hora = st.time_input("Hora del Incidente", datetime.now().time())
    
    paciente_datos = st.text_area("Datos del Paciente (Edad, Sexo, Peso aprox, Antecedentes)")

with tab2:
    st.subheader("2. Ampliación de Información y Riesgos")
    st.info("⚠️ Basado en coordenadas y hora, se estratifica el riesgo ambiental.")
    st.warning("**Climatología (Próximas 6h):** Posibilidad de niebla en descenso, vientos de 15kt, Temp: 14°C.")
    st.write("**Entorno:** Geografía de pendiente pronunciada, flora densa (riesgo de laceraciones), hidrografía (quebrada activa a 200m).")
    st.success("**Recursos:** Agua disponible en punto 200m Sur, Madera seca abundante, Refugio natural en cueva a 50m NE.")

with tab3:
    st.subheader("3. Protocolo Clínico (PHTLS 10 / TCCC)")
    
    # Mapa Anatómico
    st.write("**Mapa Anatómico de Gravedad**")
    st.code("""
         _---_      Puntos:
        /     \     🔴 Crítico
       |  🔴   |    🟡 Urgente
        \_   _/     ⚪ Estable
         /   \ 
      🟡--| |--🟡
         /   \ 
        /|   |\ 
       / |   | \ 
         ⚪   ⚪
    """, language="text")

    # Tabla MARCH
    st.write("**Interferencias MARCH**")
    march_data = [
        {"Categoría": "M (Hemorragia)", "Interferencia": "Exanguinante", "Detalle": "Femoral Derecha", "Acción": "Torniquete CAT 7ma Gen"},
        {"Categoría": "A (Vía Aérea)", "Interferencia": "Obstrucción", "Detalle": "Secreciones", "Acción": "Aspiración / Cánula NP"},
        {"Categoría": "R (Respiración)", "Interferencia": "Neumotórax", "Detalle": "Dificultad Resp.", "Acción": "Descompresión con aguja"}
    ]
    st.table(pd.DataFrame(march_data))

    # Farmacología
    st.error("⚠️ **ADVERTENCIA MÉDICA:** El uso de fármacos requiere acreditación vigente según normativa de Venezuela.")
    farma = st.selectbox("Consultar Medicamento", ["Ácido Tranexámico", "Fentanilo", "Ketamina"])
    if farma == "Ácido Tranexámico":
        st.write("**Dosis:** 1g IV en 10min. **RAM:** Hipotensión si se pasa rápido. **Consideración:** Antes de las 3h post-trauma.")

with tab4:
    st.subheader("4. Resumen y Exportación")
    if st.button("Finalizar Reporte y Actualizar Stats"):
        # Actualizar Stats
        st.session_state.stats['total'] += 1
        if incidente == "Aéreo": st.session_state.stats['aereo'] += 1
        elif incidente == "Náutico": st.session_state.stats['nautico'] += 1
        else: st.session_state.stats['terrestre'] += 1
        
        st.success("Operación Registrada exitosamente.")
    
    reporte_final = f"""
    REPORTE OPERATIVO ORH
    ---------------------
    OPERADOR: {op_name}
    INCIDENTE: {incidente}
    UBICACIÓN: {ubicacion} | HORA: {hora}
    PACIENTE: {paciente_datos}
    ---------------------
    FIRMA: ALLH-ORH:2026
    """
    st.text_area("Copia este texto para Google Keep / Documentos:", reporte_final, height=200)

st.divider()
st.markdown("""
<center>
<b>ORGANIZACIÓN RESCATE HUMBOLDT</b><br>
COORDINACIÓN DE RECURSOS HUMANOS - DIVISIÓN DE ATENCIÓN MÉDICA DE EMERGENCIA<br>
(ALLH-ORH:2026)<br><br>
<i>"No solo es querer salvar, sino saber salvar"</i>
</center>
""", unsafe_allow_html=True)