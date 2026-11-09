"""Knowledge bases: documents split into chunks with an embedding each.

`embedding` is a pgvector `vector` column on Postgres when the extension is installed (similarity search in SQL) and
JSON text everywhere else (SQLite, or Postgres without pgvector), searched by brute force in the repository."""
from typing import Optional
from sqlalchemy import Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    owner: Mapped[str] = mapped_column(Text, index=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    model: Mapped[Optional[str]] = mapped_column(Text)          # embedding model (default text-embedding-3-small)
    credential_id: Mapped[Optional[str]] = mapped_column(Text)  # OpenAI-compatible credential; none = env key or mock
    embedder: Mapped[Optional[str]] = mapped_column(Text)       # effective embedder of the stored vectors, e.g. mock:256
    dims: Mapped[Optional[int]] = mapped_column(Integer)        # dimension of the stored vectors; NULL = empty / legacy
    created: Mapped[float] = mapped_column(Float)


class KbDocument(Base):
    __tablename__ = "kb_documents"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    kb_id: Mapped[str] = mapped_column(Text, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(Text)
    size: Mapped[int] = mapped_column(Integer)
    chunks: Mapped[int] = mapped_column(Integer, default=0)
    created: Mapped[float] = mapped_column(Float)


class KbChunk(Base):
    __tablename__ = "kb_chunks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kb_id: Mapped[str] = mapped_column(Text, index=True)
    document_id: Mapped[str] = mapped_column(Text, ForeignKey("kb_documents.id", ondelete="CASCADE"), index=True)
    idx: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[Optional[str]] = mapped_column(Text)  # vector or JSON text; written/read by the repository in SQL (has_vector)
