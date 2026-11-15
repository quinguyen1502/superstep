"""Drop cell snapshots from Dataset write receipts and index their expiry."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0069_dataset_receipt_retention"
down_revision = "0068_dataset_team_owner"
branch_labels = depends_on = None

_receipts = sa.table(
    "dataset_write_receipts",
    sa.column("dataset_id", sa.String),
    sa.column("scope", sa.String),
    sa.column("operation_id", sa.String),
    sa.column("created", sa.Float),
    sa.column("result", sa.JSON().with_variant(JSONB(), "postgresql")),
)
_key = (_receipts.c.dataset_id, _receipts.c.scope, _receipts.c.operation_id)


def _rewrite(convert):
    connection = op.get_bind()
    base = sa.select(*_key, _receipts.c.created, _receipts.c.result).order_by(*_key).limit(200)
    batch = base
    update_payload = _receipts.update().where(
        *(column == sa.bindparam(f"old_{column.name}") for column in _key)
    ).values(result=sa.bindparam("new_result"))
    while records := connection.execute(batch).all():
        changed = []
        for dataset_id, scope, operation_id, created, old in records:
            new = convert(old, created)
            if new != old:
                changed.append({
                    "old_dataset_id": dataset_id, "old_scope": scope, "old_operation_id": operation_id,
                    "new_result": new,
                })
        if changed:
            connection.execute(update_payload, changed)
        batch = base.where(sa.tuple_(*_key) > sa.tuple_(*records[-1][:3]))


def _minimize(result, _created):
    if "row" not in result:
        return result
    row = result["row"]
    return {"row_id": row["id"], "revision": row["revision"], "inserted": result["inserted"]}


def _legacy_shape(result, created):
    if "inserted" not in result:
        return result
    # The previous binary expects a row snapshot. Cell values are irrecoverable.
    return {
        "row": {
            "id": result["row_id"], "revision": result["revision"],
            "values": {}, "created": created, "updated": created,
        },
        "inserted": result["inserted"],
    }


def upgrade():
    _rewrite(_minimize)
    op.create_index("ix_dataset_write_receipts_created", "dataset_write_receipts", ["created"])


def downgrade():
    op.drop_index("ix_dataset_write_receipts_created", table_name="dataset_write_receipts")
    _rewrite(_legacy_shape)
