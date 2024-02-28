import streamlit as st
import requests
import json

def main():
    st.set_page_config(page_title="AssetBot", layout='wide')

    st.header("AssetBot: Tu asistente de mantenimiento y gestión de activos")

    with st.sidebar:
        st.write("## Configuraciones")
        st.info("Ajusta las configuraciones según tus necesidades:")
        verbose_mode = st.checkbox("Modo detallado", value=True)

    chat_container = st.container()

    user_question = st.text_input("Haz una pregunta sobre mantenimiento y gestión de activos:", "")

    if st.button("Obtener respuesta"):
        if user_question:
            with chat_container:
                st.markdown(f"**Tú:** {user_question}")
            with st.spinner("Generando la respuesta..."):
                response = get_response(user_question, verbose_mode)
                if response:
                    with chat_container:
                        st.markdown(response)
                else:
                    st.error("Por favor intenta de nuevo")
        else:
            st.warning("Por favor, ingresa una pregunta.")

def get_response(question, verbose):
    endpoint = "https://iyog3kse4hwpnwwfeoooyjmbji0ajijo.lambda-url.us-east-2.on.aws/"
    headers = {"Content-Type": "application/json"}
    data = {"question": question, "verbose": verbose}

    try:
        response = requests.post(endpoint, headers=headers, json=data)
        if response.status_code == 200:
            response_json = response.json()
            answer_text = response_json.get('answer', '').replace('\n', '  \n')
            answer_text = answer_text.encode('utf-8').decode('unicode_escape')

            formatted_response = f"**AssetBot:**\n\n{answer_text}\n"

            return formatted_response
        else:
            st.error(f"Falla en generar la respuesta: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Una excepción ha ocurrido: {e}")
        return None

if __name__ == "__main__":
    main()