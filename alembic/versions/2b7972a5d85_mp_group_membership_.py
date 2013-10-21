revision = '2b7972a5d85'
down_revision = '36e9cd2a91c'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.add_column('mp_group_membership',
        sa.Column('interval', postgresql.DATERANGE()),
    )
    op.execute(
        "update mp_group_membership "
        "set interval = daterange('2012-12-19', 'infinity')"
    )
    op.alter_column('mp_group_membership', 'interval', nullable=False)


def downgrade():
    op.drop_column('mp_group_membership', 'interval')
