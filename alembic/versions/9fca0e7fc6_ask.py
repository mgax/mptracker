revision = '9fca0e7fc6'
down_revision = '40132825652'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column, select
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table('ask',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('question_id', postgresql.UUID(), nullable=False),
        sa.Column('mandate_id', postgresql.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['mandate_id'], ['mandate.id']),
        sa.ForeignKeyConstraint(['question_id'], ['question.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    op.execute("INSERT INTO ask (id, question_id, mandate_id) "
                 "SELECT uuid_generate_v4(), id, mandate_id "
                 "FROM question")

    op.drop_column('question', 'mandate_id')

    op.create_table('ask_flags',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('is_local_topic', sa.Boolean(), nullable=True),
        sa.Column('is_bug', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['id'], ['ask.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.execute("INSERT INTO ask_flags(id, is_local_topic, is_bug) "
               "SELECT ask.id, is_local_topic, is_bug "
               "FROM question_flags "
               "JOIN ask ON question_flags.id = ask.question_id")

    op.drop_table('question_flags')

    op.execute("UPDATE match SET parent='ask', id=ask.id "
               "FROM ask "
               "WHERE parent = 'question' AND match.id = ask.question_id")


def downgrade():
    op.execute("UPDATE match SET parent='question', id=ask.question_id "
               "FROM ask "
               "WHERE parent = 'ask' AND match.id = ask.id")

    op.create_table('question_flags',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('is_local_topic', sa.Boolean(), nullable=True),
        sa.Column('is_bug', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['id'], ['question.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.execute("INSERT INTO question_flags(id, is_local_topic, is_bug) "
               "SELECT ask.question_id, is_local_topic, is_bug "
               "FROM ask_flags "
               "JOIN ask ON ask_flags.id = ask.id")

    op.drop_table('ask_flags')

    op.add_column('question',
        sa.Column('mandate_id', postgresql.UUID(), nullable=True))

    op.execute("ALTER TABLE question "
               "ADD FOREIGN KEY(mandate_id) REFERENCES mandate (id)")

    op.execute("UPDATE question SET mandate_id = ask.mandate_id "
               "FROM ask "
               "WHERE question.id = ask.question_id")

    op.drop_table('ask')
