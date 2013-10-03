revision = '25d765ee53b'
down_revision = '20dce5e4682'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.rename_table('steno_paragraph', 'transcript')
    op.rename_table('steno_chapter', 'transcript_chapter')


def downgrade():
    op.rename_table('transcript_chapter', 'steno_chapter')
    op.rename_table('transcript', 'steno_paragraph')
