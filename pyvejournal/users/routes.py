from urllib.parse import urlsplit

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func, select

from ..extensions import db, limiter
from ..models import DEFAULT_THEME, THEMES, User, Userpic, normalize_theme
from .forms import (
    LoginForm,
    PasswordForm,
    ProfileForm,
    RegistrationForm,
    RequestResetForm,
    ResetPasswordForm,
    UserpicForm,
)
from .utils import ImageError, process_userpic, send_reset_email

users = Blueprint("users", __name__)

DEMO_LOCKED = "The demo account can't change its settings — create your own journal to try this."


def safe_next(target: str | None) -> str | None:
    """Only follow ?next= to paths on this site (prevents open redirects)."""
    if not target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or not target.startswith("/") or target.startswith("//"):
        return None
    return target


@users.route("/register", methods=["GET", "POST"])
@limiter.limit("10/hour", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data.strip(),
            email=form.email.data.strip().lower(),
            theme=normalize_theme(request.cookies.get("theme", DEFAULT_THEME)),
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash(f"Welcome to PyveJournal, {user.username}! Your journal is ready — write your first entry.", "success")
        return redirect(url_for("posts.new_post"))
    return render_template("users/register.html", title="Create a journal", form=form)


@users.route("/login", methods=["GET", "POST"])
@limiter.limit("10/minute;50/hour", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(select(User).where(func.lower(User.email) == form.email.data.strip().lower()))
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash(f"Welcome back, {user.name}!", "success")
            return redirect(safe_next(request.args.get("next")) or url_for("journal.friends_page", username=user.username))
        flash("That email and password don't match.", "danger")
    return render_template("users/login.html", title="Log in", form=form)


@users.route("/demo", methods=["POST"])
@limiter.limit("30/hour")
def demo_login():
    if not current_app.config.get("DEMO_ENABLED"):
        abort(404)
    user = db.session.scalar(select(User).where(User.is_demo.is_(True)))
    if not user:
        flash("The demo account isn't set up on this server.", "warning")
        return redirect(url_for("users.login"))
    login_user(user)
    flash("You're in the demo journal. Anything you write disappears after a couple of hours.", "info")
    return redirect(url_for("journal.friends_page", username=user.username))


@users.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("You're logged out. See you soon!", "success")
    return redirect(url_for("main.home"))


@users.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    form = ProfileForm(obj=current_user)
    if request.method == "GET":
        form.theme.data = current_user.style
    pw_form = PasswordForm(prefix="pw")
    if form.submit.data and form.validate_on_submit():
        if current_user.is_demo and (
            form.username.data != current_user.username or form.email.data.lower() != current_user.email
        ):
            flash(DEMO_LOCKED, "warning")
            return redirect(url_for("users.settings"))
        form.populate_obj(current_user)
        current_user.email = current_user.email.strip().lower()
        db.session.commit()
        flash("Profile saved.", "success")
        return redirect(url_for("users.settings"))
    return render_template("users/settings.html", title="Settings", form=form, pw_form=pw_form)


@users.route("/settings/password", methods=["POST"])
@login_required
@limiter.limit("10/hour")
def change_password():
    if current_user.is_demo:
        flash(DEMO_LOCKED, "warning")
        return redirect(url_for("users.settings"))
    pw_form = PasswordForm(prefix="pw")
    if pw_form.validate_on_submit():
        if not current_user.check_password(pw_form.current_password.data):
            flash("Your current password is wrong.", "danger")
        else:
            current_user.set_password(pw_form.password.data)
            db.session.commit()
            flash("Password changed.", "success")
        return redirect(url_for("users.settings"))
    form = ProfileForm(obj=current_user)
    form.theme.data = current_user.style
    return render_template("users/settings.html", title="Settings", form=form, pw_form=pw_form), 400


# --- userpics -----------------------------------------------------------------

@users.route("/settings/userpics", methods=["GET", "POST"])
@login_required
def userpics():
    form = UserpicForm()
    if form.validate_on_submit():
        if current_user.is_demo:
            flash(DEMO_LOCKED, "warning")
        elif len(current_user.userpics) >= Userpic.MAX_PER_USER:
            flash(f"You can have up to {Userpic.MAX_PER_USER} userpics. Delete one first.", "warning")
        else:
            try:
                data = process_userpic(form.picture.data)
            except ImageError as e:
                flash(str(e), "danger")
            else:
                pic = Userpic(
                    keyword=form.keyword.data.strip(), data=data, mimetype="image/webp",
                    is_default=not current_user.userpics,
                )
                current_user.userpics.append(pic)
                db.session.commit()
                flash("Userpic uploaded.", "success")
                return redirect(url_for("users.userpics"))
    return render_template("users/userpics.html", title="Userpics", form=form, max_pics=Userpic.MAX_PER_USER)


def _own_userpic(pic_id):
    pic = db.session.get(Userpic, pic_id)
    if not pic or pic.user_id != current_user.id:
        abort(404)
    return pic


@users.route("/settings/userpics/<int:pic_id>/default", methods=["POST"])
@login_required
def userpic_default(pic_id):
    pic = _own_userpic(pic_id)
    for p in current_user.userpics:
        p.is_default = p.id == pic.id
    db.session.commit()
    flash(f"“{pic.keyword}” is now your default userpic.", "success")
    return redirect(url_for("users.userpics"))


@users.route("/settings/userpics/<int:pic_id>/delete", methods=["POST"])
@login_required
def userpic_delete(pic_id):
    pic = _own_userpic(pic_id)
    if current_user.is_demo:
        flash(DEMO_LOCKED, "warning")
        return redirect(url_for("users.userpics"))
    was_default = pic.is_default
    db.session.delete(pic)
    db.session.flush()
    if was_default and current_user.userpics:
        current_user.userpics[0].is_default = True
    db.session.commit()
    flash("Userpic deleted.", "success")
    return redirect(url_for("users.userpics"))


# --- password reset -----------------------------------------------------------

@users.route("/reset-password", methods=["GET", "POST"])
@limiter.limit("5/hour", methods=["POST"])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = db.session.scalar(select(User).where(func.lower(User.email) == form.email.data.strip().lower()))
        if user and not user.is_demo:
            try:
                send_reset_email(user)
            except Exception:
                current_app.logger.exception("Could not send reset email")
        # Same message either way, so nobody can probe which emails have accounts.
        flash("If that email has an account, a reset link is on its way.", "info")
        return redirect(url_for("users.login"))
    return render_template("users/reset_request.html", title="Reset password", form=form)


@users.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    user = User.verify_reset_token(token)
    if user is None:
        flash("That reset link is invalid or has expired.", "warning")
        return redirect(url_for("users.reset_request"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Password updated — you can log in now.", "success")
        return redirect(url_for("users.login"))
    return render_template("users/reset_token.html", title="Reset password", form=form)


# --- theme switcher -------------------------------------------------------------

@users.route("/theme", methods=["POST"])
def set_theme():
    theme = request.form.get("theme", "")
    if theme not in THEMES:
        abort(400)
    if current_user.is_authenticated:
        current_user.theme = theme
        db.session.commit()
        message = f"Style switched to {THEMES[theme]}."
    else:
        message = f"Previewing {THEMES[theme]} — make a journal to keep it."
    wants_json = request.accept_mimetypes.best == "application/json"
    resp = make_response(jsonify(message=message, theme=theme) if wants_json else redirect(
        safe_next(request.form.get("next")) or url_for("main.home")
    ))
    if not wants_json:
        flash(message, "success")
    resp.set_cookie("theme", theme, max_age=60 * 60 * 24 * 365, samesite="Lax",
                    secure=current_app.config.get("SESSION_COOKIE_SECURE", False))
    return resp


# --- old URLs from the previous version ------------------------------------------

@users.route("/account")
def old_account():
    return redirect(url_for("users.settings"), 301)


@users.route("/user/<string:username>")
def old_user_posts(username):
    return redirect(url_for("journal.journal", username=username), 301)
