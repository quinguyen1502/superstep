"""Record the owner of a team dataset; backfill it from the dataset's create audit event."""
import sqlalchemy as sa
from alembic import op

revision = "0068_dataset_team_owner"
down_revision = "0067_dataset_delete_capability"
branch_labels = depends_on = None


def upgrade():
    with op.batch_alter_table("datasets") as batch:
        batch.add_column(sa.Column("team_owner_id", sa.String(), nullable=True))
        batch.create_foreign_key("fk_datasets_team_owner", "users", ["team_owner_id"], ["id"], ondelete="SET NULL")
    op.execute(sa.text(
        "UPDATE datasets SET team_owner_id = ("
        " SELECT audit_events.actor_id FROM audit_events JOIN users ON users.id = audit_events.actor_id"
        " WHERE audit_events.action = 'dataset.create' AND audit_events.target_type = 'dataset'"
        " AND audit_events.target_id = datasets.id ORDER BY audit_events.ts LIMIT 1"
        ") WHERE team_id IS NOT NULL"
    ))


def downgrade():
    with op.batch_alter_table("datasets") as batch:
        batch.drop_constraint("fk_datasets_team_owner", type_="foreignkey")
        batch.drop_column("team_owner_id")
