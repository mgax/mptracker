revision = '521c4fc72f4'
down_revision = '26522536691'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column(
        'mp_committee',
        sa.Column('meetings_2013', sa.Integer(), nullable=True),
    )
    op.add_column(
        'mp_committee_membership',
        sa.Column('attended_2013', sa.Integer(), nullable=True),
    )


def downgrade():
    op.drop_column('mp_committee_membership', 'attended_2013')
    op.drop_column('mp_committee', 'meetings_2013')
