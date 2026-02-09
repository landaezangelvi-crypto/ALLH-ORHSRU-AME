import streamlit as st
import requests
import pandas as pd
import json
import re
import os
from datetime import datetime
from fpdf import FPDF

# --- IDENTIDAD Y SEGURIDAD ---
FIRMA = "ALLH-ORH:2026"
LEMA = '"No solo es querer salvar, sino saber salvar" Organización Rescate Humboldt.'
COPYRIGHT = "ORGANIZACIÓN RESCATE HUMBOLDT - DIVISIÓN AME"

# --- CONFIGURACIÓN IA (LLAMA 3.1 - MÁXIMA ESTABILIDAD) ---
# Usamos un endpoint de inferencia de alta disponibilidad
API_URL = "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3.1-8B-Instruct"
headers = {"Authorization": f"Bearer {st.secrets.get('HF_TOKEN', '')}"}

def llamar_ia_robusto(prompt):
    # Estructura de prompt optimizada para Llama 3.1
    sistema = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
    Eres el Asesor AME de la ORH ({FIRMA}). Protocolos PHTLS/TCCC.
    Responde de forma táctica y al final incluye este JSON:
    UPDATE_DATA: {{"march": {{"M": "...", "A": "...", "R": "...", "C": "...", "H": "..."}}}}
    <|eot_id|><|start_header_id|>user<|end_header_id|>
    {prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": sistema, "parameters": {"max_new_tokens": 800}}, timeout=20)
        if response.status_code == 200:
            return response.json()[0]['generated_text'].split("assistant")[-1].strip()
        elif response.status_code == 503:
            return "⏳ El motor está cargando. Reintenta en 15 segundos."
        elif response.status_code == 410:
            return "⚠️ El modelo actual fue movido por el proveedor. Notifica a soporte técnico."
        else:
            return f"⚠️ Error de conexión ({response.status_code})."
    except Exception as e:
        return f"⚠️ Error de red: {str(e)}"

# --- ESTADO DE LA APLICACIÓN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'stats' not in st.session_state: st.session_state.stats = {"Total": 0}
if 'march' not in st.session_state: st.session_state.march = {k: "" for k in "MARCH"}

# --- ACCESO ---
st.set_page_config(page_title="ORH AME", layout="wide")
if not st.session_state.auth:
    st.title("🚑 Sistema AME - ORH")
    if st.text_input("Clave", type="password") == "ORH2026":
        st.session_state.auth = True
        st.rerun()
    st.stop()

# --- INTERFAZ ---
st.sidebar.title("SISTEMA ORH")
st.sidebar.info(f"{LEMA}\n\nID: {FIRMA}")

tabs = st.tabs(["💬 Consultor IA", "🩺 MARCH", "📊 Estadísticas", "📄 Informe"])

# TAB CHAT
with tabs[0]:
    if "chat" not in st.session_state: st.session_state.chat = []
    for m in st.session_state.chat:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if q := st.chat_input("Consulta operativa..."):
        st.session_state.chat.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        with st.chat_message("assistant"):
            res = llamar_ia_robusto(q)
            # Lógica de sincronización
            match = re.search(r"UPDATE_DATA:\s*(\{.*\})", res, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1).replace("'", '"'))
                    for k in "MARCH": 
                        if data["march"].get(k) and data["march"][k] != "...":
                            st.session_state.march[k] = data["march"][k]
                    st.toast("✅ MARCH actualizado")
                except: pass
            
            clean_res = re.sub(r"UPDATE_DATA:.*", "", res, flags=re.DOTALL)
            st.markdown(clean_res)
            st.session_state.chat.append({"role": "assistant", "content": clean_res})

# TAB MARCH
with tabs[1]:
    st.subheader("Protocolo MARCH")
    m_cols = st.columns(5)
    for i, k in enumerate("MARCH"):
        st.session_state.march[k] = m_cols[i].text_input(k, st.session_state.march[k])
    if st.button("💾 Guardar"):
        st.session_state.stats["Total"] += 1
        st.success("Guardado.")

# TAB INFORME
with tabs[3]:
    st.subheader("Informe Final")
    reporte = f"ORH - REPORTE AME\n{FIRMA}\n\nMARCH: {st.session_state.march}"
    st.text_area("Previsualización", reporte, height=200)
    if st.button("📥 Descargar PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, reporte)
        st.download_button("Guardar PDF", data=bytes(pdf.output()), file_name="Reporte_ORH.pdf")
