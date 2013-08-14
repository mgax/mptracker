revision = '18783ac030'
down_revision = '44cd9b4c6d8'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('question_flags',
        sa.Column('is_local_topic', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column('question_flags', 'is_local_topic')
