from flask import Flask, request
from pyvejournal.config import Config
from flask_login import current_user
from flask_migrate import upgrade
from pyvejournal.extensions import db, login_manager, bcrypt, mail, migrate
import os


# moved the routes import to the bottom to avoid circular import issues since routes imports app from __init__.py and app imports routes from routes.py
# circular imports are when two modules depend on each other.
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from pyvejournal.models import User
        return User.query.get(int(user_id))


    try:
        with app.app_context():
            upgrade()
    except Exception as e:
        print(f"Migration skipped or failed: {e}")
    
    @app.context_processor
    def inject_theme():
        if current_user.is_authenticated:
            # Use the user's theme if set, otherwise default
            return dict(theme=current_user.theme or 'theme-default')
        # If not logged in, check cookie or default
        theme_cookie = request.cookies.get('theme')
        return dict(theme=theme_cookie or 'theme-default')


    def run_seed_if_enabled(app):
        if os.environ.get("PYVEJOURNAL_RUN_SEED") == "true":
            from seed_render import seed_data
            seed_data(app)

    @app.context_processor
    def inject_counts():
        from pyvejournal.models import Post
        post_count = Post.query.count()
        user_post_count = None
        if current_user.is_authenticated:
            user_post_count = Post.query.filter_by(author=current_user).count()
        return dict(post_count=post_count, user_post_count=user_post_count)


    run_seed_if_enabled(app)

    from pyvejournal.users.routes import users
    from pyvejournal.posts.routes import posts
    from pyvejournal.main.routes import main
    from pyvejournal.errors.handlers import errors
    app.register_blueprint(users)
    app.register_blueprint(posts)
    app.register_blueprint(main)
    app.register_blueprint(errors)

    return app
