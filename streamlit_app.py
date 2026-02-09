import streamlit as st
import google.generativeai as genai  # Usamos la librería estándar para mayor compatibilidad
from fpdf import FPDF
import json
import re
import os
from datetime import datetime

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="ORH - Asesor AME 2026", layout="wide", page_icon="🚑")

FIRMA = "ALLH-ORH:2026"
LEMA = '"No solo es querer salvar, sino saber salvar" Organización Rescate Humboldt.'
# CAMBIO CLAVE: Usamos 1.5 Flash para mayor estabilidad y cuota
MODELO_ID = "gemini-1.5-flash" 

# --- 2. CONFIGURACIÓN DE LA IA ---
if "GENAI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GENAI_API_KEY"])
    model = genai.GenerativeModel(
        model_name=MODELO_ID,
        system_instruction=f"Actúa como Asesor Táctico AME para la Organización Rescate Humboldt. Propiedad: {FIRMA}. Protocolos: PHTLS 10, TCCC. Al final incluye: UPDATE_DATA: {{'march': {{'M': '...', 'A': '...', 'R': '...', 'C': '...', 'H': '...'}}}}"
    )
else:
    st.error("⚠️ Falta GENAI_API_KEY en Secrets.")

# --- 3. GESTIÓN DE SESIÓN ---
if 'march' not in st.session_state:
    st.session_state.march = {k: "" for k in "MARCH"}
if 'auth' not in st.session_state:
    st.session_state.auth = False
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# --- 4. CONTROL DE ACCESO ---
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

# --- 5. INTERFAZ PRINCIPAL ---
st.sidebar.title("SISTEMA ORH")
st.sidebar.info(f"{LEMA}\n\nID: {FIRMA}")

t_reg, t_ia, t_pdf = st.tabs(["📋 Protocolo MARCH", "💬 Consultor IA", "📄 Informe"])

with t_reg:
    st.subheader("Evaluación Primaria")
    # Formulario dinámico sincronizado con la IA
    c1, c2 = st.columns(2)
    m_val = c1.text_input("M (Hemorragia)", value=st.session_state.march["M"])
    a_val = c1.text_input("A (Vía Aérea)", value=st.session_state.march["A"])
    r_val = c2.text_input("R (Respiración)", value=st.session_state.march["R"])
    c_val = c2.text_input("C (Circulación)", value=st.session_state.march["C"])
    h_val = st.text_input("H (Hipotermia/Cabeza)", value=st.session_state.march["H"])
    
    if st.button("Guardar Cambios Manuales"):
        st.session_state.march = {"M": m_val, "A": a_val, "R": r_val, "C": c_val, "H": h_val}
        st.success("Datos guardados.")

with t_ia:
    st.subheader("💬 Consultor Táctico (Gemini 1.5 Estabilidad)")
    
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Escriba su consulta o reporte..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                # Usamos una configuración que ignora bloqueos de seguridad por términos médicos
                response = model.generate_content(
                    prompt,
                    safety_settings={
                        "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
                    }
                )
                full_res = response.text
                
                # Extracción de datos para la pestaña MARCH
                match = re.search(r"UPDATE_DATA:\s*(\{.*\})", full_res, re.DOTALL)
                if match:
                    try:
                        # Reemplazamos comillas simples por dobles para JSON válido
                        json_str = match.group(1).replace("'", '"')
                        data = json.loads(json_str)
                        for k in "MARCH":
                            if data["march"].get(k) and data["march"][k] != "...":
                                st.session_state.march[k] = data["march"][k]
                        st.toast("✅ Datos MARCH actualizados")
                    except: pass
                
                clean_res = re.sub(r"UPDATE_DATA:.*", "", full_res, flags=re.DOTALL)
                st.markdown(clean_res)
                st.session_state.chat_history.append({"role": "assistant", "content": clean_res})
                
            except Exception as e:
                st.error(f"⚠️ El servicio está saturado. Por favor, espere unos segundos. (Error: {e})")

with t_pdf:
    st.subheader("Informe Final")
    reporte_txt = f"ORGANIZACIÓN RESCATE HUMBOLDT\nFECHA: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\nMARCH:\nM: {st.session_state.march['M']}\nA: {st.session_state.march['A']}\nR: {st.session_state.march['R']}\nC: {st.session_state.march['C']}\nH: {st.session_state.march['H']}\n\n{FIRMA}"
    st.text_area("Vista Previa", reporte_txt, height=200)
    
    if st.button("Generar PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, reporte_txt.encode('latin-1', 'replace').decode('latin-1'))
        st.download_button("Descargar", data=bytes(pdf.output()), file_name="Reporte_ORH.pdf")
