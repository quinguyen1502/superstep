"""knowledge_bases.dims, the embedding dimension of a knowledge base's stored vectors.

Existing knowledge bases keep NULL; the service reads the dimension from a stored chunk the first time it needs it."""
from alembic import op
import sqlalchemy as sa

revision = "0025_kb_dims"
down_revision = "0024_credential_headers"


def upgrade():
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("knowledge_bases")}
    if "dims" not in cols:
        op.add_column("knowledge_bases", sa.Column("dims", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("knowledge_bases", "dims")
