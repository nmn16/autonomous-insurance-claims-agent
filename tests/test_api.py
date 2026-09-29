"""End-to-end tests: real HTTP calls against the FastAPI app."""

from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_documents"


def upload(filename: str, content: bytes, content_type: str = "text/plain"):
    return client.post(
        "/process-claim", files={"file": (filename, content, content_type)}
    )


def make_pdf_bytes(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    y_position = 50
    for line in text.replace("₹", "Rs. ").splitlines():
        if line.strip():
            page.insert_text((40, y_position), line, fontsize=9)
        y_position += 12
    data = document.tobytes()
    document.close()
    return data


def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert "running" in response.json()["message"]


@pytest.mark.parametrize(
    "filename, expected_route",
    [
        ("claim_fast_track.txt", "Fast-track"),
        ("claim_injury.txt", "Specialist Queue"),
        ("claim_investigation.txt", "Investigation Flag"),
        ("claim_missing_fields.txt", "Manual Review"),
        ("claim_manual_review.txt", "Manual Review"),
        ("claim_multiple_conditions.txt", "Investigation Flag"),
    ],
)
def test_sample_documents_route_as_expected(filename, expected_route):
    response = upload(filename, (SAMPLE_DIR / filename).read_bytes())
    assert response.status_code == 200
    body = response.json()
    assert body["recommendedRoute"] == expected_route
    assert set(body) >= {
        "extractedFields", "missingFields", "recommendedRoute", "reasoning",
    }


def test_missing_fields_are_listed_in_response():
    content = (SAMPLE_DIR / "claim_missing_fields.txt").read_bytes()
    body = upload("claim_missing_fields.txt", content).json()
    assert "policyNumber" in body["missingFields"]
    assert body["extractedFields"]["policyNumber"] is None


def test_pdf_upload_works_end_to_end():
    text = (SAMPLE_DIR / "claim_fast_track.txt").read_text(encoding="utf-8")
    response = upload("claim.pdf", make_pdf_bytes(text), "application/pdf")
    assert response.status_code == 200
    body = response.json()
    assert body["extractedFields"]["policyNumber"] == "POL-2025-004521"
    assert body["recommendedRoute"] == "Fast-track"


def test_unsupported_file_type_returns_415():
    assert upload("notes.docx", b"hello").status_code == 415


def test_empty_file_returns_400():
    assert upload("empty.txt", b"").status_code == 400


def test_invalid_pdf_returns_400():
    assert upload("fake.pdf", b"this is not a pdf").status_code == 400


def test_pdf_without_text_returns_400():
    document = fitz.open()
    document.new_page()
    data = document.tobytes()
    document.close()
    assert upload("scan.pdf", data, "application/pdf").status_code == 400


def test_text_without_fnol_fields_returns_422():
    response = upload("random.txt", b"Dear sir, please call me back soon.")
    assert response.status_code == 422
