import streamlit as st
from google import genai
from fpdf import FPDF
import json
import re
import os
from datetime import datetime

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="ORH - Asesor AME 2026", layout="wide", page_icon="🚑")

FIRMA = "ALLH-ORH:2026"
LEMA = '"No solo es querer salvar, sino saber salvar" Organización Rescate Humboldt.'
MODELO_ID = "gemini-2.0-flash"

# --- 2. CONFIGURACIÓN DEL SDK (Gemini 2.0) ---
client = None
if "GENAI_API_KEY" in st.secrets:
    try:
        client = genai.Client(api_key=st.secrets["GENAI_API_KEY"])
    except Exception as e:
        st.error(f"Error de conexión SDK: {e}")
else:
    st.error("⚠️ Falta GENAI_API_KEY en Secrets.")

# --- 3. INSTRUCCIONES DEL SISTEMA ---
SYSTEM_INSTRUCTION = f"""
Actúa como Asesor Táctico AME para la Organización Rescate Humboldt. Propiedad: {FIRMA}.
Protocolos: PHTLS 10, TCCC y ATLS. 
Al final de cada respuesta, incluye SIEMPRE:
UPDATE_DATA: {{"march": {{"M": "...", "A": "...", "R": "...", "C": "...", "H": "..."}}}}
"""

# --- 4. GESTIÓN DE SESIÓN ---
if 'march' not in st.session_state:
    st.session_state.march = {k: "" for k in "MARCH"}
if 'auth' not in st.session_state:
    st.session_state.auth = False
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# --- 5. CONTROL DE ACCESO ---
if not st.session_state.auth:
    st.title("🚑 Acceso Operativo AME - ORH")
    with st.form("login"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.form_submit_button("INGRESAR"):
            if u == "ORH2026" and p == "ORH2026":
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Acceso Denegado")
    st.stop()

# --- 6. INTERFAZ PRINCIPAL (Aquí se definen las pestañas correctamente) ---
st.sidebar.title("SISTEMA ORH")
if os.path.exists("LOGO_ORH57.JPG"):
    st.sidebar.image("LOGO_ORH57.JPG")
st.sidebar.info(f"{LEMA}\n\nID: {FIRMA}")

# DEFINICIÓN DE PESTAÑAS (Esto evita el NameError)
t_reg, t_ia, t_pdf = st.tabs(["📋 Protocolo MARCH", "💬 Consultor IA", "📄 Informe"])

with t_reg:
    st.subheader("Evaluación Primaria")
    c1, c2 = st.columns(2)
    # Usamos los valores de session_state para que la IA pueda escribirlos
    m_val = c1.text_input("M (Hemorragia)", value=st.session_state.march["M"])
    a_val = c1.text_input("A (Vía Aérea)", value=st.session_state.march["A"])
    r_val = c2.text_input("R (Respiración)", value=st.session_state.march["R"])
    c_val = c2.text_input("C (Circulación)", value=st.session_state.march["C"])
    h_val = st.text_input("H (Hipotermia/Cabeza)", value=st.session_state.march["H"])
    
    # Actualizar estado si el usuario escribe manualmente
    if st.button("Guardar Cambios Manuales"):
        st.session_state.march = {"M": m_val, "A": a_val, "R": r_val, "C": c_val, "H": h_val}
        st.success("Datos guardados.")

with t_ia:
    st.subheader("💬 Consultor Táctico (Gemini 2.0)")
    
    # Mostrar historial de chat
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Escriba su consulta o reporte..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            if client:
                try:
                    response = client.models.generate_content(
                        model=MODELO_ID,
                        config={'system_instruction': SYSTEM_INSTRUCTION},
                        contents=prompt
                    )
                    full_res = response.text
                    
                    # Sincronización JSON para autollenado
                    match = re.search(r"UPDATE_DATA:\s*(\{.*\})", full_res, re.DOTALL)
                    if match:
                        try:
                            data = json.loads(match.group(1))
                            if "march" in data:
                                for k in "MARCH":
                                    if data["march"].get(k):
                                        st.session_state.march[k] = data["march"][k]
                                st.rerun() # Recargamos para que se vean los cambios en la pestaña 1
                        except: pass
                    
                    clean_res = re.sub(r"UPDATE_DATA:.*", "", full_res, flags=re.DOTALL)
                    st.markdown(clean_res)
                    st.session_state.chat_history.append({"role": "assistant", "content": clean_res})
                
                except Exception as e:
                    if "429" in str(e):
                        st.error("⏳ Límite excedido. Espere 60 segundos.")
                    else:
                        st.error(f"Fallo de IA: {e}")
            else:
                st.warning("IA no disponible.")

with t_pdf:
    st.subheader("Informe Final")
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    reporte_txt = f"ORGANIZACIÓN RESCATE HUMBOLDT\nFECHA: {fecha}\n\nMARCH:\nM: {st.session_state.march['M']}\nA: {st.session_state.march['A']}\nR: {st.session_state.march['R']}\nC: {st.session_state.march['C']}\nH: {st.session_state.march['H']}\n\n{FIRMA}"
    
    st.text_area("Previsualización", reporte_txt, height=200)
    
    if st.button("Generar PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, reporte_txt.encode('latin-1', 'replace').decode('latin-1'))
        st.download_button("Descargar", data=bytes(pdf.output()), file_name="Reporte_ORH.pdf")
