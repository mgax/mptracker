revision = '7d8040095e'
down_revision = '4298bd17545'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table('answer',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('pdf_url', sa.Text(), nullable=True),
        sa.Column('question_id', postgresql.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['question.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('answer')
