import streamlit as st
from google import genai  # La nueva SDK unificada de 2026
from fpdf import FPDF
import json
import re
from datetime import datetime

# --- IDENTIDAD ---
FIRMA = "ALLH-ORH:2026"
LEMA = '"No solo es querer salvar, sino saber salvar" Organización Rescate Humboldt.'

# --- CONFIGURACIÓN DE IA ---
# Definimos el cliente como None al inicio para evitar el error "name 'client' is not defined"
client = None
if "GENAI_API_KEY" in st.secrets:
    try:
        client = genai.Client(api_key=st.secrets["GENAI_API_KEY"])
        # Usamos Gemini 3 Flash que es el que tu panel muestra con cuota limpia
        MODELO = "gemini-3-flash" 
    except Exception as e:
        st.error(f"Error de inicialización de IA: {e}")
else:
    st.warning("⚠️ IA Desconectada: Falta GENAI_API_KEY en los Secrets.")

# --- ESTADO DE SESIÓN ---
if 'march' not in st.session_state: st.session_state.march = {k: "" for k in "MARCH"}
if 'auth' not in st.session_state: st.session_state.auth = False

# --- INTERFAZ ---
st.set_page_config(page_title="ORH AME 2026", layout="wide")

if not st.session_state.auth:
    st.title("🚑 Acceso Operativo ORH")
    if st.text_input("Credencial", type="password") == "ORH2026":
        st.session_state.auth = True
        st.rerun()
    st.stop()

st.sidebar.title("SISTEMA ORH")
st.sidebar.info(f"**{LEMA}**\n\nID: {FIRMA}")

tabs = st.tabs(["💬 Consultor IA", "🩺 MARCH", "📄 Informe"])

with tabs[0]:
    st.subheader("Asesoría Médica Táctica")
    if "chat" not in st.session_state: st.session_state.chat = []
    
    for m in st.session_state.chat:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if q := st.chat_input("Describa situación..."):
        st.session_state.chat.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        
        with st.chat_message("assistant"):
            if client:
                try:
                    prompt_instruccion = f"Actúa como Asesor AME ORH. Protocolos TCCC. Al final genera: UPDATE_DATA: {{'march': {{'M': '...', 'A': '...', 'R': '...', 'C': '...', 'H': '...'}}}}"
                    response = client.models.generate_content(model=MODELO, contents=[prompt_instruccion, q])
                    
                    # Sincronización MARCH
                    match = re.search(r"UPDATE_DATA:\s*(\{.*\})", response.text, re.DOTALL)
                    if match:
                        try:
                            data = json.loads(match.group(1).replace("'", '"'))
                            for k in "MARCH":
                                if data["march"].get(k): st.session_state.march[k] = data["march"][k]
                            st.toast("✅ MARCH Actualizado")
                        except: pass
                    
                    clean_res = re.sub(r"UPDATE_DATA:.*", "", response.text, flags=re.DOTALL)
                    st.markdown(clean_res)
                    st.session_state.chat.append({"role": "assistant", "content": clean_res})
                except Exception as e:
                    st.error(f"IA Saturada. Proceda manualmente. (Error: {e})")
            else:
                st.error("IA no disponible. Verifique su API Key en Secrets.")

with tabs[1]:
    st.subheader("Evaluación MARCH")
    cols = st.columns(5)
    for i, k in enumerate("MARCH"):
        st.session_state.march[k] = cols[i].text_input(k, st.session_state.march[k])

with tabs[2]:
    st.subheader("Informe Final")
    rep = f"REPORTE ORH - {datetime.now()}\n\nMARCH: {st.session_state.march}\n\n{FIRMA}"
    st.text_area("Previsualización", rep, height=200)
    if st.button("Descargar PDF"):
        pdf = FPDF()
        pdf.add_page(); pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, rep.encode('latin-1', 'replace').decode('latin-1'))
        st.download_button("Guardar Archivo", data=bytes(pdf.output()), file_name="Reporte_AME.pdf")
