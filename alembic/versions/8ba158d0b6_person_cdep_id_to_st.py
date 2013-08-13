revision = '8ba158d0b6'
down_revision = '4a11552bbf6'

from alembic import op
import sqlalchemy as sa


def get_table_definition():
    from sqlalchemy.dialects.postgresql import UUID
    metadata = sa.MetaData()
    Person = sa.Table('person', metadata,
        sa.Column('id', UUID),
        sa.Column('cdep_id', sa.Text, nullable=True),
        sa.Column('cdep_id_int', sa.Integer, nullable=True),
    )
    return Person


def migrate_data(conn, table, updater):
    new_values = [(row.id, updater(row))
                  for row in conn.execute(table.select())]
    for id_, values in new_values:
        if values:
            conn.execute(table.update()
                              .where(table.c.id == id_)
                              .values(**values))


def upgrade():
    op.alter_column('person', 'cdep_id', new_column_name='cdep_id_int')
    op.add_column('person', sa.Column('cdep_id', sa.Text, nullable=True))

    def stringify_cdep_id(row):
        if row.cdep_id_int is not None:
            return {'cdep_id': '2008-%03d' % row.cdep_id_int}

    migrate_data(table=get_table_definition(),
                 conn=op.get_bind(),
                 updater=stringify_cdep_id)

    op.drop_column('person', 'cdep_id_int')


def downgrade():
    op.add_column('person', sa.Column('cdep_id_int', sa.Integer(), nullable=True))
    conn = op.get_bind()

    def integer_cdep_id(row):
        if row.cdep_id is not None:
            assert row.cdep_id.startswith('2008-')
            return {'cdep_id_int': int(row.cdep_id.split('-')[1])}

    migrate_data(table=get_table_definition(),
                 conn=op.get_bind(),
                 updater=integer_cdep_id)

    op.drop_column('person', 'cdep_id')
    op.alter_column('person', 'cdep_id_int', new_column_name='cdep_id')
