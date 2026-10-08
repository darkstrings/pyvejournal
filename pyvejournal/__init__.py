from datetime import timedelta

from flask import Flask, request
from flask_login import current_user
from sqlalchemy import delete, select

from .config import pick_config
from .extensions import bcrypt, csrf, db, limiter, login_manager, mail, migrate


def create_app(config_class=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class or pick_config())
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY is not set. Add it to your environment (see .env.example).")

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    from .models import Guest, User

    login_manager.anonymous_user = Guest

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    register_template_helpers(app)
    register_security_headers(app)
    register_demo_cleanup(app)

    from .errors.handlers import errors
    from .journal.routes import bp as journal
    from .main.routes import main
    from .posts.routes import posts
    from .users.routes import users

    for bp in (main, users, posts, journal, errors):
        app.register_blueprint(bp)

    from .cli import register_cli

    register_cli(app)
    return app


def register_template_helpers(app):
    from .content import MOODS, mood_emoji, plain_excerpt, render_comment, render_entry
    from .models import DEFAULT_THEME, SECURITY_LEVELS, THEMES, normalize_theme

    app.jinja_env.filters.update(
        entry=render_entry,
        comment_html=render_comment,
        excerpt=plain_excerpt,
        mood_emoji=mood_emoji,
    )
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    @app.template_filter("ljdate")
    def ljdate(dt):
        day = dt.day
        suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return dt.strftime(f"%A, %B {day}{suffix}, %Y")

    @app.template_filter("ljtime")
    def ljtime(dt):
        return dt.strftime("%I:%M %p").lstrip("0").lower()

    @app.context_processor
    def inject_globals():
        if current_user.is_authenticated:
            viewer_theme = current_user.style
        else:
            viewer_theme = normalize_theme(request.cookies.get("theme", DEFAULT_THEME))
        return {
            "viewer_theme": viewer_theme,
            "THEMES": THEMES,
            "SECURITY_LEVELS": SECURITY_LEVELS,
            "MOODS": MOODS,
            "demo_enabled": app.config.get("DEMO_ENABLED"),
        }


def register_security_headers(app):
    @app.after_request
    def headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' https: data:; style-src 'self' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; script-src 'self'; frame-ancestors 'self'; "
            "base-uri 'self'; form-action 'self'",
        )
        return resp


def register_demo_cleanup(app):
    """Entries and comments written by the shared demo account vanish after a couple of hours."""
    state = {"next": None}

    @app.before_request
    def cleanup():
        from .models import Comment, Post, User, utcnow

        if not app.config.get("DEMO_ENABLED") or request.endpoint == "static":
            return
        now = utcnow()
        if state["next"] and now < state["next"]:
            return
        state["next"] = now + timedelta(minutes=10)
        cutoff = now - timedelta(hours=2)
        demo_ids = select(User.id).where(User.is_demo.is_(True))
        db.session.execute(
            delete(Comment).where(Comment.user_id.in_(demo_ids), Comment.created_at < cutoff)
        )
        old_posts = db.session.scalars(
            select(Post).where(Post.user_id.in_(demo_ids), Post.date_posted < cutoff)
        ).all()
        for post in old_posts:
            db.session.delete(post)
        db.session.commit()
