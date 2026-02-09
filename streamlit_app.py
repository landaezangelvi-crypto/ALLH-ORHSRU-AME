import streamlit as st
from google import genai
from fpdf import FPDF
import json
import re
import os
from datetime import datetime

# --- CONFIGURACIÓN ORH ---
FIRMA = "ALLH-ORH:2026"
LEMA = '"No solo es querer salvar, sino saber salvar" Organización Rescate Humboldt.'

# --- NUEVA CONFIGURACIÓN SDK GEMINI 2.0 ---
if "GENAI_API_KEY" in st.secrets:
    try:
        # Inicialización con el nuevo SDK unificado
        client = genai.Client(api_key=st.secrets["GENAI_API_KEY"])
        MODELO = "gemini-2.0-flash" 
    except Exception as e:
        st.error(f"Error de inicialización SDK: {e}")
else:
    st.error("⚠️ Configura 'GENAI_API_KEY' en los Secrets de Streamlit.")

# --- PROMPT TÁCTICO ---
INSTRUCCIONES = f"""
Actúa como Asesor Táctico AME para la Organización Rescate Humboldt. Propiedad: {FIRMA}.
Sigue protocolos PHTLS 10, TCCC y ATLS. 
Al final de cada respuesta, incluye SIEMPRE este JSON para autollanado:
UPDATE_DATA: {{"march": {{"M": "...", "A": "...", "R": "...", "C": "...", "H": "..."}}, "clima": "...", "riesgo": "..."}}
"""

# --- LÓGICA DE SESIÓN ---
if 'march' not in st.session_state: st.session_state.march = {k: "" for k in "MARCH"}
if 'auth' not in st.session_state: st.session_state.auth = False

# --- INTERFAZ ---
st.set_page_config(page_title="ORH - Asesor Táctico", layout="wide")

if not st.session_state.auth:
    st.title("Acceso Operativo AME")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("INGRESAR"):
        if u == "ORH2026" and p == "ORH2026":
            st.session_state.auth = True
            st.rerun()
    st.stop()

# TABS
t1, t2, t3, t4 = st.tabs(["📋 Registro/MARCH", "🌍 Entorno", "💬 Chat IA", "📄 Informe"])

with t1:
    st.subheader("Protocolo Clínico")
    c1, c2 = st.columns(2)
    m = c1.text_input("M (Hemorragia)", value=st.session_state.march["M"])
    a = c1.text_input("A (Vía Aérea)", value=st.session_state.march["A"])
    r = c2.text_input("R (Respiración)", value=st.session_state.march["R"])
    c = c2.text_input("C (Circulación)", value=st.session_state.march["C"])
    h = st.text_input("H (Hipotermia/Heridas)", value=st.session_state.march["H"])

with t3:
    st.subheader("Consultor Táctico IA (Gemini 2.0)")
    if 'chat' not in st.session_state: st.session_state.chat = []
    
    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("Consulta técnica o reporte de escena..."):
        st.session_state.chat.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        with st.chat_message("assistant"):
            try:
                # Nueva forma de llamar al modelo en Gemini 2.0
                response = client.models.generate_content(
                    model=MODELO,
                    config={'system_instruction': INSTRUCCIONES},
                    contents=prompt
                )
                res_text = response.text
                
                # Sincronización de datos
                match = re.search(r"UPDATE_DATA:\s*(\{.*\})", res_text, re.DOTALL)
                if match:
                    data = json.loads(match.group(1))
                    for k in "MARCH": 
                        if data["march"].get(k): st.session_state.march[k] = data["march"][k]
                    st.toast("Datos MARCH actualizados automáticamente")

                clean_res = re.sub(r"UPDATE_DATA:.*", "", res_text, flags=re.DOTALL)
                st.markdown(clean_res)
                st.session_state.chat.append({"role": "assistant", "content": clean_res})
            except Exception as e:
                st.error(f"Error con el nuevo SDK: {e}")

with t4:
    st.subheader("Informe Final")
    reporte = f"REPORTE ORH\nFECHA: {datetime.now()}\nMARCH: {st.session_state.march}\n{FIRMA}"
    st.text_area("Vista", reporte, height=150)
    if st.button("Descargar PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, reporte)
        st.download_button("Guardar", data=pdf.output(), file_name="Reporte.pdf")

# Logo en Sidebar
if os.path.exists("LOGO_ORH57.JPG"):
    st.sidebar.image("LOGO_ORH57.JPG")
st.sidebar.write(f"SISTEMA: {FIRMA}")
