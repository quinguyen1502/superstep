"""teams (+ members, workflow team shares), the administrative audit log and studio settings (org policy)."""
from alembic import op
import sqlalchemy as sa

revision = "0022_teams_audit"
down_revision = "0021_rbac"


def upgrade():
    have = set(sa.inspect(op.get_bind()).get_table_names())
    if "teams" not in have:
        op.create_table("teams", sa.Column("id", sa.Text(), primary_key=True), sa.Column("name", sa.Text(), nullable=False, unique=True),
                        sa.Column("description", sa.Text()), sa.Column("created", sa.Float(), nullable=False), sa.Column("created_by", sa.Text(), nullable=False))
    if "team_members" not in have:
        op.create_table("team_members",
                        sa.Column("team_id", sa.Text(), sa.ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True),
                        sa.Column("user_id", sa.Text(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True),
                        sa.Column("added", sa.Float(), nullable=False))
    if "workflow_team_shares" not in have:
        op.create_table("workflow_team_shares",
                        sa.Column("workflow_id", sa.Text(), sa.ForeignKey("workflows.id", ondelete="CASCADE"), primary_key=True),
                        sa.Column("team_id", sa.Text(), sa.ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True, index=True),
                        sa.Column("role", sa.Text(), nullable=False), sa.Column("created", sa.Float(), nullable=False),
                        sa.Column("shared_by", sa.Text(), nullable=False))
    if "audit_events" not in have:
        op.create_table("audit_events", sa.Column("id", sa.Text(), primary_key=True), sa.Column("ts", sa.Float(), nullable=False, index=True),
                        sa.Column("actor_id", sa.Text(), index=True), sa.Column("actor_email", sa.Text()),
                        sa.Column("action", sa.Text(), nullable=False, index=True), sa.Column("target_type", sa.Text(), nullable=False),
                        sa.Column("target_id", sa.Text()), sa.Column("target_label", sa.Text()), sa.Column("details", sa.Text()))
    if "studio_settings" not in have:
        op.create_table("studio_settings", sa.Column("key", sa.Text(), primary_key=True), sa.Column("value", sa.Text(), nullable=False),
                        sa.Column("updated", sa.Float(), nullable=False), sa.Column("updated_by", sa.Text()))


def downgrade():
    for t in ("studio_settings", "audit_events", "workflow_team_shares", "team_members", "teams"): op.drop_table(t)
