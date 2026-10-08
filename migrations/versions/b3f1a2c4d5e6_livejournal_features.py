"""LiveJournal-style features: profiles, userpics, moods, security levels, tags, comments, friends.

Revision ID: b3f1a2c4d5e6
Revises: 67a7c8b63cfd
Create Date: 2026-10-08
"""

import sqlalchemy as sa
from alembic import op

revision = "b3f1a2c4d5e6"
down_revision = "67a7c8b63cfd"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user") as batch:
        batch.add_column(sa.Column("display_name", sa.String(50)))
        batch.add_column(sa.Column("bio", sa.Text()))
        batch.add_column(sa.Column("location", sa.String(80)))
        batch.add_column(sa.Column("interests", sa.String(400)))
        batch.add_column(sa.Column("website", sa.String(200)))
        batch.add_column(sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
        batch.drop_column("image_file")  # replaced by userpics stored in the database

    # Old accounts used "theme-default", which no longer exists.
    op.execute("UPDATE \"user\" SET theme = 'theme-light' WHERE theme = 'theme-default' OR theme IS NULL")

    op.create_table(
        "userpic",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("keyword", sa.String(40), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("mimetype", sa.String(30), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "tag",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(40), nullable=False, unique=True),
    )

    with op.batch_alter_table("post") as batch:
        batch.add_column(sa.Column("updated_at", sa.DateTime()))
        batch.add_column(sa.Column("mood", sa.String(40)))
        batch.add_column(sa.Column("music", sa.String(120)))
        batch.add_column(sa.Column("security", sa.String(10), nullable=False, server_default="public"))
        batch.add_column(sa.Column("comments_disabled", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("userpic_id", sa.Integer()))
        batch.create_foreign_key("fk_post_userpic", "userpic", ["userpic_id"], ["id"], ondelete="SET NULL")
        batch.create_index("ix_post_user_id", ["user_id"])
        batch.create_index("ix_post_date_posted", ["date_posted"])

    op.create_table(
        "post_tag",
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("post.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "friendship",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("friend_id", sa.Integer(), sa.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "comment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("post.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("comment.id", ondelete="CASCADE")),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade():
    op.drop_table("comment")
    op.drop_table("friendship")
    op.drop_table("post_tag")
    with op.batch_alter_table("post") as batch:
        batch.drop_constraint("fk_post_userpic", type_="foreignkey")
        batch.drop_index("ix_post_user_id")
        batch.drop_index("ix_post_date_posted")
        for col in ("updated_at", "mood", "music", "security", "comments_disabled", "userpic_id"):
            batch.drop_column(col)
    op.drop_table("tag")
    op.drop_table("userpic")
    with op.batch_alter_table("user") as batch:
        batch.add_column(sa.Column("image_file", sa.String(20), nullable=False, server_default="default.jpg"))
        for col in ("display_name", "bio", "location", "interests", "website", "is_demo", "created_at"):
            batch.drop_column(col)
