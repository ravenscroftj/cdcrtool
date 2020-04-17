"""make url columns wider

Revision ID: f70e9245c226
Revises: 82b80818eeee
Create Date: 2020-04-17 10:19:43.480375

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f70e9245c226'
down_revision = '82b80818eeee'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("tasks", "news_url", type_=sa.String(255))


def downgrade():
    op.alter_column("tasks", "news_url", type_=sa.String(150))
