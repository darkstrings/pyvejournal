from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db, limiter
from ..models import Comment, Post, get_or_create_tags, utcnow
from .forms import CommentForm, PostForm

posts = Blueprint("posts", __name__)


def _userpic_choices():
    return [(0, "Default")] + [(p.id, p.keyword) for p in current_user.userpics]


def _fill_post(post: Post, form: PostForm):
    post.title = form.title.data.strip()
    post.content = form.content.data
    post.mood = (form.mood.data or "").strip() or None
    post.music = (form.music.data or "").strip() or None
    post.security = form.security.data
    post.comments_disabled = form.comments_disabled.data
    pic_ids = {p.id for p in current_user.userpics}
    post.userpic_id = form.userpic_id.data if form.userpic_id.data in pic_ids else None
    post.tags = get_or_create_tags((form.tags.data or "").split(","))


def get_visible_post(post_id) -> Post:
    post = db.session.get(Post, post_id)
    # 404 (not 403) for hidden entries so their existence isn't revealed.
    if post is None or not post.can_view(current_user):
        abort(404)
    return post


@posts.route("/post/new", methods=["GET", "POST"])
@login_required
@limiter.limit("30/hour", methods=["POST"])
def new_post():
    form = PostForm()
    form.userpic_id.choices = _userpic_choices()
    if form.validate_on_submit():
        post = Post(author=current_user)
        _fill_post(post, form)
        db.session.add(post)
        db.session.commit()
        flash("Entry posted!", "success")
        return redirect(url_for("posts.post", post_id=post.id))
    return render_template("posts/edit.html", title="Post an entry", form=form, legend="Post an entry")


@posts.route("/post/<int:post_id>")
def post(post_id):
    post = get_visible_post(post_id)
    form = CommentForm()
    top_level = [c for c in post.comments if c.parent_id is None]
    return render_template(
        "posts/post.html", title=post.title, post=post, form=form, comments=top_level,
        journal_owner=post.author,
    )


@posts.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = get_visible_post(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm(obj=post if request.method == "GET" else None)
    form.userpic_id.choices = _userpic_choices()
    if request.method == "GET":
        form.tags.data = ", ".join(t.name for t in post.tags)
        form.userpic_id.data = post.userpic_id or 0
    if form.validate_on_submit():
        _fill_post(post, form)
        post.updated_at = utcnow()
        db.session.commit()
        flash("Entry updated.", "success")
        return redirect(url_for("posts.post", post_id=post.id))
    return render_template("posts/edit.html", title="Edit entry", form=form, legend="Edit entry", post=post)


@posts.route("/post/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    post = get_visible_post(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash("Entry deleted.", "success")
    return redirect(url_for("journal.journal", username=current_user.username))


@posts.route("/post/<int:post_id>/comment", methods=["POST"])
@login_required
@limiter.limit("20/minute;200/day")
def add_comment(post_id):
    post = get_visible_post(post_id)
    if post.comments_disabled:
        abort(403)
    form = CommentForm()
    if not form.validate_on_submit():
        flash("Your comment was empty.", "warning")
        return redirect(url_for("posts.post", post_id=post.id) + "#comments")

    parent = None
    if form.parent_id.data:
        parent = db.session.get(Comment, int(form.parent_id.data)) if form.parent_id.data.isdigit() else None
        if parent is None or parent.post_id != post.id or parent.is_deleted:
            abort(400)
        # Keep threads readable: replies past the max depth attach to the deepest allowed level.
        while parent.depth >= Comment.MAX_DEPTH - 1:
            parent = parent.parent

    comment = Comment(post=post, author=current_user, parent=parent, body=form.body.data.strip())
    db.session.add(comment)
    db.session.commit()
    flash("Comment posted.", "success")
    return redirect(url_for("posts.post", post_id=post.id) + f"#t{comment.id}")


@posts.route("/comment/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    comment = db.session.get(Comment, comment_id)
    if comment is None:
        abort(404)
    # The commenter or the journal owner may delete a comment (like on LJ).
    if current_user.id not in (comment.user_id, comment.post.user_id):
        abort(403)
    post_id = comment.post_id
    if comment.replies:
        comment.is_deleted = True  # keep the thread, hide the text
        comment.body = ""
    else:
        db.session.delete(comment)
    db.session.commit()
    flash("Comment deleted.", "success")
    return redirect(url_for("posts.post", post_id=post_id) + "#comments")


@posts.route("/post/<int:post_id>/update")
def old_update(post_id):
    return redirect(url_for("posts.edit_post", post_id=post_id), 301)
