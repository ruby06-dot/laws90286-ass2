"""API credentials sidebar, based on the course module
https://github.com/stoneman-mls/openai_credentials

Changes from the original module:
- the key input is masked (type="password");
- the key is no longer printed on the page;
- the session state is set up inside the function, so it works for every user session;
- the module is wrapped in get_openai_client() so home.py can use it.

Never put your own API key in this repository.
"""

import streamlit as st
from openai import OpenAI


def render_sidebar():
    st.sidebar.title("API Key Input")
    api_key = st.sidebar.text_input("Enter your API key:", type="password")
    update_button = st.sidebar.button("Update API Key")
    return api_key, update_button


def get_openai_client():
    """Show the sidebar and return an OpenAI client, or None if no key is saved yet."""
    if "openai_api_key" not in st.session_state:
        st.session_state.openai_api_key = None

    api_key, update_button = render_sidebar()

    if update_button:
        st.session_state.openai_api_key = api_key

    if st.session_state.openai_api_key:
        st.sidebar.success("API key saved for this session.")
        return OpenAI(api_key=st.session_state.openai_api_key)

    st.sidebar.info("Enter your API key and click 'Update API Key'.")
    return None