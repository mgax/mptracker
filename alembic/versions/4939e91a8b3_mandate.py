revision = '4939e91a8b3'
down_revision = '2dc81b310cf'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table('mandate',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('cdep_number', sa.Integer(), nullable=True),
        sa.Column('minority', sa.Boolean(), nullable=True),
        sa.Column('person_id', postgresql.UUID(), nullable=False),
        sa.Column('chamber_id', postgresql.UUID(), nullable=False),
        sa.Column('county_id', postgresql.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['chamber_id'], ['chamber.id']),
        sa.ForeignKeyConstraint(['county_id'], ['county.id']),
        sa.ForeignKeyConstraint(['person_id'], ['person.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.add_column('question',
        sa.Column('mandate_id', postgresql.UUID(), nullable=True))
    op.add_column('sponsorship',
        sa.Column('mandate_id', postgresql.UUID(), nullable=True))
    op.add_column('steno_paragraph',
        sa.Column('mandate_id', postgresql.UUID(), nullable=True))

    op.alter_column('sponsorship', 'person_id',
               existing_type=postgresql.UUID(),
               nullable=True)


def downgrade():
    op.alter_column('sponsorship', 'person_id',
               existing_type=postgresql.UUID(),
               nullable=False)

    op.drop_column('steno_paragraph', 'mandate_id')
    op.drop_column('sponsorship', 'mandate_id')
    op.drop_column('question', 'mandate_id')

    op.drop_table('mandate')
