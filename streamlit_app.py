import streamlit as st
from google import genai
from fpdf import FPDF
import json, re, os
from datetime import datetime
from PIL import Image
import requests

# --- 1. CONFIGURACIÓN E IDENTIDAD ---
st.set_page_config(page_title="ORH - AME Táctico Legal", layout="wide", page_icon="🚑")

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

# --- 4. PROMPT DE PRECISIÓN TÁCTICA Y LEGAL (ACTUALIZADO) ---
SYSTEM_PROMPT = f"""
ACTÚA COMO: Oficial Médico/SAR de la Organización Rescate Humboldt (ORH).
PROPIEDAD: {FIRMA}.

FUENTES DE REFERENCIA OBLIGATORIAS:
- Clínicas: PHTLS 10ma Ed (2025-2026), TECC/TCCC, AHA 2024 (Drowning), ACLS/BLS.
- Legales Ven: Código Penal (Omisión de Socorro), Ley del Ejercicio de la Medicina, Código de Deontología de Enfermería, LOPCYMAT y Estatutos ORH.

REGLAS DE INTERACCIÓN:
1. PRECISIÓN AMIGABLE: Sé cordial con el operador ("Entendido, Operador", "Proceda con precaución").
2. NO ASUMIR: Si no hay evidencia de signos (TA, FC, FR, SPO2) o síntomas, NO des recomendaciones farmacológicas.
3. MARCO LEGAL: Si una acción sugerida tiene implicaciones legales (ej. realizar una cricotiroidotomía sin ser personal médico), advierte al operador sobre el límite de sus atribuciones según la ley venezolana.
4. ESTRUCTURA POR FASES:
   - FASE 1: Amenaza Directa (Care Under Fire).
   - FASE 2: Campo Táctico (MARCH).
   - FASE 3: Evacuación (TACEVAC).

FINALIZACIÓN: Todas las respuestas deben cerrar estrictamente con: {LEMA}

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

# --- 6. GENERADOR DE PDF INSTITUCIONAL ---
class ORHPDF(FPDF):
    def header(self):
        try: self.image("logo_temp.png", 10, 8, 20)
        except: pass
        self.set_font('Arial', 'B', 12)
        self.cell(0, 5, 'ORGANIZACIÓN RESCATE HUMBOLDT', 0, 1, 'C')
        self.set_font('Arial', '', 9)
        self.cell(0, 5, 'DIVISIÓN DE ATENCIÓN MÉDICA DE EMERGENCIA', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-22)
        self.set_font('Arial', 'I', 6)
        # Copyright solicitado
        self.multi_cell(0, 4, f"{COPYRIGHT_FULL}\n{LEMA}", 0, 'C')

# --- 7. INTERFAZ ---
logo_path = "logo_temp.png"
if not os.path.exists(logo_path):
    try:
        r = requests.get(LOGO_URL)
        with open(logo_path, 'wb') as f: f.write(r.content)
    except: pass

st.sidebar.title("SISTEMA ORH - AME")
st.sidebar.image(LOGO_URL, width=80)
st.sidebar.info(f"**ID OPERATIVO:** {FIRMA}")

tab1, tab2, tab3 = st.tabs(["💬 CONSULTOR TÁCTICO", "📋 REGISTRO DE CAMPO", "📄 INFORME PDF"])

with tab1:
    st.write("### Centro de Mando e IA")
    for m in st.session_state.chat:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    
    if q := st.chat_input("Operador, describa la situación actual..."):
        st.session_state.chat.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        
        with st.chat_message("assistant"):
            if client:
                with st.spinner("Consultando protocolos y marco legal..."):
                    res = client.models.generate_content(model=MODELO, contents=[SYSTEM_PROMPT, q])
                    full_text = res.text
                    
                    # Motor de Autollenado invisible
                    match = re.search(r"UPDATE_DATA:\s*(\{.*\})", full_text, re.DOTALL)
                    if match:
                        try:
                            js = json.loads(match.group(1).replace("'", '"'))
                            for cat in ["info", "march"]:
                                for k, v in js[cat].items():
                                    if v and v != "...": st.session_state[k] = v
                            if js.get("farmaco"): st.session_state["farmaco"] = js["farmaco"]
                            st.toast("Datos sincronizados con la ficha")
                        except: pass

                    clean_res = re.sub(r"UPDATE_DATA:.*", "", full_text, flags=re.DOTALL)
                    st.markdown(clean_res)
                    st.session_state.chat.append({"role": "assistant", "content": clean_res})

with tab2:
    st.subheader("Ficha de Atención Prehospitalaria")
    c1, c2 = st.columns(2)
    st.session_state["operador"] = c1.text_input("Operador SAR/APH", st.session_state["operador"])
    st.session_state["paciente"] = c2.text_input("Identificación Paciente", st.session_state["paciente"])
    
    st.markdown("**Evaluación Primaria (Protocolo MARCH)**")
    m_cols = st.columns(5)
    labels = ["M (Hemorragia)", "A (Vía Aérea)", "R (Respiración)", "C (Circulación)", "H (Hipotermia)"]
    keys = ["M", "A", "R", "C", "H"]
    for i, k in enumerate(keys):
        st.session_state[k] = m_cols[i].text_area(labels[i], st.session_state[k], height=100)
    
    st.session_state["farmaco"] = st.text_area("Terapéutica, Fármacos y Observaciones Legales", st.session_state["farmaco"])

with tab3:
    st.subheader("Generación de Informe Institucional")
    st.info("Este informe cumple con los estándares de la ORH y sirve como respaldo de la actuación realizada.")
    
    

    if st.button("🖨️ GENERAR INFORME PDF"):
        pdf = ORHPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 10, f"REGISTRO DE INCIDENTE - FECHA: {datetime.now().strftime('%d/%m/%Y')} | HORA: {st.session_state['hora']}", 1, 1, 'C')
        
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, "1. IDENTIFICACIÓN", 0, 1)
        pdf.set_font('Arial', '', 9)
        pdf.multi_cell(0, 5, f"Operador: {st.session_state['operador']}\nUbicación: {st.session_state['ubicacion']}\nPaciente: {st.session_state['paciente']}")
        
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, "2. HALLAZGOS CLÍNICOS (MARCH)", 0, 1)
        pdf.set_font('Arial', '', 9)
        march_full = f"M: {st.session_state['M']}\nA: {st.session_state['A']}\nR: {st.session_state['R']}\nC: {st.session_state['C']}\nH: {st.session_state['H']}"
        pdf.multi_cell(0, 5, march_full.encode('latin-1', 'replace').decode('latin-1'))
        
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, "3. INTERVENCIONES Y TRATAMIENTO", 0, 1)
        pdf.set_font('Arial', '', 9)
        pdf.multi_cell(0, 5, st.session_state['farmaco'].encode('latin-1', 'replace').decode('latin-1'))
        
        pdf.ln(10)
        pdf.set_font('Arial', 'I', 8)
        pdf.multi_cell(0, 4, "Aviso Legal: Las actuaciones descritas se basan en protocolos internacionales y nacionales de atención de emergencias. Este reporte es confidencial y para uso exclusivo de la ORH.")
        
        output = pdf.output()
        st.download_button("⬇️ DESCARGAR INFORME OFICIAL ORH", data=bytes(output), file_name=f"Informe_ORH_AME_{datetime.now().strftime('%H%M')}.pdf")

st.markdown(f"--- \n<center><small>{COPYRIGHT_FULL}</small></center>", unsafe_allow_html=True)
