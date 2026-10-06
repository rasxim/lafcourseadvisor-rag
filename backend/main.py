from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from audit_parser import AuditParseError, parse_audit

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


@app.get("/")
def root():
    return {"status": "ok", "service": "Lafayette Course Advisor API"}


@app.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest):
    import rag

    text, sources = rag.answer(request.query, request.student_profile)
    return AskResponse(answer=text, sources=sources)


MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@app.post("/upload-transcript")
def upload_transcript(file: UploadFile = File(...)):
    # Plain def: FastAPI runs it in a worker thread, so PDF parsing doesn't block other requests.
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    contents = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="That file is too large for a degree audit.")

    try:
        return parse_audit(contents)
    except AuditParseError as e:
        raise HTTPException(
            status_code=422,
            detail=f"{e} Upload the PDF of your Degree Works audit (Lafayette's degree progress report).",
        ) from e
