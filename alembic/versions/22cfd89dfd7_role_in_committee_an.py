revision = '22cfd89dfd7'
down_revision = '17fc4edda5c'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('mp_committee_membership',
        sa.Column('role', sa.Text(), nullable=True))
    op.add_column('mp_group_membership',
        sa.Column('role', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('mp_group_membership', 'role')
    op.drop_column('mp_committee_membership', 'role')
