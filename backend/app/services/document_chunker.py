from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings


def chunk_document(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    return splitter.split_text(text)
