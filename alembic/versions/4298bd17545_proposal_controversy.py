revision = '4298bd17545'
down_revision = '3682d277095'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table('proposal_controversy',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('press_links', sa.Text(), nullable=True),
        sa.Column('proposal_id', postgresql.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['proposal_id'], ['proposal.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('proposal_controversy')
