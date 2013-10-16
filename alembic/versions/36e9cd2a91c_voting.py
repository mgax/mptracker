revision = '36e9cd2a91c'
down_revision = '229b3fd2631'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table('voting_session',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('date', sa.Date(), nullable=True),
        sa.Column('subject', sa.Text(), nullable=True),
        sa.Column('cdeppk', sa.Integer(), nullable=True),
        sa.Column('proposal_id', postgresql.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['proposal_id'], ['proposal.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('vote',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('choice', sa.Text(), nullable=True),
        sa.Column('mandate_id', postgresql.UUID(), nullable=False),
        sa.Column('voting_session_id', postgresql.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['mandate_id'], ['mandate.id']),
        sa.ForeignKeyConstraint(['voting_session_id'], ['voting_session.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('vote')
    op.drop_table('voting_session')
