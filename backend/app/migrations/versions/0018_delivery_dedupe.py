"""follow-up: webhook_deliveries.dedupe_key, so each settled segment of an API run sends its callback once,
whichever path resumed it (studio, Slack, Telegram, recovery). Nullable + unique (manual redeliveries carry none)."""
from alembic import op
import sqlalchemy as sa

revision = "0018_delivery_dedupe"
down_revision = "0017_verified_identity_unique"


def upgrade():
    if "dedupe_key" in {c["name"] for c in sa.inspect(op.get_bind()).get_columns("webhook_deliveries")}: return
    with op.batch_alter_table("webhook_deliveries") as b:
        b.add_column(sa.Column("dedupe_key", sa.Text(), nullable=True))
        b.create_unique_constraint("uq_webhook_deliveries_dedupe_key", ["dedupe_key"])


def downgrade():
    with op.batch_alter_table("webhook_deliveries") as b:
        b.drop_constraint("uq_webhook_deliveries_dedupe_key", type_="unique")
        b.drop_column("dedupe_key")
