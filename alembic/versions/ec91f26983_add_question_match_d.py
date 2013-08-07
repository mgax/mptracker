revision = 'ec91f26983'
down_revision = 'b0a6720166'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('question', sa.Column('match_data', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('question', 'match_data')
