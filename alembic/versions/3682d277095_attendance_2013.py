revision = '3682d277095'
down_revision = '521c4fc72f4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_column('mp_committee', 'meetings_2013')
    op.drop_column('mp_committee_membership', 'attended_2013')
    op.add_column('mp_committee_membership',
        sa.Column('attendance_2013', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('mp_committee_membership', 'attendance_2013')
    op.add_column('mp_committee_membership',
        sa.Column('attended_2013', sa.INTEGER(), nullable=True))
    op.add_column('mp_committee',
        sa.Column('meetings_2013', sa.INTEGER(), nullable=True))
