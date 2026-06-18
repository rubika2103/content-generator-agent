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
