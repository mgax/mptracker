revision = '619369f92a'
down_revision = '3216a0bd78a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column(
        'proposal_controversy',
        sa.Column('title', sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_column('proposal_controversy', 'title')
