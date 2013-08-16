revision = '4bc50a6cca9'
down_revision = 'aca6937e73'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table('question_match',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('data', sa.Text(), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['id'], ['question.id']),
        sa.PrimaryKeyConstraint('id')
    )

    question = sql.table('question',
        sql.column('id'),
        sql.column('match_data'),
        sql.column('match_score'))
    question_match = sql.table('question_match',
        sql.column('id'),
        sql.column('data'),
        sql.column('score'))

    op.execute(
        question_match.insert().from_select(
            ['id', 'data', 'score'],
            question.select().where(question.c.match_data != None)))

    op.drop_column('question', 'match_data')
    op.drop_column('question', 'match_score')


def downgrade():
    raise RuntimeError("Too lazy to write backwards migration :(")
    op.add_column('question',
        sa.Column('match_score', sa.Float(), nullable=True))
    op.add_column('question',
        sa.Column('match_data', sa.Text(), nullable=True))
    op.drop_table('question_match')
