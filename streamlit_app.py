import streamlit as st
from google import genai
from fpdf import FPDF
import json, re, os
from datetime import datetime
from PIL import Image
import requests

# --- 1. CONFIGURACIÓN E IDENTIDAD INSTITUCIONAL ---
st.set_page_config(page_title="ORH - AME Táctico 10.0", layout="wide", page_icon="🚑")

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

# --- 3. CONEXIÓN NEURONAL (GEMINI 2.0 FLASH) ---
client = None
if "GENAI_API_KEY" in st.secrets:
    try:
        client = genai.Client(api_key=st.secrets["GENAI_API_KEY"])
        MODELO = "gemini-2.0-flash"
    except Exception as e: st.error(f"Error IA: {e}")

# --- 4. PROMPT MAESTRO (PRECISIÓN, ENTORNO Y LEY) ---
SYSTEM_PROMPT = f"""
ACTÚA COMO: Oficial de Operaciones SAR y Asesor Médico Táctico de la ORH ({FIRMA}).

REGLAS DE ORO:
1. PRECISIÓN OPERATIVA: No seas redundante. El operador es personal capacitado. No expliques procedimientos básicos (RCP, torniquetes, etc.) a menos que se te solicite explícitamente o notes confusión.
2. ANÁLISIS DE ENTORNO SAR: Ante cualquier mención de ubicación o coordenadas, genera OBLIGATORIAMENTE una sección de "INTELIGENCIA DE TERRENO" detallando:
   - Geografía (Riesgo de caídas, estabilidad).
   - Hidrología/Clima (Crecidas, hipotermia por humedad, pronóstico).
   - Fauna/Flora (Ofidismo, plantas urticantes).
   - Recursos (Puntos de agua, leña, cuevas para pernocta).
3. MARCO LEGAL VENEZOLANO: Cruza tus consejos con el Código Penal, Ley del Ejercicio de la Medicina y Código de Deontología de Enfermería. Advierte sobre atribuciones legales en procedimientos invasivos.
4. FUENTES: PHTLS 10ma Ed (2025-2026), TECC/TCCC, BCLS, ATLS.

ESTRUCTURA DE RESPUESTA:
- FASE 1: Amenaza Directa (Care Under Fire).
- FASE 2: Campo Táctico (MARCH).
- FASE 3: Evacuación (TACEVAC).

CIERRE OBLIGATORIO: {LEMA}

SALIDA JSON (OCULTA):
UPDATE_DATA: {{
  "info": {{ "operador": "...", "paciente": "...", "ubicacion": "...", "tipo_incidente": "...", "hora": "..." }},
  "march": {{ "M": "...", "A": "...", "R": "...", "C": "...", "H": "..." }},
  "farmaco": "..."
}}
"""

# --- 5. GESTIÓN DE DATOS ---
vars_default = {
    "operador": "", "paciente": "", "ubicacion": "", "tipo_incidente": "Terrestre", 
    "hora": datetime.now().strftime('%H:%M'), "farmaco": "", 
    "M":"", "A":"", "R":"", "C":"", "H":""
}
for k, v in vars_default.items():
    if k not in st.session_state: st.session_state[k] = v
if 'chat' not in st.session_state: st.session_state.chat = []

# --- 6. CLASE PDF INSTITUCIONAL ---
class ORHPDF(FPDF):
    def header(self):
        try: self.image("logo_temp.png", 10, 8, 20)
        except: pass
        self.set_font('Arial', 'B', 12)
        self.cell(0, 5, 'ORGANIZACIÓN RESCATE HUMBOLDT', 0, 1, 'C')
        self.set_font('Arial', '', 8)
        self.cell(0, 5, 'AME - REPORTE DE INCIDENTE TÁCTICO', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-22)
        self.set_font('Arial', 'I', 6)
        self.multi_cell(0, 4, f"{COPYRIGHT_FULL}\n{LEMA}", 0, 'C')

# --- 7. INTERFAZ DE USUARIO ---
logo_path = "logo_temp.png"
if not os.path.exists(logo_path):
    try:
        r = requests.get(LOGO_URL)
        with open(logo_path, 'wb') as f: f.write(r.content)
    except: pass

st.sidebar.title("ORH CENTRO DE MANDO")
st.sidebar.image(LOGO_URL, width=80)
st.sidebar.info(f"**UNIDAD:** {FIRMA}")

tab1, tab2, tab3 = st.tabs(["💬 CONSULTOR TÁCTICO", "📋 REGISTRO DE CAMPO", "📄 INFORME PDF"])

with tab1:
    st.subheader("Interacción con Operador")
    for m in st.session_state.chat:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    
    if q := st.chat_input("Operador, reporte situación o coordenadas..."):
        st.session_state.chat.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        
        with st.chat_message("assistant"):
            if client:
                with st.spinner("Procesando inteligencia..."):
                    res = client.models.generate_content(model=MODELO, contents=[SYSTEM_PROMPT, q])
                    full_text = res.text
                    
                    # Sincronización automática de datos
                    match = re.search(r"UPDATE_DATA:\s*(\{.*\})", full_text, re.DOTALL)
                    if match:
                        try:
                            js = json.loads(match.group(1).replace("'", '"'))
                            for cat in ["info", "march"]:
                                for k, v in js[cat].items():
                                    if v and v != "...": st.session_state[k] = v
                            st.toast("Ficha actualizada con IA")
                        except: pass

                    clean_res = re.sub(r"UPDATE_DATA:.*", "", full_text, flags=re.DOTALL)
                    st.markdown(clean_res)
                    st.session_state.chat.append({"role": "assistant", "content": clean_res})

with tab2:
    st.subheader("Datos Operativos (Sincronizados)")
    c1, c2, c3 = st.columns([2, 2, 1])
    st.session_state["operador"] = c1.text_input("Operador", st.session_state["operador"])
    st.session_state["ubicacion"] = c2.text_input("Ubicación/Coordenadas", st.session_state["ubicacion"])
    st.session_state["paciente"] = c3.text_input("Paciente", st.session_state["paciente"])
    
    st.markdown("**Evaluación MARCH**")
    m_cols = st.columns(5)
    keys = ["M", "A", "R", "C", "H"]
    for i, k in enumerate(keys):
        st.session_state[k] = m_cols[i].text_area(k, st.session_state[k], height=120)
    
    st.session_state["farmaco"] = st.text_area("Tratamiento, Notas de Riesgo y Observaciones Legales", st.session_state["farmaco"])

with tab3:
    st.subheader("Generación de Informe Institucional")
    st.info("Este documento es un registro oficial de la Organización Rescate Humboldt.")
    
    # Previsualización compacta
    with st.expander("Ver previsualización de datos"):
        st.write(f"**Operador:** {st.session_state['operador']}")
        st.write(f"**Ubicación:** {st.session_state['ubicacion']}")
        st.write(f"**MARCH:** {st.session_state['M']}, {st.session_state['A']}, {st.session_state['R']}, {st.session_state['C']}, {st.session_state['H']}")

    if st.button("📥 DESCARGAR INFORME OFICIAL (PDF)"):
        pdf = ORHPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 10, f"REGISTRO OPERATIVO - {datetime.now().strftime('%d/%m/%Y %H:%M')}", 1, 1, 'C')
        
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, "I. DATOS DE IDENTIFICACIÓN", 0, 1)
        pdf.set_font('Arial', '', 9)
        pdf.multi_cell(0, 5, f"Operador Responsable: {st.session_state['operador']}\nUbicación/Punto SAR: {st.session_state['ubicacion']}\nPaciente: {st.session_state['paciente']}")
        
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, "II. EVALUACIÓN Y PROTOCOLOS (MARCH)", 0, 1)
        pdf.set_font('Arial', '', 9)
        pdf.multi_cell(0, 5, f"M: {st.session_state['M']}\nA: {st.session_state['A']}\nR: {st.session_state['R']}\nC: {st.session_state['C']}\nH: {st.session_state['H']}".encode('latin-1', 'replace').decode('latin-1'))
        
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, "III. OBSERVACIONES OPERATIVAS Y LEGALES", 0, 1)
        pdf.set_font('Arial', '', 9)
        pdf.multi_cell(0, 5, st.session_state['farmaco'].encode('latin-1', 'replace').decode('latin-1'))
        
        pdf.ln(10)
        pdf.set_font('Arial', 'B', 8)
        pdf.cell(0, 5, "DECLARACIÓN:", 0, 1)
        pdf.set_font('Arial', '', 7)
        pdf.multi_cell(0, 4, "El personal actuante declara que los procedimientos se realizaron bajo protocolos internacionales vigentes y en cumplimiento con el marco legal de la República Bolivariana de Venezuela.")
        
        st.download_button("Guardar PDF Oficial", data=bytes(pdf.output()), file_name=f"ORH_AME_{datetime.now().strftime('%H%M')}.pdf")

st.markdown(f"--- \n<center><small>{COPYRIGHT_FULL}</small></center>", unsafe_allow_html=True)
