revision = '4d73f8e17e0'
down_revision = '20f47ca3208'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.drop_table('mp_committee_membership')
    op.drop_table('committee_summary')


def downgrade():
    op.create_table('committee_summary',
        sa.Column('id', postgresql.UUID(),
                  autoincrement=False, nullable=False),
        sa.Column('title', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('date', sa.DATE(), autoincrement=False, nullable=True),
        sa.Column('committee', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('pdf_url', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('text', sa.TEXT(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint('id', name='committee_summary_pkey'),
    )
    op.create_table('mp_committee_membership',
        sa.Column('id', postgresql.UUID(),
                  autoincrement=False, nullable=False),
        sa.Column('mp_committee_id', postgresql.UUID(),
                  autoincrement=False, nullable=False),
        sa.Column('mandate_id', postgresql.UUID(),
                  autoincrement=False, nullable=False),
        sa.Column('role', sa.TEXT(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(
            ['mp_committee_id'], ['mp_committee.id'],
            name='mp_committee_membership_mp_committee_id_fkey'),
        sa.PrimaryKeyConstraint('id', name='mp_committee_membership_pkey'),
    )
