revision = '191d638f4fb'
down_revision = '2c4d94de0c3'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.rename_table('question_text', 'ocr_text')


def downgrade():
    op.rename_table('ocr_text', 'question_text')
