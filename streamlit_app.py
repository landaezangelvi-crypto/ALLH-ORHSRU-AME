import streamlit as st
from google import genai
from fpdf import FPDF
import json, re, os
from datetime import datetime
from PIL import Image
import requests

# --- 1. CONFIGURACIÓN E IDENTIDAD VISUAL ---
st.set_page_config(page_title="ORH - AME Táctico 10.0", layout="wide", page_icon="🚑")

# Estilo personalizado para una interfaz más limpia y profesional
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stChatFloatingInputContainer { bottom: 20px; }
    .reportview-container .main .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

FIRMA = "ALLH-ORH:2026"
LEMA = '"No solo es querer salvar, sino saber salvar" Organización Rescate Humboldt.'
COPYRIGHT_FULL = "ORGANIZACIÓN RESCATE HUMBOLDT - COORDINACIÓN DE RECURSOS HUMANOS - DIVISIÓN DE ATENCIÓN MÉDICA DE EMERGENCIA - (ALLH-ORH:2026)"
LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/82/Gnome-medical-emergency.svg/1024px-Gnome-medical-emergency.svg.png"

# --- 2. CONTROL DE ACCESO ---
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🚑 Sistema Táctico AME - ORH")
    c1, c2 = st.columns([1, 2])
    with c1: st.image(LOGO_URL, width=120)
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

# --- 3. CONEXIÓN NEURONAL (IA) ---
client = None
if "GENAI_API_KEY" in st.secrets:
    try:
        client = genai.Client(api_key=st.secrets["GENAI_API_KEY"])
        MODELO = "gemini-2.0-flash" # Versión optimizada para razonamiento rápido
    except Exception as e: st.error(f"Error IA: {e}")

# --- 4. PROMPT MAESTRO (CONSOLIDADO) ---
SYSTEM_PROMPT = f"""
ROL: Oficial Médico y SAR de la Organización Rescate Humboldt (ORH). {FIRMA}
FUENTES: PHTLS 10ma Ed (2025-2026), TECC/TCCC, ACLS/BLS AHA 2024, ATLS, Código Penal Ven, Ley Ejercicio Medicina Ven, Deontología de Enfermería Ven, Estatutos ORH.

REGLAS DE ORO:
1. AMIGABILIDAD PROFESIONAL: Saluda al operador ("Entendido, Operador"). Sé asertivo y práctico.
2. NO REDUNDANCIA: No expliques técnicas básicas a menos que haya dudas o se te pida explícitamente.
3. PRECISIÓN CLÍNICA: Solo recomienda sobre base de evidencia (signos/síntomas reportados).
4. INTELIGENCIA DE TERRENO (OBLIGATORIO): Si se da una ubicación, detalla obligatoriamente:
   - Geografía (Riesgos de terreno).
   - Hidrología/Clima (Crecidas, pronóstico).
   - Fauna/Flora (Amenazas biológicas).
   - Recursos Naturales (Supervivencia/Pernocta).
5. MARCO LEGAL: Advierte sobre atribuciones legales según la ley venezolana si el procedimiento es invasivo.
6. FASES: Care Under Fire -> Tactical Field Care -> TACEVAC.

CIERRE: {LEMA}

SALIDA JSON (INVISIBLE):
UPDATE_DATA: {{
  "info": {{ "operador": "...", "paciente": "...", "ubicacion": "...", "tipo_incidente": "...", "hora": "..." }},
  "march": {{ "M": "...", "A": "...", "R": "...", "C": "...", "H": "..." }},
  "farmaco": "..."
}}
"""

# --- 5. GESTIÓN DE ESTADO ---
vars_list = ["operador", "paciente", "ubicacion", "tipo_incidente", "hora", "farmaco", "M", "A", "R", "C", "H"]
for v in vars_list:
    if v not in st.session_state:
        st.session_state[v] = "Terrestre" if v == "tipo_incidente" else (datetime.now().strftime('%H:%M') if v == "hora" else "")

if 'chat' not in st.session_state: st.session_state.chat = []

# --- 6. CLASE PDF INSTITUCIONAL ---
class ORH_Report(FPDF):
    def header(self):
        try: self.image("logo_temp.png", 10, 8, 22)
        except: pass
        self.set_font('Arial', 'B', 14)
        self.cell(0, 7, 'ORGANIZACIÓN RESCATE HUMBOLDT', 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, 'DIVISIÓN DE ATENCIÓN MÉDICA DE EMERGENCIA (AME)', 0, 1, 'C')
        self.set_draw_color(200, 0, 0)
        self.line(10, 32, 200, 32)
        self.ln(12)

    def footer(self):
        self.set_y(-25)
        self.set_font('Arial', 'I', 7)
        self.multi_cell(0, 4, f"{COPYRIGHT_FULL}\n{LEMA}", 0, 'C')

# --- 7. INTERFAZ OPERATIVA ---
logo_path = "logo_temp.png"
if not os.path.exists(logo_path):
    try:
        r = requests.get(LOGO_URL)
        with open(logo_path, 'wb') as f: f.write(r.content)
    except: pass

st.sidebar.title("SISTEMA CENTINELA")
st.sidebar.image(LOGO_URL, width=100)
st.sidebar.markdown(f"**ID:** {FIRMA}")
st.sidebar.markdown("---")

tab1, tab2, tab3 = st.tabs(["💬 CONSULTOR TÁCTICO", "📋 FICHA TÉCNICA", "📄 INFORME OFICIAL"])

with tab1:
    st.subheader("Interacción y Asesoría AME")
    for m in st.session_state.chat:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    
    if q := st.chat_input("Operador, ingrese reporte de situación o ubicación..."):
        st.session_state.chat.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        
        with st.chat_message("assistant"):
            if client:
                with st.spinner("Procesando inteligencia..."):
                    res = client.models.generate_content(model=MODELO, contents=[SYSTEM_PROMPT, q])
                    full_text = res.text
                    
                    # Extracción de datos para autollenado
                    match = re.search(r"UPDATE_DATA:\s*(\{.*\})", full_text, re.DOTALL)
                    if match:
                        try:
                            js = json.loads(match.group(1).replace("'", '"'))
                            for key in ["info", "march"]:
                                for k, v in js[key].items():
                                    if v and v != "...": st.session_state[k] = v
                            if js.get("farmaco"): st.session_state["farmaco"] = js["farmaco"]
                        except: pass

                    clean_res = re.sub(r"UPDATE_DATA:.*", "", full_text, flags=re.DOTALL)
                    st.markdown(clean_res)
                    st.session_state.chat.append({"role": "assistant", "content": clean_res})

with tab2:
    st.subheader("Registro de Campo")
    c1, c2, c3 = st.columns(3)
    st.session_state["operador"] = c1.text_input("Operador SAR", st.session_state["operador"])
    st.session_state["paciente"] = c2.text_input("Paciente", st.session_state["paciente"])
    st.session_state["ubicacion"] = c3.text_input("Ubicación/COORD", st.session_state["ubicacion"])
    
    st.markdown("### Evaluación Primaria (MARCH)")
    
    m_cols = st.columns(5)
    keys = ["M", "A", "R", "C", "H"]
    for i, k in enumerate(keys):
        st.session_state[k] = m_cols[i].text_area(k, st.session_state[k], height=120)
    
    st.session_state["farmaco"] = st.text_area("Análisis de Riesgo y Terapéutica", st.session_state["farmaco"])

with tab3:
    st.subheader("Gestión de Informe Institucional")
    st.info("
