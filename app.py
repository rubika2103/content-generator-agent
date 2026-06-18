import os
import sys
import subprocess
import streamlit as st
import re
from pathlib import Path
import requests as req

@st.cache_resource
def install_playwright():
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"],
                   capture_output=True)

install_playwright()

# Inject API key from Streamlit secrets into environment before importing agent
try:
    key = st.secrets.get('GROQ_API_KEY', '')
    if key:
        os.environ['GROQ_API_KEY'] = key
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).parent))
from agent import render_poster, render_to_png, get_next_style, extract_content, extract_file_text, STYLE_NAMES, TEMPLATES

st.set_page_config(page_title="Qualesce Poster Agent", layout="centered")

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

# Session state
if 'poster_png' not in st.session_state:
    st.session_state.poster_png = None
if 'poster_style' not in st.session_state:
    st.session_state.poster_style = None
if 'extracted_content' not in st.session_state:
    st.session_state.extracted_content = None

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

def generate_poster(content, style_num=None):
    api_key = os.environ.get('GROQ_API_KEY', '')
    if not api_key:
        st.error("GROQ_API_KEY is missing. Add it in Manage app → Settings → Secrets.")
        st.stop()

    with st.spinner("Generating poster content..."):
        try:
            extracted = extract_content(content)
            st.session_state.extracted_content = extracted
        except Exception as e:
            st.error(f"Content generation failed: {e}")
            st.stop()

    if style_num is None:
        style_num = get_next_style()

    with st.spinner("Rendering poster image..."):
        try:
            html = TEMPLATES[style_num % len(TEMPLATES)](extracted)
            png = render_to_png(html)
            st.session_state.poster_png = png
            st.session_state.poster_style = style_num
        except Exception as e:
            st.error(f"Render failed: {e}")
            st.stop()

col1, col2 = st.columns(2)

with col1:
    if st.button("Generate Poster", use_container_width=True):
        if not content:
            st.error("Please enter some content first.")
        else:
            if input_mode == "URL":
                with st.spinner("Fetching URL..."):
                    try:
                        resp = req.get(content, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
                        text = re.sub(r"<[^>]+>", " ", resp.text)
                        text = re.sub(r"\s+", " ", text).strip()
                        content = f"URL: {content}\n\nPage content:\n{text[:6000]}"
                    except Exception as e:
                        st.error(f"Could not fetch URL: {e}")
                        st.stop()
            generate_poster(content)

with col2:
    if st.button("Try Another Style", use_container_width=True,
                 disabled=st.session_state.extracted_content is None):
        if st.session_state.extracted_content:
            new_style = get_next_style()
            with st.spinner("Trying new style..."):
                try:
                    extracted = st.session_state.extracted_content
                    html = TEMPLATES[new_style % len(TEMPLATES)](extracted)
                    png = render_to_png(html)
                    st.session_state.poster_png = png
                    st.session_state.poster_style = new_style
                except Exception as e:
                    st.error(f"Render failed: {e}")

if st.session_state.poster_png:
    style_name = STYLE_NAMES[st.session_state.poster_style]
    st.success(f"Style: **{style_name}**")
    st.image(st.session_state.poster_png, use_column_width=True)
    st.download_button(
        label="Download Poster (PNG)",
        data=st.session_state.poster_png,
        file_name="qualesce_poster.png",
        mime="image/png",
        use_container_width=True
    )
