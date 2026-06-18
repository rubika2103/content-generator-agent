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
