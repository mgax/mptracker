revision = '17fc4edda5c'
down_revision = '22900728ca6'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.add_column('mp_committee_membership',
        sa.Column('mandate_id', postgresql.UUID(), nullable=False))
    op.drop_column('mp_committee_membership', 'person_id')

    op.add_column('mp_group_membership',
        sa.Column('mandate_id', postgresql.UUID(), nullable=False))
    op.drop_column('mp_group_membership', 'person_id')


def downgrade():
    op.add_column('mp_group_membership',
        sa.Column('person_id', postgresql.UUID(), nullable=False))
    op.drop_column('mp_group_membership', 'mandate_id')

    op.add_column('mp_committee_membership',
        sa.Column('person_id', postgresql.UUID(), nullable=False))
    op.drop_column('mp_committee_membership', 'mandate_id')
