"""Add priority column

Revision ID: a7573d5a6512
Revises: ada801bded08
Create Date: 2020-06-12 12:06:56.692352

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7573d5a6512'
down_revision = 'ada801bded08'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('tasks', sa.Column('priority', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('tasks', 'priority')
    # ### end Alembic commands ###