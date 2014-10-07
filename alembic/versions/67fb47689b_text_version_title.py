revision = '67fb47689b'
down_revision = '619369f92a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('text_version', sa.Column('title', sa.Text(), nullable=True))
    op.execute("UPDATE text_version SET title=''")
    op.alter_column('text_version', 'title', nullable=False)
    op.alter_column('text_version', 'content', nullable=False)
    op.alter_column('text_version', 'more_content', nullable=False)


def downgrade():
    op.alter_column('text_version', 'more_content', nullable=True)
    op.alter_column('text_version', 'content', nullable=True)
    op.drop_column('text_version', 'title')
