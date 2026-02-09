import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import re
from datetime import datetime
from fpdf import FPDF

# --- IDENTIDAD Y SEGURIDAD ---
FIRMA = "ALLH-ORH:2026"
LEMA = '"No solo es querer salvar, sino saber salvar" Organización Rescate Humboldt.'
COPYRIGHT = "ORH - DIVISIÓN DE ATENCIÓN MÉDICA DE EMERGENCIA (AME)"

# --- CONFIGURACIÓN IA (GEMINI 3 FLASH - MODELO ACTUAL 2026) ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # Usamos Gemini 3 Flash según tu panel de control
    model = genai.GenerativeModel('gemini-3-flash')
else:
    st.error("⚠️ Falta GEMINI_API_KEY en los Secrets de Streamlit.")

def consultor_tactico_gemini(prompt):
    instrucciones = f"""SISTEMA: Eres el Asesor AME de la ORH ({FIRMA}). 
    PROTOCOLOS: PHTLS 10, TCCC. 
    TAREA: Analiza riesgos y provee guía médica. 
    JSON OBLIGATORIO AL FINAL: UPDATE_DATA: {{"march": {{"M": "...", "A": "...", "R": "...", "C": "...", "H": "..."}}}}
    CONSULTA: {prompt}"""
    
    try:
        # Configuración de seguridad para evitar bloqueos por contenido médico táctico
        response = model.generate_content(
            instrucciones,
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        )
        return response.text
    except Exception as e:
        return f"⚠️ Nota: El motor IA está en mantenimiento o límite de cuota. Proceda con llenado manual. (Error: {str(e)})"

# --- ESTADO DE SESIÓN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'stats' not in st.session_state: st.session_state.stats = {"Total": 0}
if 'march' not in st.session_state: st.session_state.march = {k: "" for k in "MARCH"}

# --- ACCESO ---
st.set_page_config(page_title="ORH AME 3.5", layout="wide", page_icon="🚑")
if not st.session_state.auth:
    st.title("🚑 Acceso Operativo ORH")
    if st.text_input("Credencial (ORH2026)", type="password") == "ORH2026":
        st.session_state.auth = True
        st.rerun()
    st.stop()

# --- INTERFAZ ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/8/82/Gnome-medical-emergency.svg", width=80)
st.sidebar.info(f"**{LEMA}**\n\nID: {FIRMA}")

tabs = st.tabs(["💬 Consultor IA (Gemini 3)", "🩺 MARCH", "📊 Estadísticas", "📄 Informe"])

with tabs[0]:
    st.subheader("Asesoría Médica Táctica 2026")
    if "chat" not in st.session_state: st.session_state.chat = []
    
    for m in st.session_state.chat:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if q := st.chat_input("Describa situación..."):
        st.session_state.chat.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        
        with st.chat_message("assistant"):
            with st.spinner("Consultando base de datos táctica..."):
                res = consultor_tactico_gemini(q)
            
            # Autollenado MARCH
            match = re.search(r"UPDATE_DATA:\s*(\{.*\})", res, re.DOTALL)
            if match:
                try:
                    js = json.loads(match.group(1).replace("'", '"'))
                    for k in "MARCH":
                        if js["march"].get(k) and js["march"][k] != "...":
                            st.session_state.march[k] = js["march"][k]
                    st.toast("✅ Datos MARCH sincronizados")
                except: pass
            
            clean_res = re.sub(r"UPDATE_DATA:.*", "", res, flags=re.DOTALL)
            st.markdown(clean_res)
            st.session_state.chat.append({"role": "assistant", "content": clean_res})

with tabs[1]:
    st.subheader("Evaluación Primaria MARCH")
    m_cols = st.columns(5)
    for i, k in enumerate("MARCH"):
        st.session_state.march[k] = m_cols[i].text_input(k, st.session_state.march[k])
    if st.button("💾 Guardar Datos"):
        st.session_state.stats["Total"] += 1
        st.success("Información guardada localmente.")

with tabs[3]:
    st.subheader("Exportar Informe")
    rep = f"REPORTE ORH AME\nID: {FIRMA}\nFECHA: {datetime.now()}\n\nMARCH: {st.session_state.march}\n\n{LEMA}"
    st.text_area("Previsualización", rep, height=200)
    if st.button("Descargar PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 10, rep.encode('latin-1', 'replace').decode('latin-1'))
        st.download_button("Guardar Archivo", data=bytes(pdf.output()), file_name="Reporte_ORH.pdf")

st.markdown(f"--- \n<center><small>{COPYRIGHT} | {FIRMA}</small></center>", unsafe_allow_html=True)
