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

st.set_page_config(page_title="Qualesce Poster Agent", layout="wide", page_icon="🎨")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.block-container { padding: 2rem 2rem 2rem 2rem; max-width: 1400px; }

.hero-header {
    background: linear-gradient(135deg, #0d2a3d 0%, #005a8c 100%);
    border-radius: 14px;
    padding: 28px 36px;
    margin-bottom: 28px;
}
.hero-header h1 { color: #ffffff; font-size: 26px; font-weight: 800; margin: 0 0 6px 0; }
.hero-header p  { color: rgba(255,255,255,0.65); font-size: 14px; margin: 0; }

.stButton > button {
    background: linear-gradient(135deg, #e8900a, #c97800) !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 11px 20px !important;
    box-shadow: 0 4px 12px rgba(232,144,10,0.3) !important;
    transition: all 0.2s !important;
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

.stDownloadButton > button {
    background: linear-gradient(135deg, #0d2a3d, #005a8c) !important;
    color: white !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    border: none !important;
    box-shadow: 0 4px 12px rgba(13,42,61,0.2) !important;
}

.preview-placeholder {
    background: #f1f5f9;
    border: 2px dashed #cbd5e1;
    border-radius: 14px;
    height: 500px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #94a3b8;
    font-size: 15px;
    font-weight: 500;
}

.style-badge {
    background: linear-gradient(135deg, #0096b4, #005a8c);
    color: white;
    padding: 6px 16px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    display: inline-block;
    margin-bottom: 12px;
}

section[data-testid="stSidebar"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-header">
    <h1>Qualesce Poster Agent</h1>
    <p>Generate professional marketing posters powered by AI</p>
</div>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if 'poster_png' not in st.session_state:
    st.session_state.poster_png = None
if 'poster_style' not in st.session_state:
    st.session_state.poster_style = None
if 'extracted_content' not in st.session_state:
    st.session_state.extracted_content = None

# ── Generate function ─────────────────────────────────────────────────────────
def generate_poster(content, reuse_content=False):
    api_key = os.environ.get('GROQ_API_KEY', '')
    if not api_key:
        st.error("GROQ_API_KEY is missing. Go to Manage app → Settings → Secrets.")
        st.stop()

    if not reuse_content:
        with st.spinner("Generating content with AI..."):
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

# ── Two-column layout ─────────────────────────────────────────────────────────
left, right = st.columns([1, 1], gap="large")

with left:
    st.markdown("#### Input")
    input_mode = st.radio("", ["Topic / Text", "URL", "Upload File"],
                          horizontal=True, label_visibility="collapsed")

    content = ""

    if input_mode == "Topic / Text":
        content = st.text_area(
            "Enter your topic or blog content",
            height=160,
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

    btn1, btn2 = st.columns(2)
    with btn1:
        generate_clicked = st.button("Generate Poster", use_container_width=True)
    with btn2:
        restyle_clicked = st.button("Try Another Style", use_container_width=True,
                                    disabled=st.session_state.extracted_content is None)

    if generate_clicked:
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

    if restyle_clicked:
        generate_poster(None, reuse_content=True)

with right:
    st.markdown("#### Preview")
    if st.session_state.poster_png:
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
    else:
        st.markdown("""
        <div class="preview-placeholder">
            <div style="font-size:48px;margin-bottom:16px">🖼️</div>
            <div>Your poster will appear here</div>
            <div style="font-size:13px;margin-top:6px;color:#b0bec5">Enter content and click Generate</div>
        </div>
        """, unsafe_allow_html=True)
