"""knowledge bases, documents and chunks for the Retriever node.

On Postgres the `vector` extension (pgvector) is enabled when available and kb_chunks.embedding becomes a `vector`
column; without the extension (plain Postgres image) or on SQLite it is JSON text and search is brute force."""
from alembic import op
import sqlalchemy as sa

revision = "0019_knowledge_bases"
down_revision = "0018_delivery_dedupe"


def _vector_available(bind) -> bool:
    if bind.dialect.name != "postgresql": return False
    try:
        with bind.begin_nested():
            bind.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        return True
    except Exception:
        return False  # extension not installed on the server or no privilege: JSON fallback


def upgrade():
    bind = op.get_bind()
    if "knowledge_bases" in sa.inspect(bind).get_table_names(): return
    op.create_table("knowledge_bases",
        sa.Column("id", sa.Text(), primary_key=True), sa.Column("owner", sa.Text(), nullable=False, index=True),
        sa.Column("name", sa.Text(), nullable=False), sa.Column("description", sa.Text()), sa.Column("model", sa.Text()),
        sa.Column("credential_id", sa.Text()), sa.Column("embedder", sa.Text()), sa.Column("created", sa.Float(), nullable=False))
    op.create_table("kb_documents",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("kb_id", sa.Text(), sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("filename", sa.Text(), nullable=False), sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("chunks", sa.Integer(), nullable=False, server_default="0"), sa.Column("created", sa.Float(), nullable=False))
    op.create_table("kb_chunks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("kb_id", sa.Text(), nullable=False, index=True),
        sa.Column("document_id", sa.Text(), sa.ForeignKey("kb_documents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("idx", sa.Integer(), nullable=False), sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", sa.Text()))
    if _vector_available(bind):  # vectors of any dimension (models differ); filtered by kb_id, so no ANN index needed
        bind.exec_driver_sql("ALTER TABLE kb_chunks ALTER COLUMN embedding TYPE vector USING embedding::vector")


def downgrade():
    op.drop_table("kb_chunks"); op.drop_table("kb_documents"); op.drop_table("knowledge_bases")
