import streamlit as st
import requests
import json
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

st.title('Federal Register Chat Agent')

if 'messages' not in st.session_state:
    st.session_state.messages = []

doc_type = st.selectbox('Filter by document type (optional):', 
                        ['All', 'Executive Order', 'Proposed Rule', 'Rule', 'Notice'])

for message in st.session_state.messages:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

if st.button('Export Chat History'):
    with open('chat_history.json', 'w') as f:
        json.dump(st.session_state.messages, f)
    st.success('Chat history exported to chat_history.json')

with st.form(key='chat_form', clear_on_submit=True):
    query = st.chat_input('Ask about Federal Register documents...', key='chat_input')
    submit_button = st.form_submit_button('Submit')

    if query and submit_button:
        if doc_type != 'All':
            query = f'{query} (type: {doc_type})'
        
        st.session_state.messages.append({'role': 'user', 'content': query})
        with st.chat_message('user'):
            st.markdown(query)
        
        try:
            response = requests.post(f'{os.getenv('API_URL')}/chat', json={'query': query})
            response.raise_for_status()
            result = response.json()['response']
        except requests.RequestException as e:
            logger.error(f'UI API call failed: {str(e)}')
            result = f'Error: Failed to connect to the server. Please try again.'
        
        st.session_state.messages.append({'role': 'assistant', 'content': result})
        with st.chat_message('assistant'):
            st.markdown(result)
