import streamlit as st
from google import genai
from fpdf import FPDF
import json, re, os
from datetime import datetime
import requests

# --- 1. CONFIGURACIÓN E IDENTIDAD INSTITUCIONAL ---
st.set_page_config(page_title="ORH - AME Táctico 11.0", layout="wide", page_icon="🚑")

FIRMA = "ALLH-ORH:2026"
LEMA = '"No solo es querer salvar, sino saber salvar" Organización Rescate Humboldt.'
COPYRIGHT_FULL = "ORGANIZACIÓN RESCATE HUMBOLDT - COORDINACIÓN DE RECURSOS HUMANOS - DIVISIÓN DE ATENCIÓN MÉDICA DE EMERGENCIA - (ALLH-ORH:2026)"
LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/82/Gnome-medical-emergency.svg/1024px-Gnome-medical-emergency.svg.png"

# --- 2. CONTROL DE ACCESO ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🚑 Sistema Táctico AME - ORH")
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

# --- 3. CONEXIÓN AL CLIENTE (CORREGIDO) ---
@st.cache_resource
def get_ai_client():
    api_key = st.secrets.get("GENAI_API_KEY")
    if not api_key:
        st.error("Error: GENAI_API_KEY no configurada en Secrets.")
        return None
    return genai.Client(api_key=api_key)

client = get_ai_client()
# Nombre de modelo compatible con SDK v1.0+
MODELO_ID = "gemini-2.0-flash" 

# --- 4. PROMPT MAESTRO (ENTORNO, TÁCTICA Y LEY) ---
SYSTEM_PROMPT = f"""
ACTÚA COMO: Oficial de Operaciones SAR y Asesor Médico Táctico de la ORH ({FIRMA}).

REGLAS CRÍTICAS:
1. PRECISIÓN OPERATIVA: El operador es personal capacitado. Evita redundancia en técnicas básicas (RCP, torniquetes) a menos que se solicite o detectes inseguridad.
2. INTELIGENCIA DE TERRENO SAR: Si se detecta una ubicación o coordenadas, incluye SIEMPRE un análisis de:
   - Geografía/Riesgos (Suelos, pendientes).
   - Hidrología/Clima (Crecidas, pronóstico de montaña).
   - Fauna/Flora (Ofidismo, recursos para pernocta).
3. MARCO LEGAL VENEZUELA: Respeta el Código Penal, Ley de Medicina y Deontología SAR. Advierte sobre límites legales en actos invasivos.
4. ESTRUCTURA: Fase 1 (Amenaza Directa), Fase 2 (MARCH), Fase 3 (TACEVAC).

CIERRE: {LEMA}

UPDATE_DATA: JSON oculto para autollenado de ficha.
"""

# --- 5. ESTADO DE SESIÓN ---
if 'chat' not in st.session_state: st.session_state.chat = []
for k in ["operador", "paciente", "ubicacion", "M", "A", "R", "C", "H", "farmaco"]:
    if k not in st.session_state: st.session_state[k] = ""

# --- 6. GENERADOR PDF ---
class ORHPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 5, 'ORGANIZACIÓN RESCATE HUMBOLDT', 0, 1, 'C')
        self.set_font('Arial', '', 8)
        self.cell(0, 5, 'DIVISIÓN AME - REPORTE TÁCTICO', 0, 1, 'C')
        self.ln(10)
    def footer(self):
        self.set_y(-22)
        self.set_font('Arial', 'I', 6)
        self.multi_cell(0, 4, f"{COPYRIGHT_FULL}\n{LEMA}", 0, 'C')

# --- 7. INTERFAZ ---
tab1, tab2, tab3 = st.tabs(["💬 CONSULTOR", "📋 FICHA", "📄 PDF"])

with tab1:
    for m in st.session_state.chat:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    
    if q := st.chat_input("Reporte situación o coordenadas..."):
        st.session_state.chat.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        
        with st.chat_message("assistant"):
            if client:
                try:
                    # Llamada corregida para evitar ClientError
                    res = client.models.generate_content(
                        model=MODELO_ID,
                        contents=f"{SYSTEM_PROMPT}\n\nSOLICITUD OPERADOR: {q}"
                    )
                    full_text = res.text
                    
                    # Sincronización de datos (Regex)
                    match = re.search(r"UPDATE_DATA:\s*(\{.*\})", full_text, re.DOTALL)
                    if match:
                        try:
                            js = json.loads(match.group(1).replace("'", '"'))
                            for cat in ["info", "march"]:
                                for k, v in js[cat].items():
                                    if v and v != "...": st.session_state[k] = v
                        except: pass

                    clean_res = re.sub(r"UPDATE_DATA:.*", "", full_text, flags=re.DOTALL)
                    st.markdown(clean_res)
                    st.session_state.chat.append({"role": "assistant", "content": clean_res})
                except Exception as e:
                    st.error(f"Error Crítico de Conexión: {e}")

with tab2:
    st.subheader("Datos de la Misión")
    c1, c2 = st.columns(2)
    st.session_state.operador = c1.text_input("Operador SAR", st.session_state.operador)
    st.session_state.ubicacion = c2.text_input("Ubicación/Coordenadas", st.session_state.ubicacion)
    
    m_cols = st.columns(5)
    for i, k in enumerate(["M", "A", "R", "C", "H"]):
        st.session_state[k] = m_cols[i].text_area(k, st.session_state[k], height=100)
    st.session_state.farmaco = st.text_area("Tratamiento y Notas de Riesgo", st.session_state.farmaco)

with tab3:
    st.subheader("Informe Oficial")
    
    if st.button("📥 GENERAR Y DESCARGAR PDF"):
        pdf = ORHPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 10, f"REPORTE DE CAMPO - {datetime.now().strftime('%d/%m/%Y %H:%M')}", 1, 1, 'C')
        pdf.ln(5)
        pdf.multi_cell(0, 5, f"Operador: {st.session_state.operador}\nUbicación: {st.session_state.ubicacion}\n\nMARCH:\n{st.session_state.M}\n{st.session_state.A}\n{st.session_state.R}\n{st.session_state.C}\n{st.session_state.H}\n\nTratamiento:\n{st.session_state.farmaco}")
        st.download_button("Guardar PDF", data=bytes(pdf.output()), file_name=f"ORH_AME_{datetime.now().strftime('%H%M')}.pdf")

st.markdown(f"--- \n<center><small>{COPYRIGHT_FULL}</small></center>", unsafe_allow_html=True)
