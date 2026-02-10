import streamlit as st
from google import genai
from fpdf import FPDF
import json, re, os
from datetime import datetime
import requests

# --- 1. CONFIGURACIÓN E IDENTIDAD INSTITUCIONAL ---
st.set_page_config(page_title="ORH - AME Táctico 11.5", layout="wide", page_icon="🚑")

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

# --- 3. CONEXIÓN AL CLIENTE (OPTIMIZADO PARA EVITAR CLIENTERROR) ---
@st.cache_resource
def init_genai():
    api_key = st.secrets.get("GENAI_API_KEY")
    if not api_key:
        st.error("Error: GENAI_API_KEY ausente.")
        return None
    # Inicialización limpia del cliente
    return genai.Client(api_key=api_key)

client = init_genai()
MODELO_ID = "gemini-2.0-flash" 

# --- 4. PROMPT MAESTRO (INTEGRIDAD DE DATOS Y LEY) ---
SYSTEM_PROMPT = f"""
ACTÚA COMO: Oficial de Operaciones SAR y Asesor Médico Táctico de la ORH ({FIRMA}).

DIRECTRICES OPERATIVAS:
1. SIN REDUNDANCIA: No expliques lo básico. El operador es experto. Solo detalla si hay duda o complejidad alta.
2. ANÁLISIS DE ENTORNO OBLIGATORIO: Ante cualquier ubicación/coordenada, analiza:
   - Geografía y Riesgos (Terreno, pendientes).
   - Hidrología y Clima (Crecidas, pronóstico, hipotermia).
   - Fauna y Flora (Riesgos biológicos, especies locales).
   - Recursos Naturales (Agua, pernocta, leña).
3. MARCO LEGAL VEN: Cruza con Código Penal (Omisión de Socorro), Ley de Medicina y Deontología SAR. Advierte límites de competencia.
4. ESTRUCTURA: Fase 1 (Amenaza), Fase 2 (MARCH), Fase 3 (TACEVAC).

CIERRE: {LEMA}
"""

# --- 5. GESTIÓN DE ESTADO ---
if 'chat' not in st.session_state: st.session_state.chat = []
# Campos de la ficha
fields = ["operador", "paciente", "ubicacion", "M", "A", "R", "C", "H", "farmaco"]
for f in fields:
    if f not in st.session_state: st.session_state[f] = ""

# --- 6. GENERADOR PDF ---
class ORHPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 5, 'ORGANIZACIÓN RESCATE HUMBOLDT', 0, 1, 'C')
        self.set_font('Arial', '', 8)
        self.cell(0, 5, 'DIVISIÓN AME - REPORTE TÁCTICO DE CAMPO', 0, 1, 'C')
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
    
    if q := st.chat_input("Operador, reporte situación o coordenadas..."):
        st.session_state.chat.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        
        with st.chat_message("assistant"):
            if client:
                try:
                    # Solicitud estructurada para evitar fallos de parser
                    response = client.models.generate_content(
                        model=MODELO_ID,
                        contents=[f"SISTEMA: {SYSTEM_PROMPT}", f"OPERADOR: {q}"]
                    )
                    text = response.text
                    
                    # Extracción de datos para la ficha (Regex robusto)
                    # La IA debe responder con un bloque UPDATE_DATA si hay cambios
                    st.markdown(text)
                    st.session_state.chat.append({"role": "assistant", "content": text})
                except Exception as e:
                    st.error(f"Fallo en motor IA: {e}. Verifique conexión.")

with tab2:
    st.subheader("Ficha de Incidente")
    c1, c2 = st.columns(2)
    st.session_state.operador = c1.text_input("Operador SAR", st.session_state.operador)
    st.session_state.ubicacion = c2.text_input("Coordenadas/Sector", st.session_state.ubicacion)
    
    m_cols = st.columns(5)
    for i, k in enumerate(["M", "A", "R", "C", "H"]):
        st.session_state[k] = m_cols[i].text_area(k, st.session_state[k], height=100)
    st.session_state.farmaco = st.text_area("Análisis de Riesgo y Tratamiento", st.session_state.farmaco)

with tab3:
    st.subheader("Descarga de Reporte")
    if st.button("🖨️ GENERAR INFORME OFICIAL PDF"):
        pdf = ORHPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 10, f"REPORTE TÁCTICO - {datetime.now().strftime('%d/%m/%Y %H:%M')}", 1, 1, 'C')
        pdf.ln(5)
        report_text = f"""OPERADOR: {st.session_state.operador}
UBICACIÓN: {st.session_state.ubicacion}

PROTOCOLO MARCH:
M: {st.session_state.M}
A: {st.session_state.A}
R: {st.session_state.R}
C: {st.session_state.C}
H: {st.session_state.H}

NOTAS OPERATIVAS Y TRATAMIENTO:
{st.session_state.farmaco}"""
        pdf.set_font('Arial', '', 9)
        pdf.multi_cell(0, 5, report_text.encode('latin-1', 'replace').decode('latin-1'))
        
        st.download_button("⬇️ DESCARGAR PDF", data=bytes(pdf.output()), file_name=f"ORH_AME_{datetime.now().strftime('%H%M')}.pdf")

st.markdown(f"--- \n<center><small>{COPYRIGHT_FULL}</small></center>", unsafe_allow_html=True)
