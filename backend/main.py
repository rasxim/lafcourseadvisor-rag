from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import tempfile, os, json
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    query: str
    student_profile: dict


class AskResponse(BaseModel):
    answer: str
    sources: list[dict]


def extract_profile_from_text(text: str) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = f"""Extract student information from this degree audit text and return ONLY valid JSON.

Return this exact structure:
{{
  "name": "student full name",
  "major": "major name",
  "class_year": 2029,
  "overall_gpa": 3.8,
  "completed_courses": [
    {{"code": "CS 105", "title": "course title", "grade": "A", "credits": 1}}
  ],
  "in_progress_courses": [
    {{"code": "CS 202", "title": "course title", "credits": 1}}
  ],
  "credits": {{"required": 32, "applied": 15}}
}}

Degree audit text:
{text[:8000]}"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        config=types.GenerateContentConfig(temperature=0.0),
        contents=prompt,
    )
    raw = response.text.strip().removeprefix("```json").removesuffix("```").strip()
    return json.loads(raw)


@app.get("/")
def root():
    return {"status": "ok", "service": "Lafayette Course Advisor API"}


@app.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest):
    from rag import ask
    from retriever import Retriever

    retriever = Retriever()
    chunks = retriever.retrieve(request.query)
    if not chunks:
        return AskResponse(
            answer="I couldn't find relevant information for that question.",
            sources=[],
        )
    answer = ask(request.query, student_profile=request.student_profile)
    return AskResponse(answer=answer, sources=chunks)


@app.post("/upload-transcript")
async def upload_transcript(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files accepted")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        from llama_cloud import LlamaCloud
        client = LlamaCloud(token=os.environ["LLAMA_CLOUD_API_KEY"])
        with open(tmp_path, "rb") as f:
            upload = client.files.upload_file(upload_file=("transcript.pdf", f, "application/pdf"))
        job = client.parsing.begin_parsing(upload.id, language="en", result_type="markdown")
        import time
        for _ in range(30):
            status = client.parsing.get_job(job.id)
            if status.status == "SUCCESS":
                break
            if status.status == "ERROR":
                raise HTTPException(status_code=500, detail="LlamaParse failed to parse PDF")
            time.sleep(2)
        result = client.parsing.get_job_result_markdown(job.id)
        full_text = result.markdown
        profile = extract_profile_from_text(full_text)
        return profile
    finally:
        os.unlink(tmp_path)