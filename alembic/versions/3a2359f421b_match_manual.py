revision = '3a2359f421b'
down_revision = '8dac320dea'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('match', sa.Column('manual', sa.Boolean(), nullable=True))
    op.execute("UPDATE match SET manual = false")
    op.alter_column('match', 'manual', nullable=False)

    op.execute(
        "INSERT INTO match(id, parent, manual) "
        "SELECT object_id, 'ask', true "
        "FROM meta "
        "LEFT JOIN match ON meta.object_id = match.id "
        "WHERE match.id IS NULL AND meta.key = 'is_local_topic'"
    )

    op.execute(
        "UPDATE match "
        "SET manual = true, score = 11 "
        "FROM ( "
        "    SELECT object_id, value "
        "    FROM meta "
        "    WHERE key='is_local_topic' AND value = 'true' "
        "  ) AS meta_row "
        "WHERE match.id = meta_row.object_id"
    )

    op.execute(
        "UPDATE match "
        "SET manual = true, score = 0 "
        "FROM ( "
        "    SELECT object_id, value "
        "    FROM meta "
        "    WHERE key='is_local_topic' AND value = 'false' "
        "  ) AS meta_row "
        "WHERE match.id = meta_row.object_id"
    )

    op.execute("DELETE FROM meta WHERE key = 'is_local_topic'")


def downgrade():
    raise RuntimeError(
        "Downgrade causes data loss. "
        "Comment out this line to run it anyway."
    )
    op.execute("DELETE FROM match WHERE data IS NULL")
    op.drop_column('match', 'manual')
