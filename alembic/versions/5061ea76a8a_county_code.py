revision = '5061ea76a8a'
down_revision = '25d50134b28'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


def upgrade():
    op.add_column('county', sa.Column('code', sa.Text(), nullable=True))

    county = table('county', column('code', sa.Text), column('name', sa.Text))
    for code, name in CODES:
        op.execute(
            county.update()
            .where(county.c.name == op.inline_literal(name))
            .values({'code': op.inline_literal(code)})
        )


def downgrade():
    op.drop_column('county', 'code')

CODES = [
    ('AB', "Alba"),
    ('AG', "Argeș"),
    ('AR', "Arad"),
    ('B',  "București"),
    ('BC', "Bacău"),
    ('BH', "Bihor"),
    ('BN', "Bistrița Năsăud"),
    ('BR', "Brăila"),
    ('BT', "Botoșani"),
    ('BV', "Brașov"),
    ('BZ', "Buzău"),
    ('CJ', "Cluj"),
    ('CL', "Călărași"),
    ('CS', "Caraș-Severin"),
    ('CT', "Constanța"),
    ('CV', "Covasna"),
    ('DB', "Dâmbovița"),
    ('DJ', "Dolj"),
    ('GJ', "Gorj"),
    ('GL', "Galați"),
    ('GR', "Giurgiu"),
    ('HD', "Hunedoara"),
    ('HR', "Harghita"),
    ('IF', "Ilfov"),
    ('IL', "Ialomița"),
    ('IS', "Iași"),
    ('MH', "Mehedinți"),
    ('MM', "Maramureș"),
    ('MS', "Mureș"),
    ('NT', "Neamț"),
    ('OT', "Olt"),
    ('PH', "Prahova"),
    ('SB', "Sibiu"),
    ('SJ', "Sălaj"),
    ('SM', "Satu-Mare"),
    ('SV', "Suceava"),
    ('TL', "Tulcea"),
    ('TM', "Timiș"),
    ('TR', "Teleorman"),
    ('VL', "Vâlcea"),
    ('VN', "Vrancea"),
    ('VS', "Vaslui"),
]
