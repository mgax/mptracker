revision = '197c7328f64'
down_revision = '1659018fc4d'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql
from sqlalchemy.dialects import postgresql

def upgrade():
    op.rename_table('question_match', 'match')
    op.drop_constraint('question_match_id_fkey', 'match')
    op.add_column('match', sa.Column('parent', sa.Text()))

    match = sql.table('match', sql.column('parent'))
    op.execute(match.update().values({'parent': 'question'}))

    op.alter_column('match', 'parent', existing_type=sa.TEXT(), nullable=False)


def downgrade():
    op.drop_column('match', 'parent')
    op.rename_table('match', 'question_match')
    op.create_foreign_key('question_match_id_fkey',
        'question_match', 'question', ['id'], ['id'])
