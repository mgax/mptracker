revision = '1c3de973ee8'
down_revision = '38579825699'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table('question_text',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('text', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['id'], ['question.id']),
        sa.PrimaryKeyConstraint('id')
    )


    question = sql.table('question',
        sql.column('id'),
        sql.column('text'))
    question_text = sql.table('question_text',
        sql.column('id'),
        sql.column('text'))

    op.execute(
        question_text.insert().from_select(
            ['id', 'text'],
            question.select().where(question.c.text != None)))

    op.drop_column('question', 'text')


def downgrade():
    raise RuntimeError("Too lazy to write backwards migration :(")
    op.add_column('question', sa.Column('text', sa.Text(), nullable=True))
    op.drop_table('question_text')
