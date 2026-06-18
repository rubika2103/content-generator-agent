






now i have the agent which is called poster agent i hosted it with streamlit and i have to connect that agent with maestro 

Yes, you can connect your Streamlit-hosted Poster Agent to UiPath Maestro, but the integration depends on how your Poster Agent is exposed.

Option 1: Best Practice – Expose the Poster Agent as an API
Maestro works best with APIs.

Architecture
UiPath Maestro
      |
      v
Agent Task
      |
      v
HTTP Request
      |
      v
Poster Agent API (FastAPI/Flask)
      |
      v
Generate Poster
      |
      v
Return URL / Image Path
Step 1: Create an API for your Poster Agent
Instead of only Streamlit UI, create a FastAPI endpoint.

Example:

from fastapi import FastAPI

app = FastAPI()

@app.post("/generate-poster")
def generate_poster(topic:str):

    # Call your poster generation logic

    return {
        "status":"success",
        "poster_url":"https://yourserver/posters/poster1.png"
    }
Run:

uvicorn app:app --host 0.0.0.0 --port 8000
Step 2: Test API
Example:

POST https://yourserver/generate-poster

{
   "topic":"AI in Healthcare"
}
Response:

{
  "status":"success",
  "poster_url":"https://yourserver/posters/poster1.png"
}
Step 3: Register Agent in Maestro
In UiPath Maestro Documentation:

Open Maestro.

Create a new Agent Task.

Select External Agent or API-based Agent (depending on your version).

Configure:

Endpoint URL

Authentication

Input Schema

Output Schema

Example Input:

{
   "topic":"string",
   "content":"string"
}
Example Output:

{
   "poster_url":"string",
   "status":"string"
}
Step 4: Use in BPMN
Example Marketing Flow:

Campaign Request
      |
      v
Human Approval
      |
      v
Poster Agent
      |
      v
Generate Poster
      |
      v
Marketing Review
      |
      +-- Approved --> Publish
      |
      +-- Rejected --> Re-generate
Human tasks become User Tasks and Poster generation becomes an Agent Task.

If You Only Have Streamlit
If your application is currently:

https://poster-agent.streamlit.app
and there is no API, Maestro cannot directly interact with it as an agent.

You have two choices:

Add a FastAPI backend (recommended).

Use a UiPath Process to open the Streamlit page and automate it via browser automation.

The recommended approach is:

Poster Agent UI (Streamlit)
          +
Poster Agent API (FastAPI)
          +
UiPath Maestro
Can you tell me:

Is your Poster Agent hosted on Streamlit Community Cloud, VM/VPS, or local machine?

Do you already have a FastAPI/Flask backend, or only a Streamlit URL?

Based on that, I can give the exact Maestro configuration steps.


give any youtube video

For your use case (connecting a custom Poster Agent with UiPath Maestro), these YouTube videos are the most relevant:

1. UiPath Maestro Tutorial | RPA & Agent Deployment from Scratch
▶️ https://www.youtube.com/watch?v=XExl_S_EIAk

Covers:

Creating agents

Connecting agents to Maestro

Deploying to Orchestrator

End-to-end agentic workflow setup 

2. How to Build Advanced Agentic Automation in UiPath (Step-by-Step)
▶️ https://www.youtube.com/watch?v=yxP3kQFTYZo

Covers:

AI Agents

Human-in-the-loop

Action Center

Maestro orchestration

This is one of the best practical tutorials available. 

3. UiPath Maestro: Orchestrate AI Agents, Robots, and People
▶️ https://www.youtube.com/watch?v=MQ9gxVVUIkQ

Official UiPath video explaining how Maestro coordinates agents, robots, and humans using BPMN processes. 

4. Mastering UiPath Maestro – Building a Live Use Case
▶️ https://www.youtube.com/watch?v=Nj3Dt1qESnU

Shows:

Agent integration

Workflow design

Testing and deployment

Real use case implementation 

For Your Poster Agent
Watch them in this order:

Introduction to Process Modeling – https://www.youtube.com/watch?v=QnvlACXwKDA 

Build & Deploy First Process – https://www.youtube.com/watch?v=spu8UMMYUaY 

RPA & Agent Deployment from Scratch – https://www.youtube.com/watch?v=XExl_S_EIAk 

Advanced Agentic Automation – https://www.youtube.com/watch?v=yxP3kQFTYZo 

Since you already have a Streamlit-based Poster Agent, after watching these videos send me:

Your Streamlit URL

Whether it has a REST API endpoint

Screenshot of your Maestro screen

Then I can show exactly how to register the Poster Agent in Maestro and call it from a BPMN workflow.


Qualesce Poster Agent · Streamlit

If "Qualesce Poster Agent · Streamlit" is your deployed Streamlit app, I need the actual URL to verify how it can be connected to Maestro.

For example:

https://qualesce-poster-agent.streamlit.app
or

https://posteragent.qualesce.com
If you already have the URL, open it and check:

Test 1: Is there an API?
Try adding:

/docs
Example:

https://your-url/docs
If a Swagger page opens, then it has a FastAPI backend and can be directly integrated with Maestro.

Test 2: Streamlit Only?
If it only shows the Streamlit UI (upload file, enter topic, generate poster) and no API exists, then Maestro cannot call it directly. You would need:

Maestro
   ↓
UiPath Process
   ↓
Browser Automation
   ↓
Streamlit Poster Agent
or create a REST API around the poster generation logic.

For Maestro Integration
Your Poster Agent should ideally expose an endpoint like:

POST /generate-poster
Input:

{
  "topic": "AI in Healthcare",
  "theme": "Corporate"
}
Output:

{
  "poster_url": "https://..."
}
Then Maestro can call it as an Agent Task.

Send me:

The Streamlit URL.

A screenshot of the app.

Whether you hosted it on Streamlit Community Cloud, VPS, Azure, or local machine.

I can then tell you the exact integration approach for Maestro.


https://content-generator-agent-wpur9zmyevt8cxtn5uopw9.streamlit.app/

I can't directly inspect that Streamlit app from the URL alone, but if that URL is your deployed Poster Agent, you can determine whether Maestro can connect to it by checking a few things:

1. Check whether the app exposes an API
Try opening:

https://content-generator-agent-wpur9zmyevt8cxtn5uopw9.streamlit.app/docs
or

https://content-generator-agent-wpur9zmyevt8cxtn5uopw9.streamlit.app/openapi.json
If you get API documentation or JSON, Maestro can potentially call it directly.

If you get a Streamlit page or a "Page not found", it's likely UI-only.

2. If it's Streamlit UI only
Maestro cannot directly invoke a Streamlit button click. You have two options:

Option A (Recommended):

Move your poster-generation logic into a FastAPI service.

Keep Streamlit as the frontend.

Let Maestro call the FastAPI endpoint.

Option B:

Create a UiPath process that:

Opens the Streamlit URL.

Uploads content.

Clicks Generate.

Downloads/stores the generated poster.

Call that UiPath process from Maestro.

3. Recommended Architecture
Maestro BPMN
    ↓
Agent Task
    ↓
UiPath Process / API Call
    ↓
Poster Generator Service
    ↓
Poster URL Returned
    ↓
Human Review
    ↓
Publish
4. What I need from you
Send:

A screenshot of the Streamlit app home page.

Whether you have the source code.

Whether the poster is generated using:

OpenAI

Claude

Gemini

Local model

Then I can tell you the exact Maestro integration pattern and whether you need an API layer or can connect it directly.


acb0b67d-c1b2-46fc-a862-8b643800b033.png
if i open this it shows like ths

From your screenshot, /docs is not opening Swagger/OpenAPI documentation. It is simply loading the same Streamlit application page.

That means:

✅ Streamlit app is running.

❌ No REST API is exposed.

❌ Maestro cannot directly call this URL as an Agent endpoint.

What you need for Maestro
Your current setup is:

Maestro
   ❌
Streamlit UI
Maestro cannot click buttons inside Streamlit.

Instead, you need:

Maestro
   ↓
API Endpoint
   ↓
Poster Generation Logic
   ↓
Poster Output
Check if you have the source code
If you have the Python code for the Poster Agent, look for files like:

app.py
streamlit_app.py
main.py
If it contains:

import streamlit as st
only, then it's UI-only.

Recommended Fix
Create a FastAPI endpoint alongside Streamlit:

from fastapi import FastAPI

app = FastAPI()

@app.post("/generate-poster")
async def generate_poster(data: dict):

    topic = data["topic"]

    # Call your poster generation code

    return {
        "status": "success",
        "poster_url": "generated_poster.png"
    }
Then:

Deploy FastAPI.

Register the API in Maestro.

Use an Agent Task in BPMN to call it.

Alternative (No Code Changes)
If you don't want to modify the agent:

Maestro
   ↓
UiPath Process
   ↓
Open Browser
   ↓
https://content-generator-agent-wpur9zmyevt8cxtn5uopw9.streamlit.app
   ↓
Enter Topic
   ↓
Click Generate Poster
   ↓
Download Poster
Then Maestro orchestrates the UiPath process instead of calling the Streamlit app directly.

Can you share:
The source code repository (GitHub link or main Python file)?

Was this agent built using Claude Code, OpenAI, LangGraph, CrewAI, or something else?

Then I can tell you the exact steps to make it Maestro-compatible.


how to deploy the fast API ?

Since your goal is to connect the Poster Agent to UiPath Maestro, the easiest approach is:

Step 1: Install FastAPI
pip install fastapi uvicorn
FastAPI uses Uvicorn as the ASGI server to run the API. 

Step 2: Create main.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"status": "running"}

@app.post("/generate-poster")
def generate_poster(data: dict):

    topic = data.get("topic")

    # Call your poster generation function here

    return {
        "status": "success",
        "poster_url": "poster.png"
    }
Step 3: Run Locally
uvicorn main:app --reload
Then open:

http://127.0.0.1:8000/docs
FastAPI automatically generates Swagger/OpenAPI documentation at /docs. 

Step 4: Test API
Use Swagger UI:

{
  "topic": "AI in Healthcare"
}
or use Postman.

Step 5: Deploy
Option A – Render (Easiest)
Push code to GitHub.

Create an account on:

Render

New Web Service.

Connect GitHub repo.

Build Command:

pip install -r requirements.txt
Start Command:

uvicorn main:app --host 0.0.0.0 --port $PORT
Your API URL becomes:

https://your-app.onrender.com
Option B – Streamlit + FastAPI Together
Since your Poster Agent is already on Streamlit, you can:

Streamlit UI
      |
      v
FastAPI Backend
      |
      v
Poster Generation Logic
Keep Streamlit for users and expose FastAPI for Maestro.

Step 6: Connect to Maestro
Once deployed, Maestro can call:

POST https://your-api-url/generate-poster
Input:

{
  "topic": "AI Agents in Marketing"
}
Output:

{
  "status": "success",
  "poster_url": "https://..."
}
Then use this endpoint in a Maestro Agent Task.

Since you already have the Qualesce Poster Agent deployed on Streamlit, the next step is to see the source code. If you upload your app.py or GitHub repository, I can show you exactly how to extract the poster-generation logic and create the FastAPI service in less than 30 minutes.


i already uploaded my app.py into github

Great. If your app.py is already in GitHub, you don't need to upload it again.

The next question is:

Is the GitHub repository connected to Streamlit Cloud?
If yes, your current deployment is probably:

GitHub Repo
     ↓
Streamlit Cloud
     ↓
Qualesce Poster Agent
To integrate with Maestro, you need a separate FastAPI deployment.

Simplest Approach
1. Create a new file in the same GitHub repo
Create api.py

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"status":"running"}

@app.post("/generate-poster")
def generate_poster(data: dict):

    topic = data.get("topic")

    # call your existing poster generation function here

    return {
        "status":"success",
        "topic":topic
    }
2. Add requirements
In requirements.txt

fastapi
uvicorn
streamlit
3. Deploy FastAPI
Use:

Render (easiest)

Railway

Azure App Service

I recommend Render.

4. Connect GitHub to Render
Login to Render

New → Web Service

Select your GitHub repository

Build Command:

pip install -r requirements.txt
Start Command:

uvicorn api:app --host 0.0.0.0 --port $PORT
5. Test
Render will give:

https://poster-agent-api.onrender.com
Open:

https://poster-agent-api.onrender.com/docs
If Swagger appears, Maestro can use it.

What I need from you now
Send either:

Your GitHub repository link

OR

The contents of your app.py

Then I can show:

Which function generates the poster.

Exactly how to wrap that function inside FastAPI.

How to deploy it on Render.

How to register it in UiPath Maestro.


https://github.com/rubika2103/content-generator-agent

I checked the repository link you shared:

content-generator-agent GitHub Repository

The repository contents are not directly visible through the search results I can access, so I can't see your actual app.py implementation yet. 

Fastest way forward
Open your repository and send me either:

The contents of app.py, or

A screenshot of the repository file list, or

The direct GitHub URL to app.py

Example:

https://github.com/rubika2103/content-generator-agent/blob/main/app.py
What I'll do next
Once I see the code, I'll give you:

Option A: Convert existing Streamlit app to FastAPI
# Existing function
generate_poster(...)

# FastAPI wrapper
@app.post("/generate-poster")
Option B: Run both together
GitHub
   |
   +-- streamlit_app.py  --> Streamlit UI
   |
   +-- api.py            --> FastAPI
Then deploy:

Streamlit Cloud
      +
Render (FastAPI)
      +
UiPath Maestro
End Goal
Your Maestro BPMN will look like:

Marketing Request
      |
      v
Human Approval
      |
      v
Poster Agent (FastAPI)
      |
      v
Poster Generated
      |
      v
Marketing Review
      |
      v
Publish
Send the app.py file (or its GitHub URL), and I'll generate the exact api.py, requirements.txt, and Render deployment configuration needed for Maestro.


https://github.com/rubika2103/content-generator-agent/blob/main/app.py

The GitHub file isn't accessible through the search results in a way that lets me read the contents of app.py, so I can't see your code yet. 

Quickest way forward
Open:

https://github.com/rubika2103/content-generator-agent/blob/main/app.py
Then either:

Copy and paste the entire app.py here, or

Upload the app.py file directly in this chat, or

Share screenshots of:

app.py

requirements.txt

Once you send the code
I will give you:

✅ api.py ready for FastAPI
✅ Updated requirements.txt
✅ Render deployment settings
✅ Swagger URL (/docs)
✅ UiPath Maestro Agent configuration
✅ BPMN flow for your Poster Agent

Most likely, your code already has a function similar to:

generate_poster(...)
or

create_poster(...)
I will simply wrap that function inside:

from fastapi import FastAPI

app = FastAPI()

@app.post("/generate-poster")
def generate_poster_api(request: dict):
    ...
and then show you how to deploy it to Render and connect it to Maestro.

Upload the actual app.py file here, and I'll generate the complete FastAPI version for you.


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

Perfect. Looking at your app.py, I can see that your Streamlit app already has the core function:

generate_poster(content, reuse_content=False)
and internally it uses:

extract_content()
render_to_png()
get_next_style()
To make this Maestro-compatible, create a new file called api.py in the same repository.

api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os

from agent import (
    render_to_png,
    get_next_style,
    extract_content,
    TEMPLATES
)

app = FastAPI(
    title="Qualesce Poster Agent API",
    version="1.0"
)

class PosterRequest(BaseModel):
    content: str

@app.get("/")
def home():
    return {"status": "running"}

@app.post("/generate-poster")
def generate_poster(req: PosterRequest):

    try:
        extracted = extract_content(req.content)

        style_num = get_next_style()

        html = TEMPLATES[style_num % len(TEMPLATES)](extracted)

        png = render_to_png(html)

        output_file = "generated_poster.png"

        with open(output_file, "wb") as f:
            f.write(png)

        return {
            "status": "success",
            "style": style_num,
            "file_name": output_file
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
Update requirements.txt
Add:

fastapi
uvicorn
pydantic
Test Locally
pip install -r requirements.txt

uvicorn api:app --reload
Open:

http://127.0.0.1:8000/docs
You should see Swagger UI.

Test Endpoint
POST

http://127.0.0.1:8000/generate-poster
Body:

{
  "content": "AI Agents are transforming marketing operations."
}
Response:

{
  "status": "success",
  "style": 3,
  "file_name": "generated_poster.png"
}
Deploy to Render
Push api.py to GitHub.

Create a Render account.

New → Web Service.

Connect repository content-generator-agent.

Build Command

pip install -r requirements.txt
Start Command

uvicorn api:app --host 0.0.0.0 --port $PORT
Add environment variable:

GROQ_API_KEY=<your_key>
After Deployment
Render will give a URL like:

https://content-generator-api.onrender.com
Swagger:

https://content-generator-api.onrender.com/docs
Connect to Maestro
In Maestro:

Create an Agent Task.

Choose External API Agent.

Endpoint:

POST https://content-generator-api.onrender.com/generate-poster
Input Schema:

{
  "content": "string"
}
Output Schema:

{
  "status": "string",
  "style": "number",
  "file_name": "string"
}
One improvement I'd recommend before deploying: instead of returning only generated_poster.png, upload the generated image to a storage location (Azure Blob, S3, etc.) and return a poster URL. Maestro workflows work much better when they receive a URL to the generated poster rather than a local filename.



