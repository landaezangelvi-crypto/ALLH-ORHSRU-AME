import streamlit as st
from google import genai  # Nueva librería unificada de 2026
from fpdf import FPDF
import json
import re
from datetime import datetime

# --- CONFIGURACIÓN DE IDENTIDAD ---
FIRMA = "ALLH-ORH:2026"
LEMA = '"No solo es querer salvar, sino saber salvar" Organización Rescate Humboldt.'

# --- CONFIGURACIÓN DE IA (SDK 2026) ---
# Inicializamos el cliente fuera de cualquier función para evitar errores de "not defined"
client = None
if "GENAI_API_KEY" in st.secrets:
    try:
        client = genai.Client(api_key=st.secrets["GENAI_API_KEY"])
        MODELO_OPERATIVO = "gemini-2.5-flash" # Tu panel muestra que este tiene cuota disponible
    except Exception as e:
        st.error(f"Error crítico de inicialización: {e}")
else:
    st.error("⚠️ Falta GENAI_API_KEY en los Secrets de Streamlit.")

# --- GESTIÓN DE SESIÓN ---
if 'march' not in st.session_state:
    st.session_state.march = {k: "" for k in "MARCH"}
if 'auth' not in st.session_state:
    st.session_state.auth = False

# --- CONTROL DE ACCESO ---
st.set_page_config(page_title="ORH AME 4.0", layout="wide", page_icon="🚑")

if not st.session_state.auth:
    st.title("🚑 Sistema AME - Rescate Humboldt")
    with st.form("login"):
        if st.text_input("Credencial Operativa", type="password") == "ORH2026":
            if st.form_submit_button("ENTRAR"):
                st.session_state.auth = True
                st.rerun()
        else: st.form_submit_button("ENTRAR")
    st.stop()

# --- INTERFAZ PRINCIPAL ---
st.sidebar.title("SISTEMA ORH")
st.sidebar.info(f"**{LEMA}**\n\nID: {FIRMA}")

tab_ia, tab_march, tab_pdf = st.tabs(["💬 Consultor IA", "🩺 Protocolo MARCH", "📄 Informe"])

with tab_ia:
    st.subheader("Asesoría Médica en Tiempo Real")
    if "chat" not in st.session_state: st.session_state.chat = []
    
    for m in st.session_state.chat:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Describa la situación..."):
        st.session_state.chat.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        with st.chat_message("assistant"):
            if client:
                try:
                    # Instrucciones del sistema integradas en la llamada para evitar bloqueos
                    instruccion = f"Actúa como Asesor AME (ORH). Protocolos PHTLS/TCCC. Responde técnico y breve. Al final genera este JSON exacto: UPDATE_DATA: {{'march': {{'M': '...', 'A': '...', 'R': '...', 'C': '...', 'H': '...'}}}}"
                    
                    response = client.models.generate_content(
                        model=MODELO_OPERATIVO,
                        contents=[instruccion, prompt]
                    )
                    
                    full_text = response.text
                    
                    # Sincronización MARCH
                    match = re.search(r"UPDATE_DATA:\s*(\{.*\})", full_text, re.DOTALL)
                    if match:
                        try:
                            data = json.loads(match.group(1).replace("'", '"'))
                            for k in "MARCH":
                                if data["march"].get(k) and data["march"][k] != "...":
                                    st.session_state.march[k] = data["march"][k]
                            st.toast("✅ Datos MARCH sincronizados")
                        except: pass
                    
                    clean_text = re.sub(r"UPDATE_DATA:.*", "", full_text, flags=re.DOTALL)
                    st.markdown(clean_text)
                    st.session_state.chat.append({"role": "assistant", "content": clean_text})
                except Exception as e:
                    st.error(f"IA temporalmente fuera de línea. Use llenado manual. (Detalle: {e})")
            else:
                st.warning("IA no disponible por falta de llave de acceso.")

with tab_march:
    st.subheader("Evaluación Primaria Táctica")
    m_cols = st.columns(5)
    for i, k in enumerate("MARCH"):
        st.session_state.march[k] = m_cols[i].text_input(k, st.session_state.march[k], help=f"Fase {k} del protocolo")
    
    if st.button("💾 Guardar Progreso"):
        st.success("Información respaldada en la sesión.")

with tab_pdf:
    st.subheader("Generación de Documento")
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    reporte = f"REPORTE DE ATENCIÓN AME - ORH\nID: {FIRMA}\nFECHA: {fecha}\n\nRESULTADOS MARCH:\n"
    for k, v in st.session_state.march.items():
        reporte += f"- {k}: {v}\n"
    reporte += f"\n{LEMA}"
    
    st.text_area("Vista Previa", reporte, height=250)
    
    if st.button("📥 Descargar Reporte PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, reporte.encode('latin-1', 'replace').decode('latin-1'))
        st.download_button("Guardar PDF", data=bytes(pdf.output()), file_name=f"ORH_AME_{datetime.now().strftime('%H%M%S')}.pdf")
