revision = '22900728ca6'
down_revision = '4f0940bd3d5'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('mandate', sa.Column('address', sa.Text(), nullable=True))
    op.add_column('mandate', sa.Column('college', sa.Integer(), nullable=True))
    op.add_column('mandate', sa.Column('constituency', sa.Integer(), nullable=True))
    op.add_column('mandate', sa.Column('phone', sa.Text(), nullable=True))
    op.add_column('mandate', sa.Column('votes', sa.Integer(), nullable=True))
    op.add_column('mandate', sa.Column('votes_percent', sa.Numeric(), nullable=True))

    op.add_column('person', sa.Column('blog_url', sa.Text(), nullable=True))
    op.add_column('person', sa.Column('education', sa.Text(), nullable=True))
    op.add_column('person', sa.Column('email_value', sa.Text(), nullable=True))
    op.add_column('person', sa.Column('facebook_url', sa.Text(), nullable=True))
    op.add_column('person', sa.Column('twitter_url', sa.Text(), nullable=True))
    op.add_column('person', sa.Column('website_url', sa.Text(), nullable=True))
    op.add_column('person', sa.Column('year_born', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('person', 'year_born')
    op.drop_column('person', 'website_url')
    op.drop_column('person', 'twitter_url')
    op.drop_column('person', 'facebook_url')
    op.drop_column('person', 'email_value')
    op.drop_column('person', 'education')
    op.drop_column('person', 'blog_url')

    op.drop_column('mandate', 'votes_percent')
    op.drop_column('mandate', 'votes')
    op.drop_column('mandate', 'phone')
    op.drop_column('mandate', 'constituency')
    op.drop_column('mandate', 'college')
    op.drop_column('mandate', 'address')
