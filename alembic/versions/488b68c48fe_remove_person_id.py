revision = '488b68c48fe'
down_revision = '4939e91a8b3'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.drop_column('person', 'cdep_id')
    op.drop_column('person', 'minority')
    op.drop_column('person', 'county_id')

    op.drop_column('question', 'person_id')
    op.drop_column('sponsorship', 'person_id')
    op.drop_column('steno_paragraph', 'person_id')

    op.alter_column('sponsorship', 'mandate_id',
               existing_type=postgresql.UUID(),
               nullable=False)


def downgrade():
    op.alter_column('sponsorship', 'mandate_id',
               existing_type=postgresql.UUID(),
               nullable=True)

    op.add_column('steno_paragraph',
        sa.Column('person_id', postgresql.UUID(), nullable=True))
    op.add_column('sponsorship',
        sa.Column('person_id', postgresql.UUID(), nullable=True))
    op.add_column('question',
        sa.Column('person_id', postgresql.UUID(), nullable=True))

    op.add_column('person',
        sa.Column('county_id', postgresql.UUID(), nullable=True))
    op.add_column('person',
        sa.Column('minority', sa.BOOLEAN(), nullable=True))
    op.add_column('person',
        sa.Column('cdep_id', sa.TEXT(), nullable=True))


def deduplicate_people():
    from mptracker.models import db, Mandate
    people = {}
    unique = removed = 0
    for mandate in Mandate.query.join(Mandate.person):
        person = mandate.person
        name = person.name
        if name in people:
            assert mandate.year not in people[name]
            print("-->", name, mandate.year)
            mandate.person = people[name]['default']
            db.session.delete(person)
            people[name][mandate.year] = True
            removed += 1
        else:
            print(">>>", name, mandate.year)
            people[name] = {
                'default': person,
                mandate.year: True,
            }
            unique += 1
    print("unique:", unique, "removed:", removed)
    db.session.flush()
