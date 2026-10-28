"""API credentials sidebar, based on the course module
https://github.com/stoneman-mls/openai_credentials

Changes from the original module:
- the key input is masked (type="password");
- the key is no longer printed on the page;
- the session state is set up inside the function, so it works for every user session;
- the module is wrapped in get_openai_client() so home.py can use it;
- select_model() lists the chat models this key can use (no tokens are spent).

Never put your own API key in this repository.
"""

import re

import streamlit as st
from openai import OpenAI

DEFAULT_MODEL = "gpt-4o"   # the model the test cases were checked with

# Models that are not chat models, or do not work with this app's JSON prompts.
EXCLUDED_WORDS = ("embedding", "tts", "whisper", "dall-e", "audio", "realtime", "transcribe",
                  "image", "search", "moderation", "instruct", "codex", "computer-use",
                  "gpt-3.5", "o1-mini", "o1-preview")
SNAPSHOT_DATE = re.compile(r"-\d{4}-\d{2}-\d{2}$")   # e.g. gpt-4o-2024-08-06


def render_sidebar():
    st.sidebar.title("API Key Input")
    api_key = st.sidebar.text_input("Enter your API key:", type="password", key="api_key_input")
    update_button = st.sidebar.button("Update API Key")
    return api_key, update_button


def remove_api_key():
    """Log out: forget the key, clear the input box and the model list."""
    st.session_state.openai_api_key = None
    st.session_state.api_key_input = ""
    st.session_state.pop("available_models", None)
    st.session_state.pop("model", None)


def get_openai_client():
    """Show the sidebar and return an OpenAI client, or None if no key is saved yet."""
    if "openai_api_key" not in st.session_state:
        st.session_state.openai_api_key = None

    api_key, update_button = render_sidebar()

    if update_button:
        st.session_state.openai_api_key = api_key
        st.session_state.pop("available_models", None)   # re-check models for the new key

    if st.session_state.openai_api_key:
        st.sidebar.success("API key saved for this session.")
        st.sidebar.button("Remove API key (log out)", on_click=remove_api_key)
        return OpenAI(api_key=st.session_state.openai_api_key)

    st.sidebar.info("Enter your API key and click 'Update API Key'.")
    return None


def is_chat_model(model_id):
    if not re.match(r"^(gpt-|o\d|chatgpt-)", model_id):
        return False
    if model_id == "gpt-4" or model_id.startswith("gpt-4-0"):   # old GPT-4, no JSON mode
        return False
    if SNAPSHOT_DATE.search(model_id):                           # hide dated duplicates
        return False
    return not any(word in model_id for word in EXCLUDED_WORDS)


def select_model(client):
    """Show a model dropdown with the chat models this key can access.

    Listing models is free (it does not use tokens). The list is stored in the
    session so the API is only asked once per key.
    """
    if client is None:
        return DEFAULT_MODEL

    if "available_models" not in st.session_state:
        try:
            ids = sorted(m.id for m in client.models.list() if is_chat_model(m.id))
        except Exception:
            st.sidebar.error("Could not check this API key. Please make sure it is correct.")
            ids = []
        st.session_state.available_models = ids

    models = st.session_state.available_models or [DEFAULT_MODEL]
    if DEFAULT_MODEL in models:   # put the tested model first
        models = [DEFAULT_MODEL] + [m for m in models if m != DEFAULT_MODEL]

    model = st.sidebar.selectbox("Model", models, key="model")
    st.sidebar.caption(
        f"The test cases were checked with {DEFAULT_MODEL}. Other models may give different "
        "results. Reasoning models (o-series, gpt-5) are slower and cost more."
    )
    return model
