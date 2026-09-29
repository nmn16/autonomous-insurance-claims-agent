"""FastAPI application: HTTP handling only, no business logic."""

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import ValidationError

from app import config
from app.document_parser import parse_document
from app.exceptions import (
    EmptyDocumentError,
    ExtractionError,
    InvalidPdfError,
    UnsupportedFileTypeError,
)
from app.models import ClaimResult
from app.pipeline import process_claim_text

app = FastAPI(
    title="Autonomous Insurance Claims Processing Agent",
    description="Upload an FNOL document (PDF/TXT) and get extracted "
    "fields, missing fields and a recommended route.",
    version="1.0.0",
)


@app.get("/")
def health_check() -> dict[str, str]:
    return {
        "message": "Autonomous Insurance Claims Processing Agent is running"
    }


@app.post("/process-claim", response_model=ClaimResult)
async def process_claim(file: UploadFile = File(...)) -> ClaimResult:
    content = await file.read()
    if len(content) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File is larger than {config.MAX_UPLOAD_MB} MB.",
        )

    try:
        text = parse_document(file.filename or "", content)
        return process_claim_text(text)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except (EmptyDocumentError, InvalidPdfError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Extracted claim data is invalid ({exc.error_count()} error(s)).",
        ) from exc
