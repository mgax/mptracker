revision = '5994be361ba'
down_revision = '9fca0e7fc6'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table('meta',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('object_id', postgresql.UUID(), nullable=True),
        sa.Column('key', sa.Text(), nullable=True),
        sa.Column('value', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.execute("INSERT INTO meta(id, object_id, key, value) "
                   "SELECT uuid_generate_v4(), id, 'is_local_topic', 'true' "
                   "FROM ask_flags "
                   "WHERE is_local_topic = true")

    op.execute("INSERT INTO meta(id, object_id, key, value) "
                   "SELECT uuid_generate_v4(), id, 'is_local_topic', 'false' "
                   "FROM ask_flags "
                   "WHERE is_local_topic = false")

    op.execute("INSERT INTO meta(id, object_id, key, value) "
                   "SELECT uuid_generate_v4(), id, 'is_bug', 'true' "
                   "FROM ask_flags "
                   "WHERE is_bug = true")

    op.drop_table('ask_flags')


def downgrade():
    op.create_table('ask_flags',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('is_local_topic', sa.Boolean(), nullable=True),
        sa.Column('is_bug', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['id'], ['ask.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.execute("INSERT INTO ask_flags(id) "
                   "SELECT DISTINCT object_id FROM meta")

    op.execute("UPDATE ask_flags SET is_local_topic = true "
                   "FROM meta "
                   "WHERE ask_flags.id = meta.object_id AND "
                         "meta.key = 'is_local_topic' AND "
                         "meta.value = 'true'")

    op.execute("UPDATE ask_flags SET is_local_topic = false "
                   "FROM meta "
                   "WHERE ask_flags.id = meta.object_id AND "
                         "meta.key = 'is_local_topic' AND "
                         "meta.value = 'false'")

    op.execute("UPDATE ask_flags SET is_bug = true "
                   "FROM meta "
                   "WHERE ask_flags.id = meta.object_id AND "
                         "meta.key = 'is_bug' AND "
                         "meta.value = 'true'")

    op.drop_table('meta')
