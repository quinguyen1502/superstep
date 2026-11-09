"""optional extra HTTP headers on a credential (OpenRouter HTTP-Referer / X-Title), JSON text."""
from alembic import op
import sqlalchemy as sa

revision = "0024_credential_headers"
down_revision = "0023_templates"


def upgrade():
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("credentials")}
    if "headers" not in cols:
        op.add_column("credentials", sa.Column("headers", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("credentials", "headers")
