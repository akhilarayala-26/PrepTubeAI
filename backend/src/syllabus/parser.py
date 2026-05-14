"""
Syllabus PDF Parser.
Extracts raw text from uploaded PDF syllabi using PyPDF2.
"""

from pathlib import Path
from PyPDF2 import PdfReader


def extract_text_from_pdf(file_path: str | Path) -> str:
    """
    Extract all text content from a PDF file.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Concatenated text from all pages of the PDF.

    Raises:
        FileNotFoundError: If the PDF file doesn't exist.
        ValueError: If the file is not a valid PDF or contains no extractable text.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    if file_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, got: {file_path.suffix}")

    reader = PdfReader(str(file_path))

    if len(reader.pages) == 0:
        raise ValueError("PDF file has no pages.")

    text_parts = []
    for page_num, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text()
        if page_text:
            # Add page marker for reference
            text_parts.append(f"--- Page {page_num} ---")
            text_parts.append(page_text.strip())

    full_text = "\n\n".join(text_parts)

    if not full_text.strip():
        raise ValueError(
            "Could not extract any text from the PDF. "
            "It may be a scanned document (image-based). "
            "Please provide a text-based PDF."
        )

    return full_text


def get_pdf_metadata(file_path: str | Path) -> dict:
    """
    Extract metadata from a PDF file.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Dictionary containing PDF metadata (title, author, pages, etc.)
    """
    file_path = Path(file_path)
    reader = PdfReader(str(file_path))

    metadata = reader.metadata or {}

    return {
        "title": metadata.get("/Title", "Unknown"),
        "author": metadata.get("/Author", "Unknown"),
        "num_pages": len(reader.pages),
        "file_name": file_path.name,
        "file_size_kb": round(file_path.stat().st_size / 1024, 1),
    }
