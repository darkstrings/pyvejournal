from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, select

from ..extensions import db
from ..models import Post, Tag, User, friendship, post_tag, visible_posts_query

bp = Blueprint("journal", __name__)


def get_user(username) -> User:
    user = db.session.scalar(select(User).where(func.lower(User.username) == username.lower()))
    if user is None:
        abort(404)
    return user


def paginate(query):
    page = request.args.get("page", 1, type=int)
    return db.paginate(query, page=page, per_page=current_app.config["ENTRIES_PER_PAGE"], error_out=False)


def journal_tags(user):
    """Tags used in this journal (counting only entries the viewer can see)."""
    visible = visible_posts_query(current_user).where(Post.user_id == user.id).subquery()
    rows = db.session.execute(
        select(Tag.name, func.count())
        .join(post_tag, post_tag.c.tag_id == Tag.id)
        .join(visible, visible.c.id == post_tag.c.post_id)
        .group_by(Tag.name)
        .order_by(Tag.name)
    ).all()
    return rows


@bp.route("/journal/<username>")
def journal(username):
    user = get_user(username)
    q = visible_posts_query(current_user).where(Post.user_id == user.id).order_by(Post.date_posted.desc())
    tag = request.args.get("tag")
    if tag:
        q = q.where(Post.tags.any(Tag.name == tag.lower()))
    return render_template(
        "journal/journal.html", title=f"{user.name}'s Journal", user=user, journal_owner=user,
        posts=paginate(q), tag=tag, tags=journal_tags(user),
    )


@bp.route("/journal/<username>/profile")
def profile(username):
    user = get_user(username)
    entry_count = db.session.scalar(
        select(func.count()).select_from(visible_posts_query(current_user).where(Post.user_id == user.id).subquery())
    )
    return render_template(
        "journal/profile.html", title=f"User info: {user.username}", user=user, journal_owner=user,
        entry_count=entry_count, tags=journal_tags(user),
    )


@bp.route("/journal/<username>/friends")
def friends_page(username):
    """A journal's friends page: recent entries from everyone they've friended (what the viewer may see)."""
    user = get_user(username)
    friend_ids = select(friendship.c.friend_id).where(friendship.c.user_id == user.id)
    q = (
        visible_posts_query(current_user)
        .where(Post.user_id.in_(friend_ids) | (Post.user_id == user.id))
        .order_by(Post.date_posted.desc())
    )
    return render_template(
        "journal/friends.html", title=f"{user.name}'s Friends", user=user, journal_owner=user, posts=paginate(q),
    )


@bp.route("/friends")
@login_required
def my_friends():
    return redirect(url_for("journal.friends_page", username=current_user.username))


@bp.route("/journal/<username>/friend", methods=["POST"])
@login_required
def toggle_friend(username):
    user = get_user(username)
    if user == current_user:
        abort(400)
    if user in current_user.friends:
        current_user.friends.remove(user)
        flash(f"Removed {user.username} from your friends.", "info")
    else:
        current_user.friends.append(user)
        flash(f"Added {user.username} as a friend! Their entries now show on your friends page, "
              "and they can read your friends-only entries.", "success")
    db.session.commit()
    return redirect(request.form.get("next") if (request.form.get("next") or "").startswith("/journal/")
                    else url_for("journal.journal", username=user.username))
