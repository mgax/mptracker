revision = '5272ded7959'
down_revision = '561a34e43dc'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table('mp_committee_membership',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('role', sa.Text(), nullable=True),
        sa.Column('interval', postgresql.DATERANGE(), nullable=False),
        sa.Column('mandate_id', postgresql.UUID(), nullable=False),
        sa.Column('mp_committee_id', postgresql.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['mandate_id'], ['mandate.id']),
        sa.ForeignKeyConstraint(['mp_committee_id'], ['mp_committee.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('mp_committee_membership')
