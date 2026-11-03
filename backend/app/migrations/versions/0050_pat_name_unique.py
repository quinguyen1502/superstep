"""Active token names are unique per user in the database (TASK-0213): a partial unique index on (user_id, name) over
rows that are not revoked, so two creates with the same name at the same moment cannot both succeed. Revoked rows are
left out because a revoked token's name can be used again (DEC-0071). Active duplicates already in the table are
renamed first: the oldest keeps the name, later ones get `name (2)`, `name (3)`... like PatService._free_name."""
from alembic import op
import sqlalchemy as sa

revision = "0050_pat_name_unique"
down_revision = "0049_review_recovery"

INDEX = "uq_personal_access_tokens_user_active_name"
WHERE = "revoked IS NULL"
NAME_MAX = 80


def _free(name: str, used: set) -> str:
    n = 1
    while True:
        n += 1; suffix = f" ({n})"
        chosen = name[:NAME_MAX - len(suffix)] + suffix
        if chosen not in used: return chosen


def upgrade():
    bind = op.get_bind()
    if INDEX in {i["name"] for i in sa.inspect(bind).get_indexes("personal_access_tokens")}: return
    rows = bind.execute(sa.text("SELECT id, user_id, name FROM personal_access_tokens WHERE revoked IS NULL "
                                "ORDER BY user_id, created, id")).fetchall()
    used: dict = {}
    for row in rows: used.setdefault(row.user_id, set()).add(row.name)
    seen: set = set()
    for row in rows:
        if (row.user_id, row.name) not in seen:
            seen.add((row.user_id, row.name)); continue
        chosen = _free(row.name, used[row.user_id])
        used[row.user_id].add(chosen); seen.add((row.user_id, chosen))
        bind.execute(sa.text("UPDATE personal_access_tokens SET name = :name WHERE id = :id"), {"name": chosen, "id": row.id})
    op.create_index(INDEX, "personal_access_tokens", ["user_id", "name"], unique=True,
                    sqlite_where=sa.text(WHERE), postgresql_where=sa.text(WHERE))


def downgrade():
    op.drop_index(INDEX, table_name="personal_access_tokens")
