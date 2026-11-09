"""Durable browser session/order metadata."""
from alembic import op
import sqlalchemy as sa

revision='0056_browser_sessions'
down_revision='0055_browser_artifacts'
branch_labels=depends_on=None


def upgrade():
    gate=op.create_table('browser_capacity',sa.Column('id',sa.Text(),primary_key=True),sa.Column('epoch',sa.Integer(),nullable=False))
    op.bulk_insert(gate,[{'id':'global','epoch':0}])
    op.create_table('browser_sessions',sa.Column('id',sa.Text(),primary_key=True),
        sa.Column('owner',sa.Text(),nullable=False),
        *[sa.Column(name,sa.Text(),nullable=False) for name in ['principal_id','run_id','group_id','connection_id','configuration','provider','status']],
        *[sa.Column(name,sa.Integer(),nullable=False) for name in ['lease_generation','next_order','executing_order','wire_sequence']],
        sa.Column('worker_id',sa.Text()),sa.Column('control_secret',sa.Text()),sa.Column('cleanup_pending',sa.Boolean(),nullable=False),
        *[sa.Column(name,sa.Float(),nullable=False) for name in ['created','expires','touched']])
    for name in ['owner','run_id','connection_id','expires']:op.create_index('ix_browser_sessions_'+name,'browser_sessions',[name])
    op.create_table('browser_commands',sa.Column('id',sa.Text(),primary_key=True),
        sa.Column('session_id',sa.Text(),sa.ForeignKey('browser_sessions.id',ondelete='CASCADE'),nullable=False),
        sa.Column('position',sa.Integer(),nullable=False),sa.Column('body_hash',sa.Text(),nullable=False),
        sa.Column('status',sa.Text(),nullable=False),sa.Column('started',sa.Float()),sa.Column('ended',sa.Float()),
        sa.UniqueConstraint('session_id','position',name='uq_browser_commands_position'))
    op.create_index('ix_browser_commands_session_id','browser_commands',['session_id'])


def downgrade():
    op.drop_table('browser_commands');op.drop_table('browser_sessions');op.drop_table('browser_capacity')
