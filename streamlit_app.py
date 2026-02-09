import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import re
from datetime import datetime
from fpdf import FPDF

# --- IDENTIDAD ---
FIRMA = "ALLH-ORH:2026"
LEMA = '"No solo es querer salvar, sino saber salvar" Organización Rescate Humboldt.'
COPYRIGHT = "ORH - DIVISIÓN DE ATENCIÓN MÉDICA DE EMERGENCIA (AME)"

# --- CONFIGURACIÓN IA (GEMINI 3 FLASH) ---
# Usamos el API Key que proporcionaste
API_KEY = "AIzaSyBHWvkKJKIaWY1f9EX8ntCsBovLy-HYD8s"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-3-flash')

def consultar_ia(prompt):
    instrucciones = f"""SISTEMA: Eres el Asesor AME de la ORH ({FIRMA}). 
    Protocolos: PHTLS 10 y TCCC. Analiza riesgos climáticos y geográficos.
    Al final de tu respuesta técnica, añade SIEMPRE este JSON:
    UPDATE_DATA: {{"march": {{"M": "...", "A": "...", "R": "...", "C": "...", "H": "..."}}}}
    CONSULTA: {prompt}"""
    
    try:
        # Configuración para permitir contenido médico de emergencia sin bloqueos
        response = model.generate_content(
            instrucciones,
            safety_settings=[
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        )
        return response.text
    except Exception as e:
        return f"⚠️ Error en el motor IA: {str(e)}. Por favor, proceda con el registro manual."

# --- ESTADO DE LA APP ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'stats' not in st.session_state: st.session_state.stats = {"Total": 0}
if 'march' not in st.session_state: st.session_state.march = {k: "" for k in "MARCH"}

# --- ACCESO ---
st.set_page_config(page_title="ORH AME 2026", layout="wide")
if not st.session_state.auth:
    st.title("🚑 Acceso Operativo ORH")
    if st.text_input("Credencial Operativa", type="password") == "ORH2026":
        st.session_state.auth = True
        st.rerun()
    st.stop()

# --- INTERFAZ ---
st.sidebar.title("SISTEMA ORH")
st.sidebar.info(f"**{LEMA}**\n\nID: {FIRMA}")

tabs = st.tabs(["💬 Consultor Táctico", "🩺 Protocolo MARCH", "📊 Estadísticas", "📄 Informe Final"])

with tabs[0]:
    st.subheader("Asesoría Médica en Tiempo Real (Gemini 3)")
    if "chat" not in st.session_state: st.session_state.chat = []
    for m in st.session_state.chat:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if q := st.chat_input("Describa la situación del paciente..."):
        st.session_state.chat.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        with st.chat_message("assistant"):
            res = consultar_ia(q)
            # Autollenado automático del MARCH
            match = re.search(r"UPDATE_DATA:\s*(\{.*\})", res, re.DOTALL)
            if match:
                try:
                    js = json.loads(match.group(1).replace("'", '"'))
                    for k in "MARCH":
                        if js["march"].get(k) and js["march"][k] != "...":
                            st.session_state.march[k] = js["march"][k]
                    st.toast("✅ Protocolo MARCH actualizado automáticamente")
                except: pass
            clean_res = re.sub(r"UPDATE_DATA:.*", "", res, flags=re.DOTALL)
            st.markdown(clean_res)
            st.session_state.chat.append({"role": "assistant", "content": clean_res})

with tabs[1]:
    st.subheader("Registro MARCH")
    m_cols = st.columns(5)
    for i, k in enumerate("MARCH"):
        st.session_state.march[k] = m_cols[i].text_input(k, st.session_state.march[k])
    if st.button("💾 REGISTRAR CASO"):
        st.session_state.stats["Total"] += 1
        st.success("Caso contabilizado con éxito.")

with tabs[3]:
    st.subheader("Generación de Informe")
    info = f"INFORME AME - ORH\nID: {FIRMA}\nFECHA: {datetime.now()}\n\nMARCH: {st.session_state.march}\n\n{LEMA}"
    st.text_area("Vista Previa", info, height=200)
    if st.button("📥 DESCARGAR PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, info.encode('latin-1', 'replace').decode('latin-1'))
        st.download_button("Guardar en dispositivo", data=bytes(pdf.output()), file_name="Reporte_ORH.pdf")

st.markdown(f"--- \n<center><small>{COPYRIGHT}<br>{FIRMA}</small></center>", unsafe_allow_html=True)
