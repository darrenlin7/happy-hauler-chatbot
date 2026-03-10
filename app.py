"""
app.py — Entry point for the Happy Hauler recruiting chatbot.

Run with:
    streamlit run app.py

Defines the two pages and their sidebar labels via st.navigation.
All chat logic lives in chat_page.py; past sessions in pages/Past_Chats.py.
"""

import streamlit as st

st.set_page_config(
    page_title="Happy Hauler — Recruiting Assistant",
    page_icon="🚛",
    layout="centered",
)

pg = st.navigation([
    st.Page("chat_page.py", title="Chat", icon="💬"),
    st.Page("pages/Past_Chats.py", title="Past Chats", icon="📋"),
])

pg.run()
