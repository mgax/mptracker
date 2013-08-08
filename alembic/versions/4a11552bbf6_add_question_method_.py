revision = '4a11552bbf6'
down_revision = '55c5ed2b4d5'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('question', sa.Column('method', sa.String(), nullable=True))


def downgrade():
    op.drop_column('question', 'method')
