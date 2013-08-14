revision = '44cd9b4c6d8'
down_revision = '8ba158d0b6'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table('question_flags',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['id'], ['question.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('question_flags')
