import streamlit as st
from google import genai
from fpdf import FPDF
import json, re, os
from datetime import datetime
from PIL import Image
import requests

# --- 1. CONFIGURACIÓN E IDENTIDAD ---
st.set_page_config(page_title="ORH - AME Táctico 9.0", layout="wide", page_icon="🚑")

FIRMA = "ALLH-ORH:2026"
LEMA = '"No solo es querer salvar, sino saber salvar" Organización Rescate Humboldt.'
COPYRIGHT_FULL = "ORGANIZACIÓN RESCATE HUMBOLDT - COORDINACIÓN DE RECURSOS HUMANOS - DIVISIÓN DE ATENCIÓN MÉDICA DE EMERGENCIA - (ALLH-ORH:2026)"
LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/82/Gnome-medical-emergency.svg/1024px-Gnome-medical-emergency.svg.png"

# --- 2. CONTROL DE ACCESO ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🚑 Sistema Táctico AME - ORH")
    c1, c2 = st.columns([1, 2])
    with c1: st.image(LOGO_URL, width=100)
    with c2:
        with st.form("login"):
            st.markdown("### Credenciales Operativas")
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("ACCEDER AL SISTEMA"):
                if u == "ORH2026" and p == "ORH2026":
                    st.session_state.auth = True
                    st.rerun()
                else: st.error("Acceso no autorizado.")
    st.stop()

# --- 3. CONEXIÓN NEURONAL ---
client = None
if "GENAI_API_KEY" in st.secrets:
    try:
        client = genai.Client(api_key=st.secrets["GENAI_API_KEY"])
        MODELO = "gemini-2.5-flash"
    except Exception as e: st.error(f"Error IA: {e}")

# --- 4. PROMPT DE PRECISIÓN OPERATIVA (ENTORNO Y LEGAL) ---
SYSTEM_PROMPT = f"""
ACTÚA COMO: Oficial de Operaciones SAR y Médico Táctico de la ORH ({FIRMA}).

INSTRUCCIONES DE RESPUESTA:
1. PRECISIÓN SIN REDUNDANCIA: No repitas procedimientos que un operador calificado ya conoce, a menos que se te solicite o haya dudas evidentes.
2. ANÁLISIS DE ENTORNO OBLIGATORIO: Si se menciona una ubicación o coordenadas, debes generar una sección de "INTELIGENCIA DE TERRENO" detallando:
   - Geografía y Riesgos: Pendientes, estabilidad de suelo.
   - Hidrología y Clima: Pronóstico probable, riesgos de crecidas.
   - Fauna y Flora: Especies venenosas, vegetación hostil.
   - Recursos Naturales: Fuentes de agua, cuevas o leña para pernocta.
3. PROTOCOLOS: PHTLS 2025-2026, CTTT, BCLS, ATLS.
4. MARCO LEGAL VEN: Código Penal, Ley Ejercicio Medicina, Deontología de Enfermería y Estatutos ORH.
5. FASES: Amenaza Directa / Campo / TACEVAC.

CIERRE: {LEMA}

SALIDA JSON (INVISIBLE):
UPDATE_DATA: {{
  "info": {{ "operador": "...", "paciente": "...", "ubicacion": "...", "tipo_incidente": "...", "hora": "..." }},
  "march": {{ "M": "...", "A": "...", "R": "...", "C": "...", "H": "..." }},
  "farmaco": "..."
}}
"""

# --- 5. ESTADO DE SESIÓN ---
vars_default = {
    "operador": "", "paciente": "", "ubicacion": "", "tipo_incidente": "Terrestre", 
    "hora": datetime.now().strftime('%H:%M'), "farmaco": "", 
    "M":"", "A":"", "R":"", "C":"", "H":""
}
for k, v in vars_default.items():
    if k not in st.session_state: st.session_state[k] = v
if 'chat' not in st.session_state: st.session_state.chat = []

# --- 6. GENERADOR DE PDF ---
class ORHPDF(FPDF):
    def header(self):
        try: self.image("logo_temp.png", 10, 8, 20)
        except: pass
        self.set_font('Arial', 'B', 12)
        self.cell(0, 5, 'ORGANIZACIÓN RESCATE HUMBOLDT', 0, 1, 'C')
        self.set_font('Arial', '', 8)
        self.cell(0, 5, 'AME - OPERACIONES TÁCTICAS DE CAMPO', 0, 1, 'C')
        self.ln(10)
    def footer(self):
        self.set_y(-22)
        self.set_font('Arial', 'I', 6)
        self.multi_cell(0, 4, f"{COPYRIGHT_FULL}\n{LEMA}", 0, 'C')

# --- 7. INTERFAZ ---
logo_path = "logo_temp.png"
if not os.path.exists(logo_path):
    try:
        r = requests.get(LOGO_URL)
        with open(logo_path, 'wb') as f: f.write(r.content)
    except: pass

st.sidebar.title("ORH - CENTRO DE MANDO")
st.sidebar.image(LOGO_URL, width=80)
st.sidebar.info(f"**UNIDAD:** {FIRMA}")

tab1, tab2, tab3 = st.tabs(["💬 CONSULTOR SAR", "📋 REGISTRO", "📄 PDF"])

with tab1:
    for m in st.session_state.chat:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    
    if q := st.chat_input("Reporte: Ubicación, estado del paciente..."):
        st.session_state.chat.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        
        with st.chat_message("assistant"):
            if client:
                with st.spinner("Analizando terreno y protocolos..."):
                    res = client.models.generate_content(model=MODELO, contents=[SYSTEM_PROMPT, q])
                    full_text = res.text
                    
                    match = re.search(r"UPDATE_DATA:\s*(\{.*\})", full_text, re.DOTALL)
                    if match:
                        try:
                            js = json.loads(match.group(1).replace("'", '"'))
                            for cat in ["info", "march"]:
                                for k, v in js[cat].items():
                                    if v and v != "...": st.session_state[k] = v
                            st.toast("Datos Sincronizados")
                        except: pass

                    clean_res = re.sub(r"UPDATE_DATA:.*", "", full_text, flags=re.DOTALL)
                    st.markdown(clean_res)
                    st.session_state.chat.append({"role": "assistant", "content": clean_res})

with tab2:
    st.subheader("Datos de la Misión")
    c1, c2 = st.columns(2)
    st.session_state["operador"] = c1.text_input("Operador", st.session_state["operador"])
    st.session_state["ubicacion"] = c2.text_input("Coordenadas/Lugar", st.session_state["ubicacion"])
    
    m_cols = st.columns(5)
    keys = ["M", "A", "R", "C", "H"]
    for i, k in enumerate(keys):
        st.session_state[k] = m_cols[i].text_area(k, st.session_state[k], height=100)
    
    st.session_state["farmaco"] = st.text_area("Notas / Tratamiento / Análisis de Riesgo", st.session_state["farmaco"])

with tab3:
    st.subheader("Informe de Evacuación / TACEVAC")
    if st.button("📥 DESCARGAR INFORME OFICIAL"):
        pdf = ORHPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 8, f"REPORTE TÁCTICO - {datetime.now().strftime('%d/%m/%Y %H:%M')}", 1, 1, 'C')
        
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, "I. INTELIGENCIA Y UBICACIÓN", 0, 1)
        pdf.set_font('Arial', '', 9)
        pdf.multi_cell(0, 5, f"Operador: {st.session_state['operador']}\nUbicación: {st.session_state['ubicacion']}")
        
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, "II. EVALUACIÓN MARCH", 0, 1)
        pdf.set_font('Arial', '', 9)
        pdf.multi_cell(0, 5, f"M: {st.session_state['M']}\nA: {st.session_state['A']}\nR: {st.session_state['R']}\nC: {st.session_state['C']}\nH: {st.session_state['H']}")
        
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, "III. OBSERVACIONES OPERATIVAS Y TERAPÉUTICA", 0, 1)
        pdf.set_font('Arial', '', 9)
        pdf.multi_cell(0, 5, st.session_state['farmaco'])
        
        st.download_button("Guardar PDF", data=bytes(pdf.output()), file_name=f"ORH_{datetime.now().strftime('%H%M')}.pdf")

st.markdown(f"--- \n<center><small>{COPYRIGHT_FULL}</small></center>", unsafe_allow_html=True)
