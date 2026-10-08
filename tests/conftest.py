import pytest
from sqlalchemy import select

from pyvejournal import create_app
from pyvejournal.config import TestConfig
from pyvejournal.extensions import db
from pyvejournal.models import Post, User


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        # Same data as `flask seed`: four sample journals plus the demo account.
        result = app.test_cli_runner().invoke(args=["seed", "--yes"])
        assert result.exit_code == 0, result.output
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def user(username) -> User:
    return db.session.scalar(select(User).where(User.username == username))


def post_titled(title) -> Post:
    return db.session.scalar(select(Post).where(Post.title == title))


def login(client, email, password="password123"):
    return client.post("/login", data={"email": email, "password": password})


@pytest.fixture
def as_john(client):
    login(client, "johndoe@example.com")
    return client
