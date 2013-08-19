revision = '3648e45fb93'
down_revision = '27bf73c8c32'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table('sponsors',
        sa.Column('person_id', postgresql.UUID(), nullable=True),
        sa.Column('proposal_id', postgresql.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['person_id'], ['person.id']),
        sa.ForeignKeyConstraint(['proposal_id'], ['proposal.id']),
        sa.PrimaryKeyConstraint()
    )


def downgrade():
    op.drop_table('sponsors')
