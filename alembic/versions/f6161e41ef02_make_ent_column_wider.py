"""make ent column wider

Revision ID: f6161e41ef02
Revises: f70e9245c226
Create Date: 2020-04-17 10:29:38.654313

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f6161e41ef02'
down_revision = 'f70e9245c226'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("tasks", "sci_ent", type_=sa.String(255))
    op.alter_column("tasks", "news_ent", type_=sa.String(255))


def downgrade():
    op.alter_column("tasks", "sci_ent", type_=sa.String(150))
    op.alter_column("tasks", "news_ent", type_=sa.String(150))
