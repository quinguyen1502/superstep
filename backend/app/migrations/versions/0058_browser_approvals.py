"""Exact-target browser approvals and explicit waiting-resume handoff."""
from alembic import op
import sqlalchemy as sa

revision='0058_browser_approvals'
down_revision='0057_browser_conv_sessions'
branch_labels=depends_on=None


def upgrade():
    op.add_column('browser_sessions',sa.Column('generation',sa.Integer(),nullable=False,server_default='1'))
    op.add_column('browser_sessions',sa.Column('next_lease_generation',sa.Integer()))
    op.add_column('browser_sessions',sa.Column('next_generation',sa.Integer()))
    op.add_column('browser_commands',sa.Column('wire_sequence',sa.Integer()))
    op.add_column('browser_commands',sa.Column('generation',sa.Integer()))
    op.add_column('approval_waits',sa.Column('browser_intent_id',sa.Text()))
    op.create_table('browser_intents',sa.Column('command_id',sa.Text(),sa.ForeignKey('browser_commands.id',ondelete='CASCADE'),primary_key=True),
        *[sa.Column(name,sa.Text(),nullable=False) for name in ['node_id','status','target_hash','origin','role','text']],
        sa.Column('page_generation',sa.Integer(),nullable=False),
        *[sa.Column(name,sa.Float(),nullable=False) for name in ['created','expires']],
        sa.Column('decided_by',sa.Text()),sa.Column('decided_channel',sa.Text()),
        sa.Column('decided_at',sa.Float()),sa.Column('consumed_at',sa.Float()),sa.Column('resume_after',sa.Float()))
    op.create_index('ix_browser_intents_expires','browser_intents',['expires'])


def downgrade():
    op.drop_table('browser_intents')
    op.drop_column('approval_waits','browser_intent_id')
    op.drop_column('browser_commands','generation')
    op.drop_column('browser_commands','wire_sequence')
    for name in ['next_generation','next_lease_generation','generation']:op.drop_column('browser_sessions',name)
