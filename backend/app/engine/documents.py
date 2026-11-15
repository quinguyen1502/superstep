"""Document text extraction and chunking for knowledge bases. Pure functions, no I/O besides parsing bytes."""
from __future__ import annotations
import io, os, re
from typing import List

EXTENSIONS = (".txt", ".md", ".pdf")
CHUNK_CHARS = 800
OVERLAP = 120


class DocumentError(Exception):
    pass


def extract(filename: str, data: bytes) -> str:
    ext = os.path.splitext(filename.lower())[1]
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            return "\n\n".join((p.extract_text() or "") for p in reader.pages).strip()
        except Exception as e:
            raise DocumentError(f"cannot read PDF ({type(e).__name__})") from None
    for enc in ("utf-8-sig", "utf-16"):
        try: return data.decode(enc).strip()
        except UnicodeDecodeError: continue
    raise DocumentError("text is not UTF-8")


def chunk(text: str, size: int = CHUNK_CHARS, overlap: int = OVERLAP) -> List[str]:
    """Paragraph-aware chunks of at most `size` characters; long paragraphs are cut with `overlap` characters repeated."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out: List[str] = []; cur = ""
    for p in paras:
        if len(cur) + len(p) + 2 <= size:
            cur = f"{cur}\n\n{p}" if cur else p; continue
        if cur: out.append(cur); cur = ""
        while len(p) > size:
            cut = p.rfind(" ", size - overlap, size); cut = cut if cut > 0 else size
            out.append(p[:cut].strip()); p = p[max(0, cut - overlap):].strip()
        cur = p
    if cur: out.append(cur)
    return out
