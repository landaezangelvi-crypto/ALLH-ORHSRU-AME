import streamlit as st
from google import genai  # IMPORTANTE: Esta es la nueva librería 2026
from fpdf import FPDF
import json
import re
from datetime import datetime

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="ORH - AME 2026", layout="wide", page_icon="🚑")

FIRMA = "ALLH-ORH:2026"
LEMA = '"No solo es querer salvar, sino saber salvar" Organización Rescate Humboldt.'

# --- INICIALIZACIÓN DE LA IA (NUEVA SDK) ---
if "GENAI_API_KEY" in st.secrets:
    try:
        # La nueva forma de conectar en 2026
        client = genai.Client(api_key=st.secrets["GENAI_API_KEY"])
        MODELO_ACTUAL = "gemini-2.5-flash" 
    except Exception as e:
        st.error(f"Error de conexión con el cliente IA: {e}")
else:
    st.error("⚠️ Falta GENAI_API_KEY en los Secrets de Streamlit.")

# --- GESTIÓN DE DATOS ---
if 'march' not in st.session_state:
    st.session_state.march = {k: "" for k in "MARCH"}
if 'auth' not in st.session_state:
    st.session_state.auth = False

# --- ACCESO ---
if not st.session_state.auth:
    st.title("🚑 Acceso Operativo ORH")
    if st.text_input("Credencial", type="password") == "ORH2026":
        st.session_state.auth = True
        st.rerun()
    st.stop()

# --- INTERFAZ ---
st.sidebar.title("SISTEMA ORH")
st.sidebar.info(f"{LEMA}\n\nID: {FIRMA}")

tabs = st.tabs(["💬 Consultor IA", "🩺 MARCH", "📄 Informe"])

with tabs[0]:
    st.subheader("Asesoría Médica (Gemini 2.5 Flash)")
    if "chat" not in st.session_state: st.session_state.chat = []
    
    for m in st.session_state.chat:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if q := st.chat_input("Consulta operativa..."):
        st.session_state.chat.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        
        with st.chat_message("assistant"):
            try:
                # Instrucción de sistema integrada en la llamada (Nueva SDK)
                response = client.models.generate_content(
                    model=MODELO_ACTUAL,
                    contents=f"Actúa como Asesor Táctico AME (ORH). Protocolos PHTLS/TCCC. Al final genera este JSON: UPDATE_DATA: {{'march': {{'M': '...', 'A': '...', 'R': '...', 'C': '...', 'H': '...'}}}}. CONSULTA: {q}"
                )
                res_text = response.text
                
                # Lógica de autollenado MARCH
                match = re.search(r"UPDATE_DATA:\s*(\{.*\})", res_text, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1).replace("'", '"'))
                        for k in "MARCH":
                            if data["march"].get(k) and data["march"][k] != "...":
                                st.session_state.march[k] = data["march"][k]
                        st.toast("✅ MARCH actualizado")
                    except: pass
                
                clean_txt = re.sub(r"UPDATE_DATA:.*", "", res_text, flags=re.DOTALL)
                st.markdown(clean_txt)
                st.session_state.chat.append({"role": "assistant", "content": clean_txt})
            except Exception as e:
                st.error(f"⚠️ Error: {e}")

with tabs[1]:
    st.subheader("Protocolo MARCH")
    cols = st.columns(5)
    for i, k in enumerate("MARCH"):
        st.session_state.march[k] = cols[i].text_input(k, st.session_state.march[k])

with tabs[2]:
    st.subheader("Informe Final")
    reporte = f"REPORTE ORH - {FIRMA}\nFECHA: {datetime.now()}\n\nMARCH: {st.session_state.march}\n\n{LEMA}"
    st.text_area("Vista Previa", reporte, height=200)
    if st.button("Descargar PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 10, reporte)
        st.download_button("Guardar", data=bytes(pdf.output()), file_name="Reporte_ORH.pdf")
