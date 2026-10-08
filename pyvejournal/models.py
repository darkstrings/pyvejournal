from __future__ import annotations

from datetime import datetime, timezone

from flask import current_app
from flask_login import AnonymousUserMixin, UserMixin
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Table,
    Text,
    and_,
    func,
    or_,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .extensions import bcrypt, db

THEMES = {
    "theme-classic": "Classic",
    "theme-light": "Light",
    "theme-signalforge": "SignalForge",
    "theme-neondrift": "Neon Drift",
}
DEFAULT_THEME = "theme-classic"

SECURITY_LEVELS = {
    "public": "Public",
    "friends": "Friends only",
    "private": "Private",
}


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalize_theme(name: str | None) -> str:
    if name == "theme-default":  # older accounts
        return "theme-light"
    return name if name in THEMES else DEFAULT_THEME


# "Friends" in the LiveJournal sense: a one-way list of journals you read.
# If A adds B, then B can see A's friends-only entries.
friendship = Table(
    "friendship",
    db.metadata,
    Column("user_id", ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
    Column("friend_id", ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime, nullable=False, default=utcnow),
)

post_tag = Table(
    "post_tag",
    db.metadata,
    Column("post_id", ForeignKey("post.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
)


class User(db.Model, UserMixin):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(20), unique=True)
    email: Mapped[str] = mapped_column(String(120), unique=True)
    password: Mapped[str] = mapped_column(String(60))
    theme: Mapped[str] = mapped_column(String(20), default=DEFAULT_THEME)
    display_name: Mapped[str | None] = mapped_column(String(50))
    bio: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(80))
    interests: Mapped[str | None] = mapped_column(String(400))
    website: Mapped[str | None] = mapped_column(String(200))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, server_default=func.now())

    posts: Mapped[list[Post]] = relationship(back_populates="author", cascade="all, delete-orphan")
    userpics: Mapped[list[Userpic]] = relationship(
        back_populates="user", cascade="all, delete-orphan", order_by="Userpic.id"
    )
    friends: Mapped[list[User]] = relationship(
        secondary=friendship,
        primaryjoin=lambda: User.id == friendship.c.user_id,
        secondaryjoin=lambda: User.id == friendship.c.friend_id,
        order_by=lambda: User.username,
        back_populates="friend_of",
    )
    friend_of: Mapped[list[User]] = relationship(
        secondary=friendship,
        primaryjoin=lambda: User.id == friendship.c.friend_id,
        secondaryjoin=lambda: User.id == friendship.c.user_id,
        order_by=lambda: User.username,
        back_populates="friends",
    )

    # --- passwords ---------------------------------------------------------
    def set_password(self, raw: str) -> None:
        self.password = bcrypt.generate_password_hash(raw).decode("utf-8")

    def check_password(self, raw: str) -> bool:
        try:
            return bcrypt.check_password_hash(self.password, raw)
        except ValueError:
            return False

    # --- password reset tokens --------------------------------------------
    def get_reset_token(self) -> str:
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="password-reset")
        # Include part of the current hash so a token stops working once it's used.
        return s.dumps({"user_id": self.id, "pw": self.password[-10:]})

    @staticmethod
    def verify_reset_token(token: str, max_age: int = 1800) -> User | None:
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="password-reset")
        try:
            data = s.loads(token, max_age=max_age)
        except Exception:
            return None
        user = db.session.get(User, data.get("user_id"))
        if not user or user.password[-10:] != data.get("pw"):
            return None
        return user

    # --- helpers -----------------------------------------------------------
    @property
    def name(self) -> str:
        return self.display_name or self.username

    @property
    def style(self) -> str:
        return normalize_theme(self.theme)

    @property
    def default_userpic(self) -> Userpic | None:
        return next((p for p in self.userpics if p.is_default), self.userpics[0] if self.userpics else None)

    def is_friend(self, other: User) -> bool:
        return other in self.friends

    def interest_list(self) -> list[str]:
        return [i.strip() for i in (self.interests or "").split(",") if i.strip()]

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class Guest(AnonymousUserMixin):
    is_demo = False


class Userpic(db.Model):
    __tablename__ = "userpic"
    MAX_PER_USER = 6

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    keyword: Mapped[str] = mapped_column(String(40))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    mimetype: Mapped[str] = mapped_column(String(30), default="image/webp")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped[User] = relationship(back_populates="userpics")


class Tag(db.Model):
    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)


class Post(db.Model):
    __tablename__ = "post"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    date_posted: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    mood: Mapped[str | None] = mapped_column(String(40))
    music: Mapped[str | None] = mapped_column(String(120))
    security: Mapped[str] = mapped_column(String(10), default="public", server_default="public")
    comments_disabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    userpic_id: Mapped[int | None] = mapped_column(ForeignKey("userpic.id", ondelete="SET NULL"))

    author: Mapped[User] = relationship(back_populates="posts")
    userpic: Mapped[Userpic | None] = relationship()
    tags: Mapped[list[Tag]] = relationship(secondary=post_tag, order_by=lambda: Tag.name)
    comments: Mapped[list[Comment]] = relationship(
        back_populates="post", cascade="all, delete-orphan", order_by="Comment.created_at"
    )

    @property
    def display_userpic(self) -> Userpic | None:
        return self.userpic or self.author.default_userpic

    @property
    def comment_count(self) -> int:
        return sum(1 for c in self.comments if not c.is_deleted)

    def can_view(self, viewer) -> bool:
        if self.security == "public":
            return True
        if not viewer.is_authenticated:
            return False
        if viewer.id == self.user_id:
            return True
        return self.security == "friends" and viewer in self.author.friends

    def __repr__(self) -> str:
        return f"<Post {self.id} {self.title!r}>"


class Comment(db.Model):
    __tablename__ = "comment"
    MAX_DEPTH = 5

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("post.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("comment.id", ondelete="CASCADE"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    post: Mapped[Post] = relationship(back_populates="comments")
    author: Mapped[User] = relationship()
    parent: Mapped[Comment | None] = relationship(remote_side=[id], back_populates="replies")
    replies: Mapped[list[Comment]] = relationship(back_populates="parent", order_by="Comment.created_at")

    @property
    def depth(self) -> int:
        d, node = 0, self.parent
        while node is not None:
            d, node = d + 1, node.parent
        return d


def visible_posts_query(viewer):
    """SELECT for posts the viewer may read (public + own + friends-only from people who friended them)."""
    q = select(Post)
    if not viewer.is_authenticated:
        return q.where(Post.security == "public")
    friended_me = select(friendship.c.user_id).where(friendship.c.friend_id == viewer.id)
    return q.where(
        or_(
            Post.security == "public",
            Post.user_id == viewer.id,
            and_(Post.security == "friends", Post.user_id.in_(friended_me)),
        )
    )


def get_or_create_tags(names: list[str]) -> list[Tag]:
    tags = []
    with db.session.no_autoflush:
        for name in dict.fromkeys(n.strip().lower()[:40] for n in names if n.strip()):
            tag = next((o for o in db.session.new if isinstance(o, Tag) and o.name == name), None)
            tag = tag or db.session.scalar(select(Tag).where(Tag.name == name))
            if not tag:
                tag = Tag(name=name)
                db.session.add(tag)
            tags.append(tag)
    return tags
