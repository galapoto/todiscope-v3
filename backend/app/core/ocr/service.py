"""
OCR (Optical Character Recognition) service.

Extracts text from PDFs and images.
"""

from __future__ import annotations

import io
from typing import Any

try:
    import pdfplumber
except ImportError:  # pragma: no cover - optional dependency
    pdfplumber = None

try:
    import pytesseract
except ImportError:  # pragma: no cover - optional dependency
    pytesseract = None

try:
    from PIL import Image
except ImportError:  # pragma: no cover - optional dependency
    Image = None


async def extract_text_from_file(
    *,
    file_content: bytes,
    content_type: str,
    filename: str,
) -> dict[str, Any]:
    """
    Extract text from a file using OCR.
    
    Args:
        file_content: Raw file content as bytes
        content_type: MIME type of the file
        filename: Original filename
    
    Returns:
        Dictionary containing:
        - extracted_text: Extracted text content
        - confidence: Overall confidence score (0.0 to 1.0)
        - low_confidence_sections: List of sections with low confidence
    """
    # Basic validation
    if not file_content:
        return {
            "extracted_text": "",
            "confidence": 0.0,
            "low_confidence_sections": [],
        }

    is_pdf = "pdf" in content_type.lower() or filename.lower().endswith(".pdf")
    is_image = content_type.lower().startswith("image/")

    if is_pdf:
        if pdfplumber is None:
            message = (
                "PDF OCR requires pdfplumber. Install pdfplumber to extract text from PDFs."
            )
            return {
                "extracted_text": message,
                "confidence": 0.0,
                "low_confidence_sections": [],
            }
        text_pages: list[str] = []
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_pages.append(page_text)
        extracted = "\n\n".join(text_pages).strip()
        return {
            "extracted_text": extracted or "",
            "confidence": 0.85 if extracted else 0.0,
            "low_confidence_sections": [],
        }

    if is_image:
        if Image is None or pytesseract is None:
            message = (
                "Image OCR requires Pillow and pytesseract. Install both to extract text from images."
            )
            return {
                "extracted_text": message,
                "confidence": 0.0,
                "low_confidence_sections": [],
            }
        image = Image.open(io.BytesIO(file_content))
        text = pytesseract.image_to_string(image) or ""
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        confidences = [
            float(conf)
            for conf in data.get("conf", [])
            if conf not in ("-1", "", None)
        ]
        avg_conf = (sum(confidences) / len(confidences)) / 100 if confidences else 0.0
        return {
            "extracted_text": text.strip(),
            "confidence": round(avg_conf, 3),
            "low_confidence_sections": [],
        }

    return {
        "extracted_text": "",
        "confidence": 0.0,
        "low_confidence_sections": [],
    }

