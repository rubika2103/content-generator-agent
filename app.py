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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stMarkdown, .stText, label, p, div {
    font-family: 'Inter', sans-serif !important;
}

.block-container {
    padding: 0 2rem 2rem 2rem !important;
    max-width: 1400px;
}

.stButton > button {
    background: linear-gradient(135deg, #e8900a, #c97800) !important;
    color: white !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 12px 20px !important;
    box-shadow: 0 4px 12px rgba(232,144,10,0.3) !important;
    transition: all 0.2s !important;
    width: 100%;
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
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    border: none !important;
    box-shadow: 0 4px 12px rgba(13,42,61,0.2) !important;
    width: 100%;
}

.stRadio > div { gap: 10px; }

.stTextArea textarea, .stTextInput input {
    font-family: 'Inter', sans-serif !important;
    border-radius: 8px !important;
    border: 1px solid #e2eaf0 !important;
}

.preview-placeholder {
    background: #f8fafc;
    border: 2px dashed #cbd5e1;
    border-radius: 14px;
    height: 480px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #94a3b8;
    font-size: 14px;
    font-weight: 500;
    font-family: 'Inter', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if 'poster_png' not in st.session_state:
    st.session_state.poster_png = None
if 'poster_style' not in st.session_state:
    st.session_state.poster_style = None
if 'extracted_content' not in st.session_state:
    st.session_state.extracted_content = None

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(135deg,#0d2a3d 0%,#005a8c 100%);
            border-radius:14px;padding:28px 36px;margin:20px 0 28px 0">
    <div style="font-family:'Inter',sans-serif;font-size:26px;font-weight:800;
                color:#ffffff;margin-bottom:6px">Qualesce Poster Agent</div>
    <div style="font-family:'Inter',sans-serif;font-size:14px;
                color:rgba(255,255,255,0.65)">Generate professional marketing posters powered by AI</div>
</div>
""", unsafe_allow_html=True)

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
    st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)

    input_mode = st.radio("Input type", ["Topic / Text", "URL", "Upload File"],
                          horizontal=True, label_visibility="collapsed")
    st.markdown("<div style='margin-bottom:12px'></div>", unsafe_allow_html=True)

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

    st.markdown("<div style='margin-bottom:20px'></div>", unsafe_allow_html=True)

    btn1, btn2 = st.columns(2, gap="medium")
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
    st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)

    if st.session_state.poster_png:
        style_name = STYLE_NAMES[st.session_state.poster_style]
        st.markdown(
            f'<div style="display:inline-block;background:linear-gradient(135deg,#0096b4,#005a8c);'
            f'color:white;padding:6px 16px;border-radius:20px;font-size:12px;font-weight:600;'
            f'font-family:Inter,sans-serif;margin-bottom:12px">Style: {style_name}</div>',
            unsafe_allow_html=True
        )
        st.image(st.session_state.poster_png, use_column_width=True)
        st.markdown("<div style='margin-bottom:12px'></div>", unsafe_allow_html=True)
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
            <div style="font-size:44px;margin-bottom:14px">🖼️</div>
            <div style="font-weight:600;color:#64748b">Your poster will appear here</div>
            <div style="font-size:12px;margin-top:6px;color:#94a3b8">
                Enter content and click Generate
            </div>
        </div>
        """, unsafe_allow_html=True)
