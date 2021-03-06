"""Add is_difficult task list

Revision ID: 1437e4c3ac82
Revises: a7573d5a6512
Create Date: 2020-06-19 09:57:09.754364

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1437e4c3ac82'
down_revision = 'a7573d5a6512'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('tasks', sa.Column('is_difficult', sa.Boolean(), nullable=True))
    op.add_column('tasks', sa.Column('is_difficult_reported_at', sa.DateTime(), nullable=True))
    op.add_column('tasks', sa.Column('is_difficult_user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'tasks', 'users', ['is_difficult_user_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'is_difficult_user_id')
    op.drop_column('tasks', 'is_difficult_reported_at')
    op.drop_column('tasks', 'is_difficult')
    # ### end Alembic commands ###
