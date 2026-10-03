"""Text extraction (BUILD-076) and chunking (BUILD-077) for uploaded documents.

Extraction is deliberately conservative: PDF (text layer only, no OCR), Word .docx,
Excel .xlsx, plain text and CSV. Scanned PDFs and images have no text layer and are
reported as such rather than guessed at. Legacy .doc/.xls (binary OLE files) are
not parsed.
"""

import io
import re
import zipfile
from dataclasses import dataclass
from xml.etree import ElementTree

CHUNK_TARGET = 900  # characters per passage: about a paragraph or two
CHUNK_OVERLAP = 150  # carried into the next passage so a phrase split at a boundary still matches

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


@dataclass
class Extracted:
    status: str  # "indexed", "no_text", "unsupported", "failed"
    pages: list[tuple[int | None, str]]  # (page number or None, text)
    page_count: int | None = None


def _clean(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def _pdf(content: bytes) -> Extracted:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    pages = [(i + 1, _clean(page.extract_text() or "")) for i, page in enumerate(reader.pages)]
    return Extracted("indexed", pages, page_count=len(reader.pages))


def _docx(content: bytes) -> Extracted:
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        root = ElementTree.fromstring(z.read("word/document.xml"))
    paragraphs = ["".join(t.text or "" for t in p.iter(f"{_W}t")) for p in root.iter(f"{_W}p")]
    return Extracted("indexed", [(None, _clean("\n".join(paragraphs)))])


def _xlsx(content: bytes) -> Extracted:
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ElementTree.fromstring(z.read("xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in si.iter(f"{_S}t")) for si in root.iter(f"{_S}si")]
        sheets = sorted(n for n in z.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))
        lines = []
        for name in sheets:
            root = ElementTree.fromstring(z.read(name))
            for row in root.iter(f"{_S}row"):
                cells = []
                for c in row.iter(f"{_S}c"):
                    v = c.find(f"{_S}v")
                    if c.get("t") == "s" and v is not None and v.text is not None:
                        cells.append(shared[int(v.text)] if int(v.text) < len(shared) else "")
                    elif c.get("t") == "inlineStr":
                        cells.append("".join(t.text or "" for t in c.iter(f"{_S}t")))
                    elif v is not None and v.text is not None:
                        cells.append(v.text)
                if any(cells):
                    lines.append(" | ".join(cells))
    return Extracted("indexed", [(None, _clean("\n".join(lines)))])


def _plain(content: bytes) -> Extracted:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("cp1252", errors="replace")
    return Extracted("indexed", [(None, _clean(text))])


_EXTRACTORS = {
    "application/pdf": _pdf,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": _docx,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": _xlsx,
    "text/plain": _plain,
    "text/csv": _plain,
}


def extract(content_type: str, content: bytes) -> Extracted:
    extractor = _EXTRACTORS.get(content_type)
    if extractor is None:
        return Extracted("unsupported", [])
    try:
        result = extractor(content)
    except Exception:  # a malformed file must never break the upload itself
        return Extracted("failed", [])
    if not any(text for _, text in result.pages):
        result.status = "no_text"
    return result


def chunk(pages: list[tuple[int | None, str]]) -> list[tuple[int | None, str]]:
    """Split each page into passages of about CHUNK_TARGET characters, breaking at
    paragraph or sentence ends where possible, with a little overlap between them."""
    chunks: list[tuple[int | None, str]] = []
    for page, text in pages:
        start = 0
        while start < len(text):
            end = min(len(text), start + CHUNK_TARGET)
            if end < len(text):
                window = text[start:end]
                cut = max(window.rfind("\n\n"), window.rfind(". "), window.rfind("\n"))
                if cut > CHUNK_TARGET // 2:
                    end = start + cut + 1
            passage = text[start:end].strip()
            if passage:
                chunks.append((page, passage))
            if end >= len(text):
                break
            start = max(end - CHUNK_OVERLAP, start + 1)
            # Don't start the next passage mid-word.
            while start < len(text) and start > 0 and not text[start - 1].isspace():
                start += 1
    return chunks
