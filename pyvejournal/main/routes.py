from flask import Blueprint, Response, abort, current_app, render_template, request
from flask_login import current_user
from sqlalchemy import func, select

from ..extensions import db
from ..models import Post, Tag, User, Userpic, post_tag, visible_posts_query

main = Blueprint("main", __name__)


@main.route("/")
@main.route("/home")
def home():
    page = request.args.get("page", 1, type=int)
    posts = db.paginate(
        visible_posts_query(current_user).order_by(Post.date_posted.desc()),
        page=page, per_page=current_app.config["ENTRIES_PER_PAGE"], error_out=False,
    )
    newest_users = db.session.scalars(select(User).where(User.is_demo.is_(False)).order_by(User.created_at.desc(), User.id.desc()).limit(8)).all()
    popular_tags = db.session.execute(
        select(Tag.name, func.count().label("n"))
        .join(post_tag, post_tag.c.tag_id == Tag.id)
        .join(Post, Post.id == post_tag.c.post_id)
        .where(Post.security == "public")
        .group_by(Tag.name)
        .order_by(func.count().desc(), Tag.name)
        .limit(15)
    ).all()
    stats = {
        "journals": db.session.scalar(select(func.count(User.id))),
        "entries": db.session.scalar(select(func.count(Post.id))),
    }
    return render_template(
        "main/home.html", posts=posts, newest_users=newest_users, popular_tags=popular_tags, stats=stats,
    )


@main.route("/tag/<name>")
def tag(name):
    page = request.args.get("page", 1, type=int)
    q = visible_posts_query(current_user).where(Post.tags.any(Tag.name == name.lower())).order_by(Post.date_posted.desc())
    posts = db.paginate(q, page=page, per_page=current_app.config["ENTRIES_PER_PAGE"], error_out=False)
    return render_template("main/tag.html", title=f"Tag: {name}", tag=name, posts=posts)


@main.route("/about")
def about():
    return render_template("main/about.html", title="About")


@main.route("/userpic/<int:pic_id>")
def userpic(pic_id):
    pic = db.session.get(Userpic, pic_id)
    if pic is None:
        abort(404)
    resp = Response(pic.data, mimetype=pic.mimetype)
    # Userpics never change in place (a new upload gets a new id), so cache hard.
    resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return resp
