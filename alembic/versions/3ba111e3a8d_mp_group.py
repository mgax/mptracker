revision = '3ba111e3a8d'
down_revision = '488b68c48fe'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table('mp_group',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('name', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('mp_group_membership',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('person_id', postgresql.UUID(), nullable=False),
        sa.Column('mp_group_id', postgresql.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['mp_group_id'], ['mp_group.id']),
        sa.ForeignKeyConstraint(['person_id'], ['person.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('mp_group_membership')
    op.drop_table('mp_group')
