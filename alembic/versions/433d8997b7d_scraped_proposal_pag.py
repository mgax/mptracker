revision = '433d8997b7d'
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
        sa.Column('result', sa.Binary(), nullable=True),
        sa.Column('parsed', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('scraped_proposal_page')
