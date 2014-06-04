revision = '18be3a9d7a1'
down_revision = '7d8040095e'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.drop_column('controversy', 'slug')
    op.drop_column('voting_session', 'controversy_id')

    op.execute("DELETE FROM controversy")

    op.rename_table('controversy', 'voting_session_controversy')

    op.add_column('voting_session_controversy',
        sa.Column('press_links', sa.Text(), nullable=True))
    op.add_column('voting_session_controversy',
        sa.Column('reason', sa.Text(), nullable=True))
    op.add_column('voting_session_controversy',
        sa.Column('status', sa.Text(), nullable=True))
    op.add_column('voting_session_controversy',
        sa.Column('vote_meaning_no', sa.Text(), nullable=True))
    op.add_column('voting_session_controversy',
        sa.Column('vote_meaning_yes', sa.Text(), nullable=True))
    op.add_column('voting_session_controversy',
        sa.Column('voting_session_id', postgresql.UUID(), nullable=False))


def downgrade():
    op.execute("DELETE FROM voting_session_controversy")

    op.drop_column('voting_session_controversy', 'voting_session_id')
    op.drop_column('voting_session_controversy', 'vote_meaning_yes')
    op.drop_column('voting_session_controversy', 'vote_meaning_no')
    op.drop_column('voting_session_controversy', 'status')
    op.drop_column('voting_session_controversy', 'reason')
    op.drop_column('voting_session_controversy', 'press_links')

    op.rename_table('voting_session_controversy', 'controversy')

    op.add_column('voting_session',
        sa.Column('controversy_id', postgresql.UUID(), nullable=True))
    op.add_column('controversy',
        sa.Column('slug', sa.TEXT(), nullable=False))
