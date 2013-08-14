revision = 'aca6937e73'
down_revision = '58f2cb9046f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('committee_summary',
        sa.Column('text', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('committee_summary', 'text')
