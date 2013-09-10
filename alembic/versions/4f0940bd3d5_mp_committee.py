revision = '4f0940bd3d5'
down_revision = '3ba111e3a8d'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table('mp_committee',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('name', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('mp_committee_membership',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('person_id', postgresql.UUID(), nullable=False),
        sa.Column('mp_committee_id', postgresql.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['mp_committee_id'], ['mp_committee.id']),
        sa.ForeignKeyConstraint(['person_id'], ['person.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('mp_committee_membership')
    op.drop_table('mp_committee')
