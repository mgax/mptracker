revision = '58f2cb9046f'
down_revision = '34e88b54970'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table('committee_summary',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('date', sa.Date(), nullable=True),
        sa.Column('committee', sa.Text(), nullable=True),
        sa.Column('pdf_url', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('committee_summary')
