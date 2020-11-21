"""uniqueid 

Revision ID: c3a3a682e1d3
Revises: b6374b96937e
Create Date: 2020-11-21 09:12:06.243349

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3a3a682e1d3'
down_revision = 'b6374b96937e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('booking', sa.Column('unique_id', sa.Integer(), nullable=True))
    op.create_unique_constraint(None, 'booking', ['unique_id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'booking', type_='unique')
    op.drop_column('booking', 'unique_id')
    # ### end Alembic commands ###
