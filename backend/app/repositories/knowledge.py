"""Knowledge bases, documents and chunks. Similarity search runs in SQL with pgvector, else brute force."""
import json
from typing import Optional
from sqlalchemy import delete, func, select, text, update
from ..engine.embeddings import cosine
from ..models import KbChunk, KbDocument, KnowledgeBase
from ..models.database import Database

_VECTOR: dict[str, bool] = {}  # database url -> kb_chunks.embedding is a pgvector column


class KnowledgeRepository:
    def __init__(self, db: Database): self.db = db

    def has_vector(self) -> bool:
        if self.db.url not in _VECTOR:
            ok = False
            if self.db.engine.dialect.name == "postgresql":
                with self.db.engine.connect() as c:
                    ok = c.execute(text("SELECT udt_name FROM information_schema.columns WHERE table_name='kb_chunks' "
                                        "AND column_name='embedding' AND table_schema=current_schema()")).scalar() == "vector"
            _VECTOR[self.db.url] = ok
        return _VECTOR[self.db.url]

    # ---- knowledge bases ----
    def add(self, kb: KnowledgeBase) -> KnowledgeBase:
        with self.db.session() as s: s.add(kb); s.commit(); return kb

    def list_for_owner(self, owner: str) -> list[tuple[KnowledgeBase, int, int]]:
        """(kb, documents, chunks) newest first."""
        docs = select(KbDocument.kb_id, func.count(KbDocument.id).label("n"), func.coalesce(func.sum(KbDocument.chunks), 0).label("c")) \
            .group_by(KbDocument.kb_id).subquery()
        with self.db.session() as s:
            rows = s.execute(select(KnowledgeBase, docs.c.n, docs.c.c).outerjoin(docs, docs.c.kb_id == KnowledgeBase.id)
                             .where(KnowledgeBase.owner == owner).order_by(KnowledgeBase.created.desc())).all()
            return [(kb, int(n or 0), int(c or 0)) for kb, n, c in rows]

    def get_owned(self, kid: str, owner: str) -> Optional[KnowledgeBase]:
        with self.db.session() as s:
            return s.scalars(select(KnowledgeBase).where(KnowledgeBase.id == kid, KnowledgeBase.owner == owner)).first()

    def update(self, kid: str, **values) -> None:
        with self.db.session() as s: s.execute(update(KnowledgeBase).where(KnowledgeBase.id == kid).values(**values)); s.commit()

    def delete(self, kid: str) -> None:
        with self.db.session() as s:
            s.execute(delete(KbChunk).where(KbChunk.kb_id == kid)); s.execute(delete(KbDocument).where(KbDocument.kb_id == kid))
            s.execute(delete(KnowledgeBase).where(KnowledgeBase.id == kid)); s.commit()

    # ---- documents / chunks ----
    def documents(self, kid: str) -> list[KbDocument]:
        with self.db.session() as s:
            return list(s.scalars(select(KbDocument).where(KbDocument.kb_id == kid).order_by(KbDocument.created.desc())))

    def get_document(self, kid: str, did: str) -> Optional[KbDocument]:
        with self.db.session() as s:
            return s.scalars(select(KbDocument).where(KbDocument.id == did, KbDocument.kb_id == kid)).first()

    def _chunk_insert(self):
        return text("INSERT INTO kb_chunks (kb_id, document_id, idx, text, embedding) VALUES (:kb_id, :document_id, :idx, :text, "
                    + ("CAST(:embedding AS vector))" if self.has_vector() else ":embedding)"))

    @staticmethod
    def _vec(v: list[float]) -> str: return "[" + ",".join(repr(float(x)) for x in v) + "]"

    def add_document(self, doc: KbDocument, texts: list[str], vectors: list[list[float]]) -> KbDocument:
        """Document and its chunks in one transaction."""
        with self.db.session() as s:
            s.add(doc); s.flush()
            if texts:
                s.execute(self._chunk_insert(), [{"kb_id": doc.kb_id, "document_id": doc.id, "idx": i, "text": t, "embedding": self._vec(v)}
                                                 for i, (t, v) in enumerate(zip(texts, vectors))])
            s.commit(); return doc

    def delete_document(self, did: str) -> None:
        with self.db.session() as s:
            s.execute(delete(KbChunk).where(KbChunk.document_id == did)); s.execute(delete(KbDocument).where(KbDocument.id == did)); s.commit()

    def chunk_texts(self, kid: str) -> list[tuple[int, str]]:
        with self.db.session() as s:
            return [(i, t) for i, t in s.execute(select(KbChunk.id, KbChunk.text).where(KbChunk.kb_id == kid).order_by(KbChunk.id))]

    def set_embeddings(self, pairs: list[tuple[int, list[float]]]) -> None:
        cast = "CAST(:e AS vector)" if self.has_vector() else ":e"
        with self.db.session() as s:
            if pairs: s.execute(text(f"UPDATE kb_chunks SET embedding = {cast} WHERE id = :id"), [{"id": i, "e": self._vec(v)} for i, v in pairs])
            s.commit()

    def stored_dims(self, kid: str) -> Optional[int]:
        """Dimension of one stored vector of the knowledge base (legacy rows without `knowledge_bases.dims`)."""
        with self.db.session() as s:
            if self.has_vector():
                return s.execute(text("SELECT vector_dims(embedding) FROM kb_chunks WHERE kb_id = :kb AND embedding IS NOT NULL LIMIT 1"), {"kb": kid}).scalar()
            e = s.scalars(select(KbChunk.embedding).where(KbChunk.kb_id == kid, KbChunk.embedding.is_not(None)).limit(1)).first()
            return len(json.loads(e)) if e else None

    def search(self, kid: str, vector: list[float], k: int) -> list[dict]:
        """Top-k chunks by cosine similarity: {text, score, document_id, filename, index}."""
        cols = "c.text, c.document_id, d.filename, c.idx"
        with self.db.session() as s:
            if self.has_vector():
                rows = s.execute(text(f"SELECT {cols}, 1 - (c.embedding <=> CAST(:q AS vector)) AS score FROM kb_chunks c "
                                      "JOIN kb_documents d ON d.id = c.document_id WHERE c.kb_id = :kb "
                                      "AND vector_dims(c.embedding) = :dims ORDER BY c.embedding <=> CAST(:q AS vector) LIMIT :k"),
                                 {"q": self._vec(vector), "kb": kid, "k": k, "dims": len(vector)}).all()
                scored = [(float(r.score), r) for r in rows]
            else:
                rows = s.execute(text(f"SELECT {cols}, c.embedding FROM kb_chunks c JOIN kb_documents d ON d.id = c.document_id "
                                      "WHERE c.kb_id = :kb"), {"kb": kid}).all()
                scored = sorted(((cosine(vector, json.loads(r.embedding)), r) for r in rows if r.embedding), key=lambda x: -x[0])[:k]
        return [{"text": r.text, "score": round(sc, 4), "document_id": r.document_id, "filename": r.filename, "index": r.idx} for sc, r in scored]
