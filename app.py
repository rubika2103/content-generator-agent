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

try:
    key = st.secrets.get('GROQ_API_KEY', '')
    if key:
        os.environ['GROQ_API_KEY'] = key
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).parent))
from agent import render_to_png, get_next_style, extract_content, extract_file_text, STYLE_NAMES, TEMPLATES

st.set_page_config(page_title="Qualesce Poster Agent", layout="centered", page_icon="🎨")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.block-container {
    max-width: 780px;
    padding-top: 2rem;
}

/* Header */
.hero-header {
    background: linear-gradient(135deg, #0d2a3d 0%, #005a8c 100%);
    border-radius: 16px;
    padding: 36px 40px;
    margin-bottom: 28px;
    text-align: center;
}
.hero-header h1 {
    color: #ffffff;
    font-size: 32px;
    font-weight: 800;
    margin: 0 0 8px 0;
    letter-spacing: -0.5px;
}
.hero-header p {
    color: rgba(255,255,255,0.7);
    font-size: 15px;
    margin: 0;
}
.hero-badge {
    display: inline-block;
    background: #e8900a;
    color: white;
    font-size: 11px;
    font-weight: 700;
    padding: 4px 12px;
    border-radius: 20px;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 14px;
}

/* Input card */
.input-card {
    background: #f8fafc;
    border: 1px solid #e2eaf0;
    border-radius: 14px;
    padding: 28px;
    margin-bottom: 20px;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #e8900a, #c97800) !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 15px !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 12px 24px !important;
    transition: all 0.2s !important;
    box-shadow: 0 4px 12px rgba(232,144,10,0.3) !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 16px rgba(232,144,10,0.4) !important;
}
.stButton > button:disabled {
    background: #e2eaf0 !important;
    color: #94a3b8 !important;
    box-shadow: none !important;
    transform: none !important;
}

/* Style badge */
.style-badge {
    background: linear-gradient(135deg, #0096b4, #005a8c);
    color: white;
    padding: 8px 20px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
    display: inline-block;
    margin-bottom: 16px;
}

/* Result card */
.result-card {
    background: #f8fafc;
    border: 1px solid #e2eaf0;
    border-radius: 14px;
    padding: 24px;
    margin-top: 20px;
}

/* Radio buttons */
.stRadio > div {
    gap: 12px;
}
.stRadio > div > label {
    background: white;
    border: 1px solid #e2eaf0;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    cursor: pointer;
}

/* Download button */
.stDownloadButton > button {
    background: linear-gradient(135deg, #0d2a3d, #005a8c) !important;
    color: white !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    border: none !important;
    box-shadow: 0 4px 12px rgba(13,42,61,0.2) !important;
}

/* Success message */
.stSuccess {
    border-radius: 10px !important;
}

/* Divider */
hr {
    border-color: #e2eaf0;
    margin: 24px 0;
}
</style>
""", unsafe_allow_html=True)

# ── Header ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-header">
    <div class="hero-badge">AI Powered</div>
    <h1>Qualesce Poster Agent</h1>
    <p>Generate stunning professional marketing posters in seconds</p>
</div>
""", unsafe_allow_html=True)

# ── Session state ────────────────────────────────────────────────────────────
if 'poster_png' not in st.session_state:
    st.session_state.poster_png = None
if 'poster_style' not in st.session_state:
    st.session_state.poster_style = None
if 'extracted_content' not in st.session_state:
    st.session_state.extracted_content = None

# ── Input section ────────────────────────────────────────────────────────────
st.markdown("#### Select Input Type")
input_mode = st.radio("", ["Topic / Text", "URL", "Upload File"], horizontal=True, label_visibility="collapsed")

content = ""

if input_mode == "Topic / Text":
    content = st.text_area(
        "Enter your topic or blog content",
        height=140,
        placeholder="e.g. How AI is transforming enterprise operations in 2025..."
    )

elif input_mode == "URL":
    url = st.text_input("Enter a URL", placeholder="https://example.com/blog/article")
    if url:
        content = url

elif input_mode == "Upload File":
    uploaded = st.file_uploader("Upload a file", type=["txt", "pdf", "docx", "pptx"])
    if uploaded:
        try:
            content = extract_file_text(uploaded.read(), uploaded.name)
            st.success(f"✓ File loaded: {uploaded.name}")
        except Exception as e:
            st.error(f"Could not read file: {e}")

st.markdown("<br>", unsafe_allow_html=True)

# ── Generate function ────────────────────────────────────────────────────────
def generate_poster(content, reuse_content=False):
    api_key = os.environ.get('GROQ_API_KEY', '')
    if not api_key:
        st.error("GROQ_API_KEY is missing. Go to Manage app → Settings → Secrets.")
        st.stop()

    if not reuse_content:
        with st.spinner("Generating poster content with AI..."):
            try:
                extracted = extract_content(content)
                st.session_state.extracted_content = extracted
            except Exception as e:
                st.error(f"Content generation failed: {e}")
                st.stop()
    else:
        extracted = st.session_state.extracted_content

    style_num = get_next_style()
    with st.spinner("Rendering poster..."):
        try:
            html = TEMPLATES[style_num % len(TEMPLATES)](extracted)
            png = render_to_png(html)
            st.session_state.poster_png = png
            st.session_state.poster_style = style_num
        except Exception as e:
            st.error(f"Render failed: {e}")
            st.stop()

# ── Buttons ──────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 1])

with col1:
    if st.button("Generate Poster", use_container_width=True):
        if not content:
            st.error("Please enter some content first.")
        else:
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
            generate_poster(content, reuse_content=False)

with col2:
    if st.button("Try Another Style", use_container_width=True,
                 disabled=st.session_state.extracted_content is None):
        generate_poster(None, reuse_content=True)

# ── Result ───────────────────────────────────────────────────────────────────
if st.session_state.poster_png:
    st.markdown("---")
    style_name = STYLE_NAMES[st.session_state.poster_style]
    st.markdown(f'<div class="style-badge">Style: {style_name}</div>', unsafe_allow_html=True)
    st.image(st.session_state.poster_png, use_column_width=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(
        label="Download Poster (PNG)",
        data=st.session_state.poster_png,
        file_name="qualesce_poster.png",
        mime="image/png",
        use_container_width=True
    )
