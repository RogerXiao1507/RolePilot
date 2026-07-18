import json
from io import BytesIO

from openai import OpenAI
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.config import settings

client = OpenAI(api_key=settings.openai_api_key)


def extract_text_from_pdf_bytes(
    file_bytes: bytes,
    *,
    max_pages: int | None = None,
    max_text_chars: int | None = None,
) -> str:
    max_pages = max_pages or settings.max_resume_pages
    max_text_chars = max_text_chars or settings.max_resume_text_chars

    if not file_bytes.startswith(b"%PDF-"):
        raise ValueError("The uploaded file is not a valid PDF.")

    try:
        pdf = PdfReader(BytesIO(file_bytes))
    except (PdfReadError, OSError, ValueError) as exc:
        raise ValueError("The uploaded PDF could not be read.") from exc

    if pdf.is_encrypted:
        raise ValueError("Encrypted PDF files are not supported.")
    if len(pdf.pages) > max_pages:
        raise ValueError(f"Resume PDFs cannot exceed {max_pages} pages.")

    pages = []
    extracted_length = 0

    try:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if not text.strip():
                continue

            cleaned_text = text.strip()
            extracted_length += len(cleaned_text)
            if extracted_length > max_text_chars:
                raise ValueError(
                    f"Extracted resume text cannot exceed {max_text_chars} characters."
                )
            pages.append(cleaned_text)
    except PdfReadError as exc:
        raise ValueError("The uploaded PDF could not be read.") from exc

    extracted_text = "\n\n".join(pages).strip()

    if not extracted_text:
        raise ValueError("Could not extract text from the uploaded PDF.")

    return extracted_text


def analyze_resume_text(text: str) -> dict:
    response = client.responses.create(
        model="gpt-5.4-mini",
        input=[
            {
                "role": "developer",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "You are an expert resume reviewer for students applying to internships "
                            "in software engineering, hardware engineering, and technical roles. "
                            "Analyze the resume text and return only valid JSON matching the schema. "
                            "Do not invent experience. Focus on strengths, weaknesses, wording quality, "
                            "missing metrics, and practical improvement suggestions."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Analyze this resume:\n\n{text}",
                    }
                ],
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "resume_analysis",
                "schema": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "strengths": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "weaknesses": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "wording_issues": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "missing_metrics": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "suggested_improvements": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "summary",
                        "strengths",
                        "weaknesses",
                        "wording_issues",
                        "missing_metrics",
                        "suggested_improvements",
                    ],
                    "additionalProperties": False,
                },
            }
        },
    )

    return json.loads(response.output_text)
