from pathlib import Path

import aiofiles
from pypdf import PdfReader
from pypdf.errors import PdfReadError


class DocumentParseError(Exception):
    pass


async def parse_document(file_path: Path) -> str:
    try:
        extension = file_path.suffix.lower()

        if extension == ".txt":
            text = await _parse_txt(file_path)
        elif extension == ".pdf":
            text = _parse_pdf(file_path)
        else:
            raise DocumentParseError(f"Unsupported document type: {extension}")

    except (OSError, UnicodeDecodeError, PdfReadError) as exc:
        raise DocumentParseError("Document could not be parsed.") from exc

    if not text.strip():
        raise DocumentParseError("Document contains no extractable text.")

    return text


async def _parse_txt(file_path: Path) -> str:
    async with aiofiles.open(
        file_path,
        "r",
        encoding="utf-8",
    ) as file:
        return await file.read()


def _parse_pdf(file_path: Path) -> str:
    reader = PdfReader(file_path)

    pages: list[str] = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            pages.append(text)

    return "\n\n".join(pages)
