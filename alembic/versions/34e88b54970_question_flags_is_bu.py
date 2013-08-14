revision = '34e88b54970'
down_revision = '18783ac030'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('question_flags',
        sa.Column('is_bug', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column('question_flags', 'is_bug')
