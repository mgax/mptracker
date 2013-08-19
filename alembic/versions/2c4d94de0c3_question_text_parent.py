revision = '2c4d94de0c3'
down_revision = '3e5cca5cb77'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql


def upgrade():
    op.add_column('question_text', sa.Column('parent', sa.Text()))

    question_text = sql.table('question_text',
        sql.column('parent'))
    op.execute(
        question_text.update()
                     .values({'parent': 'question'}))

    op.alter_column('question_text', 'parent',
               existing_type=sa.TEXT(),
               nullable=False)


def downgrade():
    op.drop_column('question_text', 'parent')
