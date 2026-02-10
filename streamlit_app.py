import streamlit as st
from google import genai
from fpdf import FPDF
import json, re
from datetime import datetime
from PIL import Image

# --- 1. CONFIGURACIÓN E IDENTIDAD ---
st.set_page_config(page_title="ORH - AME Táctico 6.0", layout="wide", page_icon="🚑")
FIRMA = "ALLH-ORH:2026"
LEMA = '"No solo es querer salvar, sino saber salvar" Organización Rescate Humboldt.'

# --- 2. CONTROL DE ACCESO ---
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🚑 Sistema Táctico AME - ORH")
    c1, c2 = st.columns([1, 2])
    with c1: st.image("https://upload.wikimedia.org/wikipedia/commons/8/82/Gnome-medical-emergency.svg", width=120)
    with c2:
        with st.form("login"):
            st.markdown("### Credenciales Operativas")
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("ACCEDER AL SISTEMA"):
                if u == "ORH2026" and p == "ORH2026":
                    st.session_state.auth = True
                    st.rerun()
                else: st.error("Acceso no autorizado.")
    st.stop()

# --- 3. CONEXIÓN NEURONAL (IA) ---
client = None
if "GENAI_API_KEY" in st.secrets:
    try:
        client = genai.Client(api_key=st.secrets["GENAI_API_KEY"])
        MODELO = "gemini-2.5-flash"
    except Exception as e: st.error(f"Error IA: {e}")

# --- 4. INSTRUCCIÓN MAESTRA (PROMPT) ---
# Aquí definimos que la IA extraiga ABSOLUTAMENTE TODO
SYSTEM_PROMPT = f"""
ROL: Asesor Táctico AME - Organización Rescate Humboldt ({FIRMA}).
OBJETIVO: Analizar texto e imágenes para llenar automáticamente el reporte operativo.

INSTRUCCIONES CLÍNICAS (PHTLS/TCCC):
1. Analiza riesgos del entorno (Geografía, Clima, Fauna).
2. Genera mapa ASCII del cuerpo marcando lesiones con (X).
3. Recomienda farmacología con DOSIS y VIA.

SALIDA DE DATOS OBLIGATORIA (JSON):
Al final de tu respuesta, genera SIEMPRE este bloque JSON con los datos que logres identificar. Si no tienes un dato, intuyelo o pon "...":
UPDATE_DATA: {{
  "info": {{
    "operador": "...",
    "paciente": "...",
    "ubicacion": "...",
    "tipo_incidente": "Terrestre/Aereo/Nautico",
    "hora": "..."
  }},
  "march": {{
    "M": "...", "A": "...", "R": "...", "C": "...", "H": "..."
  }},
  "farmaco": "..."
}}
"""

# --- 5. GESTIÓN DE MEMORIA (SESSION STATE) ---
# Inicializamos todas las variables para que los campos de texto las lean
vars_default = {
    "operador": "", "paciente": "", "ubicacion": "", "tipo_incidente": "Terrestre", 
    "hora": datetime.now().strftime('%H:%M'), "farmaco": "", "M":"", "A":"", "R":"", "C":"", "H":""
}
for k, v in vars_default.items():
    if k not in st.session_state: st.session_state[k] = v

if 'chat' not in st.session_state: st.session_state.chat = []

# --- 6. INTERFAZ GRÁFICA ---
st.sidebar.title("SISTEMA ORH")
st.sidebar.info(f"**ID:** {FIRMA}\n\n{LEMA}")

# Módulo de Carga de Imágenes (SIDEBAR para acceso rápido)
st.sidebar.markdown("### 📸 Ojos Tácticos")
foto = st.sidebar.file_uploader("Cargar evidencia", type=['jpg', 'png', 'jpeg'])
img_pil = None
if foto:
    img_pil = Image.open(foto)
    st.sidebar.image(foto, caption="Imagen cargada en memoria", use_container_width=True)

# TABS PRINCIPALES
tab1, tab2, tab3 = st.tabs(["💬 CENTRO DE MANDO (IA)", "📋 FICHA TÉCNICA (AUTO)", "📄 INFORME PDF"])

with tab1:
    st.subheader("Interacción Táctica & Diagnóstico")
    
    # Historial
    for m in st.session_state.chat:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    
    # Input de Chat
    if q := st.chat_input("Reporte situación (Ej: Paciente 30 años, caída en el Ávila, fractura expuesta fémur...)"):
        st.session_state.chat.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        
        with st.chat_message("assistant"):
            if client:
                with st.spinner("Analizando telemetría y protocolos..."):
                    try:
                        # Preparamos el contenido (Texto + Imagen si existe)
                        contenido = [SYSTEM_PROMPT, q]
                        if img_pil:
                            contenido.append(img_pil) # Enviamos la foto a la IA
                            contenido.append("Analiza también esta imagen para llenar el MARCH.")

                        response = client.models.generate_content(model=MODELO, contents=contenido)
                        full_res = response.text
                        
                        # --- MOTOR DE AUTOLLENADO ---
                        match = re.search(r"UPDATE_DATA:\s*(\{.*\})", full_res, re.DOTALL)
                        if match:
                            try:
                                js = json.loads(match.group(1).replace("'", '"'))
                                
                                # 1. Llenar Info General
                                if "info" in js:
                                    for k, v in js["info"].items():
                                        if v and v != "...": st.session_state[k] = v
                                
                                # 2. Llenar MARCH
                                if "march" in js:
                                    for k, v in js["march"].items():
                                        if v and v != "...": st.session_state[k] = v
                                        
                                # 3. Farmacología
                                if "farmaco" in js:
                                    st.session_state["farmaco"] = js.get("farmaco", "")
                                    
                                st.toast("✅ TODOS LOS CAMPOS SINCRONIZADOS", icon="🔄")
                                # Forzamos recarga para que los inputs se vean llenos
                                # st.rerun()  <-- Descomentar si quieres recarga instantánea (puede cortar la animación del chat)
                            except Exception as e:
                                print(f"Error JSON: {e}")

                        # Limpieza y visualización
                        clean_res = re.sub(r"UPDATE_DATA:.*", "", full_res, flags=re.DOTALL)
                        st.markdown(clean_res)
                        st.session_state.chat.append({"role": "assistant", "content": clean_res})
                        
                    except Exception as e:
                        st.error(f"Falla en enlace satelital (Error API): {e}")

with tab2:
    st.subheader("Datos de Operación (Autollenado)")
    st.info("Estos campos se llenan solos conversando con la IA o subiendo fotos.")
    
    # Sección 1: Datos Logísticos
    c1, c2, c3 = st.columns(3)
    st.session_state["operador"] = c1.text_input("Operador APH", st.session_state["operador"])
    st.session_state["ubicacion"] = c2.text_input("Ubicación Geográfica", st.session_state["ubicacion"])
    st.session_state["hora"] = c3.text_input("Hora Incidente", st.session_state["hora"])
    
    c4, c5 = st.columns([2, 1])
    st.session_state["paciente"] = c4.text_input("Datos Paciente", st.session_state["paciente"])
    st.session_state["tipo_incidente"] = c5.selectbox("Tipo Incidente", ["Terrestre", "Aereo", "Nautico"], index=["Terrestre", "Aereo", "Nautico"].index(st.session_state["tipo_incidente"]) if st.session_state["tipo_incidente"] in ["Terrestre", "Aereo", "Nautico"] else 0)

    st.markdown("---")
    st.subheader("Evaluación Primaria (MARCH)")
    
    # Sección 2: Protocolo MARCH (Diseño Táctico)
    col_m, col_a, col_r, col_c, col_h = st.columns(5)
    st.session_state["M"] = col_m.text_area("M (Hemorragia)", st.session_state["M"], height=100)
    st.session_state["A"] = col_a.text_area("A (Vía Aérea)", st.session_state["A"], height=100)
    st.session_state["R"] = col_r.text_area("R (Respiración)", st.session_state["R"], height=100)
    st.session_state["C"] = col_c.text_area("C (Circulación)", st.session_state["C"], height=100)
    st.session_state["H"] = col_h.text_area("H (Hipotermia)", st.session_state["H"], height=100)

    st.markdown("---")
    st.subheader("Farmacología y Notas")
    st.session_state["farmaco"] = st.text_area("Indicaciones Terapéuticas", st.session_state["farmaco"])

with tab3:
    st.subheader("Informe Final")
    
    
    
    # Generación de Texto para PDF
    reporte_final = f"""
    {COPYRIGHT}
    ----------------------------------------------------------
    REPORTE DE INCIDENTE: {FIRMA}
    FECHA: {datetime.now().strftime('%d/%m/%Y')} | HORA: {st.session_state['hora']}
    
    DATOS OPERATIVOS:
    - Operador: {st.session_state['operador']}
    - Ubicación: {st.session_state['ubicacion']}
    - Tipo: {st.session_state['tipo_incidente']}
    - Paciente: {st.session_state['paciente']}
    
    PROTOCOLO MARCH:
    [M] {st.session_state['M']}
    [A] {st.session_state['A']}
    [R] {st.session_state['R']}
    [C] {st.session_state['C']}
    [H] {st.session_state['H']}
    
    FARMACOLOGÍA / NOTAS:
    {st.session_state['farmaco']}
    ----------------------------------------------------------
    {LEMA}
    """
    
    st.text_area("Vista Previa del Documento", reporte_final, height=300)
    
    if st.button("📥 DESCARGAR EXPEDIENTE PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=10)
        # Saneamiento básico de texto para FPDF (latin-1)
        texto_pdf = reporte_final.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 5, texto_pdf)
        st.download_button("Guardar PDF", data=bytes(pdf.output()), file_name=f"ORH_CASO_{datetime.now().strftime('%H%M')}.pdf")
