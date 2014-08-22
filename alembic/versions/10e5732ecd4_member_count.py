revision = '10e5732ecd4'
down_revision = '2635be0d80f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'member_count',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('short_name', sa.Text(), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('count', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('member_count')
