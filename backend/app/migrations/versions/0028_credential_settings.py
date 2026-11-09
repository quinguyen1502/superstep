"""non-secret provider settings on credentials (SMTP host, port, security, username, sender)."""
from alembic import op
import sqlalchemy as sa

revision = "0028_credential_settings"
down_revision = "0027_schedules"


def upgrade():
    if "settings" in {c["name"] for c in sa.inspect(op.get_bind()).get_columns("credentials")}: return
    with op.batch_alter_table("credentials") as b: b.add_column(sa.Column("settings", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("credentials") as b: b.drop_column("settings")
