from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from pyvejournal.config import Config
from flask_login import current_user
from flask_migrate import Migrate, upgrade
import os




# forms is referring to forms.py and models is referring to models.py


db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = "users.login"
login_manager.login_message_category = "info"
mail = Mail()


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

    try:
        with app.app_context():
            upgrade()
    except Exception as e:
        print(f"Migration skipped or failed: {e}")

    @app.context_processor
    def inject_theme():
        if current_user.is_authenticated and current_user.theme:
            return dict(theme=current_user.theme)
        theme_cookie = request.cookies.get('theme')
        return dict(theme=theme_cookie or 'theme-default')

    def run_seed_if_enabled(app):
        if os.environ.get("PYVEJOURNAL_RUN_SEED") == "true":
            from seed_render import seed_data
            seed_data(app)

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
