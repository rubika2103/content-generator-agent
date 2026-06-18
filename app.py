import os
import streamlit as st
import re
import sys
from pathlib import Path
import requests as req

# Inject API key from Streamlit secrets into environment before importing agent
if 'GROQ_API_KEY' in st.secrets:
    os.environ['GROQ_API_KEY'] = st.secrets['GROQ_API_KEY']

sys.path.insert(0, str(Path(__file__).parent))
from agent import render_poster, render_to_png, get_next_style, extract_file_text, STYLE_NAMES

st.set_page_config(
    page_title="Qualesce Poster Agent",
    layout="centered"
)

st.markdown("""
    <style>
    .block-container { max-width: 700px; }
    .stButton > button { background-color: #e8900a; color: white; font-weight: 700; border: none; }
    .stButton > button:hover { background-color: #c97800; color: white; }
    </style>
""", unsafe_allow_html=True)

st.markdown("## Qualesce Poster Agent")
st.markdown("Generate professional marketing posters powered by AI")
st.divider()

input_mode = st.radio("Input type:", ["Topic / Text", "URL", "Upload File"], horizontal=True)

content = ""

if input_mode == "Topic / Text":
    content = st.text_area(
        "Enter topic or content:",
        height=150,
        placeholder="e.g. How AI is transforming enterprise operations in 2025"
    )

elif input_mode == "URL":
    url = st.text_input("Enter a URL:", placeholder="https://example.com/blog/article")
    if url:
        content = url

elif input_mode == "Upload File":
    uploaded = st.file_uploader("Upload file:", type=["txt", "pdf", "docx", "pptx"])
    if uploaded:
        try:
            content = extract_file_text(uploaded.read(), uploaded.name)
            st.success(f"File loaded: {uploaded.name}")
        except Exception as e:
            st.error(f"Could not read file: {e}")

st.divider()

if st.button("Generate Poster", use_container_width=True):
    if not content:
        st.error("Please enter some content first.")
    else:
        try:
            if input_mode == "URL":
                with st.spinner("Fetching URL content..."):
                    try:
                        resp = req.get(content, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
                        text = re.sub(r"<[^>]+>", " ", resp.text)
                        text = re.sub(r"\s+", " ", text).strip()
                        content = f"URL: {content}\n\nPage content:\n{text[:6000]}"
                    except Exception as e:
                        st.error(f"Could not fetch URL: {e}")
                        st.stop()

            with st.spinner("Generating poster design..."):
                style_num = get_next_style()
                html = render_poster(content, style_num)

            with st.spinner("Rendering image..."):
                png = render_to_png(html)

            style_name = STYLE_NAMES[style_num]
            st.success(f"Poster generated! Style: **{style_name}**")

            st.image(png, use_column_width=True)

            st.download_button(
                label="Download Poster (PNG)",
                data=png,
                file_name="qualesce_poster.png",
                mime="image/png",
                use_container_width=True
            )

        except Exception as e:
            st.error(f"Error: {e}")
