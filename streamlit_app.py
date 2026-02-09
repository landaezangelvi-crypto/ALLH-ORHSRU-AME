import streamlit as st
from google import genai  # Nueva SDK unificada 2026
from fpdf import FPDF
import json, re
from datetime import datetime

# --- IDENTIDAD ---
FIRMA = "ALLH-ORH:2026"
LEMA = '"No solo es querer salvar, sino saber salvar" Organización Rescate Humboldt.'

# --- CONFIGURACIÓN DE IA ---
# Definimos el cliente globalmente para evitar errores de "not defined"
client = None
if "GENAI_API_KEY" in st.secrets:
    try:
        # La nueva forma de conectar en 2026
        client = genai.Client(api_key=st.secrets["GENAI_API_KEY"])
        MODELO_ACTUAL = "gemini-2.5-flash" 
    except Exception as e:
        st.error(f"Error de conexión con la IA: {e}")
else:
    st.warning("🚨 Falta la clave GENAI_API_KEY en los Secrets de Streamlit.")

# --- INICIALIZACIÓN DE DATOS ---
if 'march' not in st.session_state:
    st.session_state.march = {k: "" for k in "MARCH"}

# --- INTERFAZ ---
st.set_page_config(page_title="ORH AME 2026", layout="wide", page_icon="🚑")

st.sidebar.title("SISTEMA ORH")
st.sidebar.info(f"{LEMA}\n\nID: {FIRMA}")

tabs = st.tabs(["💬 Consultor IA", "🩺 MARCH", "📄 Informe"])

with tabs[0]:
    st.subheader("Asesoría Médica Táctica")
    if "chat" not in st.session_state: st.session_state.chat = []
    
    for m in st.session_state.chat:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if q := st.chat_input("Describa la situación..."):
        st.session_state.chat.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        
        with st.chat_message("assistant"):
            if client:
                try:
                    # En la nueva SDK, el prompt de sistema se envía en la llamada
                    sys_instr = "Actúa como Asesor AME ORH. Usa protocolos TCCC. Al final añade: UPDATE_DATA: {'march': {'M': '...', 'A': '...', 'R': '...', 'C': '...', 'H': '...'}}"
                    
                    response = client.models.generate_content(
                        model=MODELO_ACTUAL,
                        contents=f"{sys_instr}\n\nConsulta: {q}"
                    )
                    
                    full_text = response.text
                    
                    # Lógica de autollenado para la pestaña MARCH
                    match = re.search(r"UPDATE_DATA:\s*(\{.*\})", full_text, re.DOTALL)
                    if match:
                        try:
                            # Limpieza de comillas simples para JSON válido
                            json_str = match.group(1).replace("'", '"')
                            data = json.loads(json_str)
                            for k in "MARCH":
                                if data["march"].get(k) and data["march"][k] != "...":
                                    st.session_state.march[k] = data["march"][k]
                            st.toast("✅ Protocolo MARCH actualizado")
                        except: pass
                    
                    # Mostrar solo la respuesta médica limpia
                    clean_res = re.sub(r"UPDATE_DATA:.*", "", full_text, flags=re.DOTALL)
                    st.markdown(clean_res)
                    st.session_state.chat.append({"role": "assistant", "content": clean_res})
                except Exception as e:
                    st.error(f"Error técnico: {e}")
            else:
                st.error("IA no configurada. Verifique su API Key.")

with tabs[1]:
    st.subheader("Protocolo MARCH")
        cols = st.columns(5)
    for i, k in enumerate("MARCH"):
        st.session_state.march[k] = cols[i].text_input(k, st.session_state.march[k])

with tabs[2]:
    st.subheader("Generación de Informe")
    reporte = f"REPORTE AME - ORH\nFECHA: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\nRESULTADOS MARCH:\n"
    for k, v in st.session_state.march.items():
        reporte += f"- {k}: {v}\n"
    reporte += f"\n{LEMA}\nID: {FIRMA}"
    
    st.text_area("Vista Previa", reporte, height=200)
    if st.button("Guardar en PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 10, reporte.encode('latin-1', 'replace').decode('latin-1'))
        st.download_button("Descargar", data=bytes(pdf.output()), file_name="Reporte_AME_ORH.pdf")
