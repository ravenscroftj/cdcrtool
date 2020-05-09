"""Separate news and science content from task

Revision ID: 7ddae5807eae
Revises: 921f9c6e9456
Create Date: 2020-05-09 10:31:55.513006

"""
from tqdm.auto import tqdm
from alembic import op
import sqlalchemy as sa
from sqlalchemy import orm

from cdcrapp.model import NewsArticle, SciPaper

# revision identifiers, used by Alembic.
revision = '7ddae5807eae'
down_revision = '921f9c6e9456'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('newsarticles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('url', sa.String(length=255), nullable=True),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('scipapers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('url', sa.String(length=150), nullable=True),
    sa.Column('abstract', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('tasks', sa.Column('news_article_id', sa.Integer(), nullable=True))
    op.add_column('tasks', sa.Column('sci_paper_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'tasks', 'scipapers', ['sci_paper_id'], ['id'])
    op.create_foreign_key(None, 'tasks', 'newsarticles', ['news_article_id'], ['id'])
    # ### end Alembic commands ###

    conn = op.get_bind()
    session = orm.Session(bind=conn)

    for url, text in conn.execute("SELECT news_url, news_text from tasks GROUP BY news_url, news_text"):
        na = NewsArticle(url=url, summary=text)
        session.add(na)

    for url, text in conn.execute("SELECT sci_url, sci_text from tasks GROUP BY sci_url, sci_text"):
        sp = SciPaper(url=url, abstract=text)
        session.add(sp)

    session.commit()

    from sqlalchemy.sql import text

    papercount = session.query(SciPaper).count()
    articlecount = session.query(NewsArticle).count()

    for sp in tqdm(session.query(SciPaper).all(), total=papercount):
        conn.execute(text("UPDATE tasks SET sci_paper_id=:id WHERE sci_url=:url"), id=sp.id, url=sp.url)

    for na in tqdm(session.query(NewsArticle).all(), total=articlecount):
        conn.execute(text("UPDATE tasks SET news_article_id=:id WHERE news_url=:url"), id=na.id, url=na.url)


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'tasks', type_='foreignkey')
    op.drop_constraint(None, 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'sci_paper_id')
    op.drop_column('tasks', 'news_article_id')
    op.drop_table('scipapers')
    op.drop_table('newsarticles')
    # ### end Alembic commands ###

    conn = op.get_bind()
    session = orm.Session(bind=conn)


    from sqlalchemy.sql import text

    papercount = session.query(SciPaper).count()
    articlecount = session.query(NewsArticle).count()

    for sp in tqdm(session.query(SciPaper).all(), total=papercount):
        conn.execute(text("UPDATE tasks SET sci_url=:url, sci_text=:text WHERE sci_paper_id=:id"), id=sp.id, url=sp.url, text=sp.abstract)

    for na in tqdm(session.query(NewsArticle).all(), total=articlecount):
        conn.execute(text("UPDATE tasks SET news_url=:url, news_text=:text WHERE news_article_id=:id"), id=na.id, url=na.url, text=na.summary)
