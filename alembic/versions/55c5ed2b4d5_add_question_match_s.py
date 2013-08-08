revision = '55c5ed2b4d5'
down_revision = 'ec91f26983'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('question', sa.Column('match_score', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('question', 'match_score')
