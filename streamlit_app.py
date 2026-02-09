import streamlit as st
import requests
import json
import re
import os
from datetime import datetime
from fpdf import FPDF

# --- 1. CONFIGURACIÓN E IDENTIDAD ---
st.set_page_config(page_title="ORH - Asesor Táctico 2026", layout="wide", page_icon="🚑")

FIRMA = "ALLH-ORH:2026"
LEMA = '"No solo es querer salvar, sino saber salvar" Organización Rescate Humboldt.'
COPYRIGHT = "ORH - COORDINACIÓN DE RECURSOS HUMANOS - DIVISIÓN AME"

# --- 2. CONFIGURACIÓN DE IA GRATUITA (Hugging Face) ---
# Necesitas un "Access Token" gratuito de huggingface.co
API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
headers = {"Authorization": f"Bearer {st.secrets.get('HF_TOKEN', '')}"}

def consultar_ia(prompt):
    # Instrucciones integradas para que Mistral se porte como el asesor ORH
    payload = {
        "inputs": f"<s>[INST] {FIRMA}. Actúa como Asesor Táctico AME de la ORH. Protocolos PHTLS/TCCC. Al final añade JSON: UPDATE_DATA: {{'march': {{'M': '...', 'A': '...', 'R': '...', 'C': '...', 'H': '...'}}}} \nPregunta: {prompt} [/INST]",
        "parameters": {"max_new_tokens": 500, "temperature": 0.7}
    }
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()[0]['generated_text'].split("[/INST]")[-1]
    return "Error de conexión con el servidor táctico."

# --- 3. ESTADO DE LA APP ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'march' not in st.session_state: st.session_state.march = {k: "" for k in "MARCH"}

# --- 4. ACCESO ---
if not st.session_state.auth:
    st.title("🔒 Sistema AME - Acceso")
    u = st.text_input("Operador")
    p = st.text_input("Clave", type="password")
    if st.button("INGRESAR"):
        if u == "ORH2026" and p == "ORH2026":
            st.session_state.auth = True
            st.rerun()
    st.stop()

# --- 5. INTERFAZ ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/8/82/Gnome-medical-emergency.svg", width=100) # Placeholder si no tienes el archivo
st.sidebar.markdown(f"**SISTEMA ACTIVO**\n\n{LEMA}\n\nID: {FIRMA}")

tabs = st.tabs(["💬 Consultor IA", "🩺 MARCH", "📄 Informe"])

with tabs[0]:
    st.subheader("Consultor Táctico Mistral-ORH")
    user_q = st.chat_input("Consulta médica o reporte de escena...")
    if user_q:
        with st.chat_message("user"): st.write(user_q)
        with st.chat_message("assistant"):
            respuesta = consultar_ia(user_q)
            st.markdown(respuesta)
            
            # Intento de autollenado MARCH
            match = re.search(r"UPDATE_DATA:\s*(\{.*\})", respuesta)
            if match:
                try:
                    data = json.loads(match.group(1).replace("'", '"'))
                    for k in "MARCH": st.session_state.march[k] = data['march'].get(k, "")
                    st.toast("✅ Datos MARCH actualizados")
                except: pass

with tabs[1]:
    st.subheader("Protocolo Táctico MARCH")
    col = st.columns(5)
    st.session_state.march["M"] = col[0].text_input("M", st.session_state.march["M"])
    st.session_state.march["A"] = col[1].text_input("A", st.session_state.march["A"])
    st.session_state.march["R"] = col[2].text_input("R", st.session_state.march["R"])
    st.session_state.march["C"] = col[3].text_input("C", st.session_state.march["C"])
    st.session_state.march["H"] = col[4].text_input("H", st.session_state.march["H"])

with tabs[2]:
    st.subheader("Informe Final")
    resumen = f"REPORTE ORH - AME\nMARCH: {st.session_state.march}\n{FIRMA}"
    st.text_area("Previsualización", resumen)
    if st.button("Descargar PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, resumen)
        st.download_button("Guardar PDF", data=bytes(pdf.output()), file_name="Reporte_ORH.pdf")
