"""where a run's Code nodes ran (docker | subprocess), so history shows unisolated runs later."""
from alembic import op
import sqlalchemy as sa

revision = "0029_run_code_runtime"
down_revision = "0028_credential_settings"


def upgrade():
    if "code_runtime" in {c["name"] for c in sa.inspect(op.get_bind()).get_columns("runs")}: return
    with op.batch_alter_table("runs") as b: b.add_column(sa.Column("code_runtime", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("runs") as b: b.drop_column("code_runtime")
