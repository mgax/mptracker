revision = '27bf73c8c32'
down_revision = '1c3de973ee8'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table('proposal',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('cdep_serial', sa.Text(), nullable=True),
        sa.Column('proposal_type', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('proposal')
