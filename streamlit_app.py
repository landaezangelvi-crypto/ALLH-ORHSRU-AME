with t_ia:
    st.subheader("💬 Consultor Táctico Gemini 2.0")
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Describa la situación clínica..."):
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
                    full_response = response.text
                    
                    # Sincronización JSON...
                    match = re.search(r"UPDATE_DATA:\s*(\{.*\})", full_response, re.DOTALL)
                    if match:
                        try:
                            data = json.loads(match.group(1))
                            if "march" in data:
                                for k in "MARCH":
                                    if data["march"].get(k):
                                        st.session_state.march[k] = data["march"][k]
                            st.toast("✅ Campos actualizados")
                        except: pass
                    
                    clean_text = re.sub(r"UPDATE_DATA:.*", "", full_text, flags=re.DOTALL)
                    st.markdown(clean_text)
                    st.session_state.chat_history.append({"role": "assistant", "content": clean_text})

                except Exception as e:
                    # --- MANEJO ESPECÍFICO DEL ERROR 429 ---
                    if "429" in str(e):
                        st.error("⏳ **CUPO AGOTADO:** Google ha limitado las peticiones momentáneamente. Por favor, espera 60 segundos antes de volver a consultar.")
                        st.info("Esto sucede por usar el plan gratuito. Si es una emergencia real, considera pasar a un plan de pago en Google AI Studio.")
                    else:
                        st.error(f"Fallo de comunicación: {e}")
            else:
                st.warning("IA desconectada.")
