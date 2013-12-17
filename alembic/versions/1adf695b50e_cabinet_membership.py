revision = '1adf695b50e'
down_revision = '5a99c71e171'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table('cabinet_membership',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('interval', postgresql.DATERANGE(), nullable=False),
        sa.Column('mp_group_id', postgresql.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['mp_group_id'], ['mp_group.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('cabinet_membership')
