import streamlit as st
import pandas as pd
from datetime import datetime
import google.generativeai as genai
from fpdf import FPDF
import json
import re

# --- CONFIGURACIÓN E IDENTIDAD ---
FIRMA = "ALLH-ORH:2026"
LEMA = '"No solo es querer salvar, sino saber salvar" Organización Rescate Humboldt.'

# --- PROMPT DEL SISTEMA (CON CAPACIDAD DE AUTO-LLENADO) ---
SYSTEM_PROMPT = f"""
ACTÚA COMO: Asesor Táctico de Medicina Prehospitalaria y Operaciones SAR para la Organización Rescate Humboldt (ORH).
Firma: {FIRMA}.
INSTRUCCIONES:
1. Usa protocolos PHTLS 10, TCCC, ATLS.
2. Si el usuario describe una situación, extrae información para el informe.
3. IMPORTANTE: Cada vez que sugieras una acción o identifiques un riesgo, añade al FINAL de tu respuesta un bloque JSON exactamente así:
   UPDATE_DATA: {{"march": {{"M": "acción", "A": "acción", "R": "acción", "C": "acción", "H": "acción"}}, "clima": "texto", "riesgo": "texto"}}
   Solo llena los campos que identifiques en la conversación.
"""

# --- INICIALIZACIÓN DE IA ---
model = None
if "GENAI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GENAI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=SYSTEM_PROMPT)
    except Exception as e:
        st.error(f"Error crítico de librería: {e}")

# --- ESTADO DE LA SESIÓN (SINCRONIZACIÓN) ---
if 'march_data' not in st.session_state:
    st.session_state.march_data = {"M": "", "A": "", "R": "", "C": "", "H": ""}
if 'entorno_data' not in st.session_state:
    st.session_state.entorno_data = {"clima": "", "riesgo": ""}
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# --- FUNCIÓN PDF OFICIAL ---
def generate_official_pdf(report_content):
    pdf = FPDF()
    pdf.add_page()
    # Encabezado Oficial
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "ORGANIZACIÓN RESCATE HUMBOLDT", ln=True, align='C')
    pdf.set_font("Arial", '', 8)
    pdf.cell(0, 5, "DIVISION DE ATENCION MEDICA DE EMERGENCIA (AME)", ln=True, align='C')
    pdf.ln(10)
    # Contenido
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 6, report_content)
    pdf.ln(20)
    # Firma
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 10, f"Propiedad de: {FIRMA} - {LEMA}", align='C')
    return pdf.output()

# --- INTERFAZ ---
st.set_page_config(page_title="Asesor Táctico ORH", layout="wide")

if not st.session_state.authenticated:
    try:
        st.image("LOGO_ORH57.JPG", width=150)
    except:
        st.warning("Archivo LOGO_ORH57.JPG no encontrado en el repositorio.")
    
    st.title("Acceso Operativo AME")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("INGRESAR"):
        if u == "ORH2026" and p == "ORH2026":
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- CUERPO DE LA APP ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Registro", "🌍 Entorno", "🩺 MARCH", "💬 Chat IA", "📄 Informe"])

with tab1:
    st.subheader("1. Datos Iniciales")
    col1, col2 = st.columns(2)
    op_name = col1.text_input("Operador APH")
    tipo_inc = col1.selectbox("Incidente", ["Terrestre", "Aéreo", "Náutico"])
    ubicacion = col2.text_input("Ubicación")
    paciente = st.text_area("Datos del Paciente")
    foto = st.camera_input("Evidencia Fotográfica")

with tab2:
    st.subheader("2. Análisis de Entorno")
    clima = st.text_input("Climatología", value=st.session_state.entorno_data["clima"])
    riesgos = st.text_area("Riesgos y Recursos", value=st.session_state.entorno_data["riesgo"])

with tab3:
    st.subheader("3. Protocolo Clínico MARCH")
    # Tabla editable que se sincroniza con la IA
    m_val = st.text_input("M (Hemorragia)", value=st.session_state.march_data["M"])
    a_val = st.text_input("A (Vía Aérea)", value=st.session_state.march_data["A"])
    r_val = st.text_input("R (Respiración)", value=st.session_state.march_data["R"])
    c_val = st.text_input("C (Circulación)", value=st.session_state.march_data["C"])
    h_val = st.text_input("H (Hipotermia/Heridas)", value=st.session_state.march_data["H"])

with tab4:
    st.subheader("💬 Consultor Táctico IA")
    if 'messages' not in st.session_state: st.session_state.messages = []
    
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Describa la escena o pida ayuda técnica..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        with st.chat_message("assistant"):
            if model:
                response = model.start_chat().send_message(prompt)
                full_text = response.text
                
                # --- LÓGICA DE AUTO-LLENADO ---
                json_match = re.search(r"UPDATE_DATA:\s*(\{.*\})", full_text, re.DOTALL)
                if json_match:
                    try:
                        new_data = json.loads(json_match.group(1))
                        if "march" in new_data:
                            for key in st.session_state.march_data:
                                if new_data["march"].get(key):
                                    st.session_state.march_data[key] = new_data["march"][key]
                        if "clima" in new_data: st.session_state.entorno_data["clima"] = new_data["clima"]
                        if "riesgo" in new_data: st.session_state.entorno_data["riesgo"] = new_data["riesgo"]
                        st.info("💡 La IA ha actualizado los campos del protocolo automáticamente.")
                    except: pass
                
                clean_response = re.sub(r"UPDATE_DATA:.*", "", full_text, flags=re.DOTALL)
                st.markdown(clean_response)
                st.session_state.messages.append({"role": "assistant", "content": clean_response})
            else:
                st.error("Error: Configure la API Key en los Secrets de Streamlit.")

with tab5:
    st.subheader("5. Informe Final Oficial")
    c_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    reporte_text = f"""
    FECHA/HORA: {c_time}
    OPERADOR: {op_name}
    UBICACIÓN: {ubicacion} | TIPO: {tipo_inc}
    
    PACIENTE: {paciente}
    
    PROTOCOLO MARCH:
    - M: {m_val}
    - A: {a_val}
    - R: {r_val}
    - C: {c_val}
    - H: {h_val}
    
    ENTORNO: {clima} | RIESGOS: {riesgos}
    
    -------------------------------------------
    Firma Autorizada: {FIRMA}
    {LEMA}
    """
    st.text_area("Vista Previa:", reporte_text, height=250)
    
    if st.button("📥 GENERAR PDF OFICIAL"):
        pdf_out = generate_official_pdf(reporte_text)
        st.download_button("Descargar Archivo PDF", data=pdf_out, file_name=f"ORH_AME_{c_time}.pdf")

st.sidebar.image("LOGO_ORH57.JPG")
st.sidebar.write(f"SISTEMA ACTIVO: {FIRMA}")
