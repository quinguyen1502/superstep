"""Where an external attachment's object is (TASK-0203): the fs folder or the s3 bucket/prefix at write time, so files
stay readable after STUDIO_ATTACHMENT_FS_PATH or the bucket or prefix changes. Existing rows get it at start-up
(AttachmentFiles.backfill_locations), from the settings they were written with."""
from alembic import op
import sqlalchemy as sa

revision = "0048_attachment_location"
down_revision = "0047_attachment_storage"


def upgrade():
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("chat_attachments")}
    if "location" not in cols:
        with op.batch_alter_table("chat_attachments") as b: b.add_column(sa.Column("location", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("chat_attachments") as b: b.drop_column("location")
