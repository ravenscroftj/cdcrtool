"""initial revision

Revision ID: 82b80818eeee
Revises: 
Create Date: 2020-04-17 10:13:40.721245

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '82b80818eeee'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('tasks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('hash', sa.String(length=64), nullable=True),
    sa.Column('news_text', sa.Text(), nullable=True),
    sa.Column('sci_text', sa.Text(), nullable=True),
    sa.Column('news_url', sa.String(length=150), nullable=True),
    sa.Column('sci_url', sa.String(length=150), nullable=True),
    sa.Column('news_ent', sa.String(length=150), nullable=True),
    sa.Column('sci_ent', sa.String(length=150), nullable=True),
    sa.Column('is_iaa', sa.Boolean(), nullable=True),
    sa.Column('is_bad', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('hash')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=50), nullable=True),
    sa.Column('password', sa.String(length=64), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('user_tasks',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('task_id', sa.Integer(), nullable=False),
    sa.Column('answer', sa.String(length=150), nullable=True),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'task_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('user_tasks')
    op.drop_table('users')
    op.drop_table('tasks')
    # ### end Alembic commands ###
