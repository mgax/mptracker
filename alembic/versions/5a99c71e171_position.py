revision = '5a99c71e171'
down_revision = '1b8378b8914'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table('position',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('interval', postgresql.DATERANGE(), nullable=True),
        sa.Column('person_id', postgresql.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['person_id'], ['person.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('position')
