revision = 'c9230f65c6'
down_revision = '32590709513'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('proposal', sa.Column('status', sa.Text(), nullable=True))
    op.add_column('proposal', sa.Column('status_text', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('proposal', 'status_text')
    op.drop_column('proposal', 'status')
