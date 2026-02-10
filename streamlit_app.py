import streamlit as st
from google import genai
from fpdf import FPDF
import json, re, os
from datetime import datetime
from PIL import Image
import tempfile
import requests

# --- 1. CONFIGURACIÓN E IDENTIDAD ---
st.set_page_config(page_title="ORH - AME Táctico 7.0", layout="wide", page_icon="🚑")

# --- VARIABLES GLOBALES ---
FIRMA = "ALLH-ORH:2026"
LEMA = '"No solo es querer salvar, sino saber salvar"'
COPYRIGHT = "ORGANIZACIÓN RESCATE HUMBOLDT - AME"

# URL del Logo para el PDF (Usamos uno médico genérico o sustitúyelo por la URL del logo ORH)
LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/82/Gnome-medical-emergency.svg/1024px-Gnome-medical-emergency.svg.png"

# --- 2. CONTROL DE ACCESO ---
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🚑 Sistema Táctico AME - ORH")
    c1, c2 = st.columns([1, 2])
    with c1: st.image(LOGO_URL, width=100)
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

# --- 4. INSTRUCCIÓN MAESTRA (PROMPT ACTUALIZADO 2026) ---
SYSTEM_PROMPT = f"""
ACTÚA COMO: Oficial Médico Táctico de la Organización Rescate Humboldt ({FIRMA}).
PROTOCOLOS VIGENTES: PHTLS 10ma Ed, TCCC-MP (2025/26), ATLS, BCLS.

REGLAS DE ORO (SEGURIDAD DEL PACIENTE):
1. EVIDENCIA CIENTÍFICA: NO recomiendes intervenciones (fármacos, torniquetes, descompresión) si el usuario NO ha reportado signos clínicos que lo justifiquen. Si faltan datos vitales, PÍDELOS antes de sugerir tratamiento.
2. FASES DE ATENCIÓN: Estructura tu respuesta mentalmente y en texto así:
   - FASE 1: Cuidados bajo amenaza (Detener sangrado masivo, seguridad).
   - FASE 2: Cuidados en Campo Táctico (MARCH completo, fármacos).
   - FASE 3: Evacuación (TACEVAC).
3. MAPA DE LESIONES: Usa arte ASCII para ubicar heridas si se describen.

SALIDA OCULTA DE DATOS (JSON):
Para que el sistema registre los datos, al final de tu respuesta (y de forma invisible para el reporte narrativo), genera SIEMPRE este JSON:
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
  "farmaco": "...",
  "fase_actual": "..."
}}
"""

# --- 5. GESTIÓN DE MEMORIA Y ESTADO ---
vars_default = {
    "operador": "", "paciente": "", "ubicacion": "", "tipo_incidente": "Terrestre", 
    "hora": datetime.now().strftime('%H:%M'), "farmaco": "", 
    "M":"", "A":"", "R":"", "C":"", "H":"", "fase_actual": "Evaluación Inicial"
}
for k, v in vars_default.items():
    if k not in st.session_state: st.session_state[k] = v

if 'chat' not in st.session_state: st.session_state.chat = []

# --- 6. CLASE PDF PERSONALIZADA (DISEÑO INSTITUCIONAL) ---
class PDFReport(FPDF):
    def header(self):
        # Logo (Descarga temporal para insertar en PDF)
        try:
            self.image(logo_path, 10, 8, 25)
        except: pass # Si falla el logo, sigue sin él
        
        self.set_font('Arial', 'B', 14)
        self.cell(0, 5, 'ORGANIZACIÓN RESCATE HUMBOLDT', 0, 1, 'C')
        self.set_font('Arial', 'B', 10)
        self.cell(0, 5, 'DIVISIÓN DE ATENCIÓN MÉDICA DE EMERGENCIA', 0, 1, 'C')
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, f'REPORTE TÁCTICO - REF: {FIRMA}', 0, 1, 'C')
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'{LEMA} | Pág {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, label):
        self.set_fill_color(200, 220, 255)
        self.set_font('Arial', 'B', 11)
        self.cell(0, 6, f'  {label}', 0, 1, 'L', 1)
        self.ln(4)

    def chapter_body(self, text):
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 5, text)
        self.ln()

# --- 7. INTERFAZ GRÁFICA ---
st.sidebar.title("SISTEMA ORH")
st.sidebar.info(f"**ID:** {FIRMA}\n\n{LEMA}")

# Carga de Logo para PDF (Manejo de temporal)
logo_path = "logo_temp.png"
if not os.path.exists(logo_path):
    try:
        response = requests.get(LOGO_URL)
        with open(logo_path, 'wb') as f:
            f.write(response.content)
    except: pass

# Módulo de Imágenes
st.sidebar.markdown("### 📸 Ojos Tácticos")
foto = st.sidebar.file_uploader("Cargar evidencia", type=['jpg', 'png', 'jpeg'])
img_pil = None
if foto:
    img_pil = Image.open(foto)
    st.sidebar.image(foto, caption="Evidencia", use_container_width=True)

# TABS
tab1, tab2, tab3 = st.tabs(["💬 CENTRO DE MANDO", "📋 FICHA TÉCNICA", "📄 INFORME PDF"])

with tab1:
    st.subheader("Asesoría Táctica por Fases")
    
    for m in st.session_state.chat:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    
    if q := st.chat_input("Reporte situación (Ej: Herida de bala en muslo, consciente, sin torniquete...)"):
        st.session_state.chat.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        
        with st.chat_message("assistant"):
            if client:
                with st.spinner("Triaje y Protocolos PHTLS..."):
                    try:
                        contenido = [SYSTEM_PROMPT, q]
                        if img_pil:
                            contenido.append(img_pil)
                            contenido.append("Usa esta imagen para validar lesiones y llenar el MARCH.")

                        response = client.models.generate_content(model=MODELO, contents=contenido)
                        full_res = response.text
                        
                        # Extracción JSON (Invisible al usuario)
                        match = re.search(r"UPDATE_DATA:\s*(\{.*\})", full_res, re.DOTALL)
                        if match:
                            try:
                                js = json.loads(match.group(1).replace("'", '"'))
                                if "info" in js:
                                    for k, v in js["info"].items():
                                        if v and v != "...": st.session_state[k] = v
                                if "march" in js:
                                    for k, v in js["march"].items():
                                        if v and v != "...": st.session_state[k] = v
                                if "farmaco" in js: st.session_state["farmaco"] = js.get("farmaco", "")
                                st.toast("✅ DATOS REGISTRADOS", icon="📝")
                            except: pass

                        clean_res = re.sub(r"UPDATE_DATA:.*", "", full_res, flags=re.DOTALL)
                        
                        # Formateo visual de la respuesta de la IA
                        st.markdown(clean_res)
                        st.session_state.chat.append({"role": "assistant", "content": clean_res})
                        
                    except Exception as e:
                        st.error(f"Falla de enlace: {e}")

with tab2:
    st.subheader("Ficha Operativa (Autollenado)")
    st.caption("Verifique los datos antes de generar el informe oficial.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.session_state["operador"] = st.text_input("Operador APH", st.session_state["operador"])
        st.session_state["ubicacion"] = st.text_input("Ubicación", st.session_state["ubicacion"])
        idx_tipo = 0
        opts = ["Terrestre", "Aereo", "Nautico"]
        if st.session_state["tipo_incidente"] in opts: idx_tipo = opts.index(st.session_state["tipo_incidente"])
        st.session_state["tipo_incidente"] = st.selectbox("Tipo", opts, index=idx_tipo)
    
    with col2:
        st.session_state["hora"] = st.text_input("Hora", st.session_state["hora"])
        st.session_state["paciente"] = st.text_input("Paciente", st.session_state["paciente"])

    st.markdown("### Protocolo MARCH")
    m1, m2, m3, m4, m5 = st.columns(5)
    st.session_state["M"] = m1.text_area("M (Hemorragia)", st.session_state["M"])
    st.session_state["A"] = m2.text_area("A (Vía Aérea)", st.session_state["A"])
    st.session_state["R"] = m3.text_area("R (Respiración)", st.session_state["R"])
    st.session_state["C"] = m4.text_area("C (Circulación)", st.session_state["C"])
    st.session_state["H"] = m5.text_area("H (Hipotermia)", st.session_state["H"])
    
    st.markdown("### Terapéutica")
    st.session_state["farmaco"] = st.text_area("Fármacos y Procedimientos", st.session_state["farmaco"])

with tab3:
    st.subheader("Expediente Oficial")
    
    if st.button("🖨️ GENERAR INFORME INSTITUCIONAL (PDF)"):
        # Crear PDF con la clase personalizada
        pdf = PDFReport()
        pdf.add_page()
        
        # Bloque 1: Resumen Operativo
        pdf.chapter_title("1. RESUMEN OPERATIVO")
        info_txt = f"Fecha: {datetime.now().strftime('%d/%m/%Y')}\nHora del Suceso: {st.session_state['hora']}\n" \
                   f"Operador Responsable: {st.session_state['operador']}\n" \
                   f"Ubicación: {st.session_state['ubicacion']} ({st.session_state['tipo_incidente']})\n" \
                   f"Paciente: {st.session_state['paciente']}"
        pdf.chapter_body(info_txt.encode('latin-1', 'replace').decode('latin-1'))
        
        # Bloque 2: MARCH
        pdf.chapter_title("2. EVALUACIÓN PRIMARIA (MARCH)")
        march_txt = f"[M] Massive Hemorrhage: {st.session_state['M']}\n" \
                    f"[A] Airway Control: {st.session_state['A']}\n" \
                    f"[R] Respiration: {st.session_state['R']}\n" \
                    f"[C] Circulation: {st.session_state['C']}\n" \
                    f"[H] Hypothermia/Head: {st.session_state['H']}"
        pdf.chapter_body(march_txt.encode('latin-1', 'replace').decode('latin-1'))
        
        # Bloque 3: Tratamiento
        pdf.chapter_title("3. TERAPÉUTICA Y FARMACOLOGÍA")
        pdf.chapter_body(st.session_state['farmaco'].encode('latin-1', 'replace').decode('latin-1'))
        
        # Bloque 4: Notas Legales
        pdf.ln(10)
        pdf.set_font('Arial', 'B', 8)
        pdf.multi_cell(0, 4, f"NOTA: Este documento es un registro de campo generado bajo protocolos PHTLS/TCCC. "
                             f"La información clínica es responsabilidad del operador {st.session_state['operador']}. "
                             f"{COPYRIGHT}")
        
        st.success("Documento generado exitosamente.")
        st.download_button("⬇️ DESCARGAR PDF OFICIAL", data=bytes(pdf.output()), file_name=f"ORH_EXP_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf")
