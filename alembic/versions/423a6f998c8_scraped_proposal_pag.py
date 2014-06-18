revision = '423a6f998c8'
down_revision = '4ace23c68ca'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table(
        'scraped_proposal_page',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('chamber', sa.Integer(), nullable=True),
        sa.Column('pk', sa.Integer(), nullable=True),
        sa.Column('date', sa.Date(), nullable=True),
        sa.Column('value', sa.Binary(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('scraped_proposal_page')
