revision = '25d50134b28'
down_revision = 'b9e0fdc1c7'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table('group_vote',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('choice', sa.Text(), nullable=True),
        sa.Column('voting_session_id', postgresql.UUID(), nullable=False),
        sa.Column('mp_group_id', postgresql.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['mp_group_id'], ['mp_group.id']),
        sa.ForeignKeyConstraint(['voting_session_id'], ['voting_session.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'group_vote_voting_session_id',
        'group_vote',
        ['voting_session_id'],
    )


def downgrade():
    op.drop_table('group_vote')
