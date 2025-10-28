import json
from pyvejournal import db, create_app, bcrypt
from pyvejournal.models import User, Post
import os

def seed_data(app):
    with app.app_context():
        db.drop_all()
        db.create_all()

        with open("seed_data.json", "r") as f:
            data = json.load(f)

        user_map = {}
        for user_data in data["users"]:
            hashed_pw = bcrypt.generate_password_hash(user_data["password"]).decode("utf-8")
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                password=hashed_pw,
                theme=user_data.get("theme", "theme-light")
            )
            db.session.add(user)
            user_map[user.username] = user

        db.session.commit()

        for post_data in data["posts"]:
            author = user_map.get(post_data["author"])
            if author:
                post = Post(
                    title=post_data["title"],
                    content=post_data["content"],
                    author=author
                )
                db.session.add(post)

        db.session.commit()
        print("✅ Database seeded successfully. REMEMBER TO SET PYVEJOURNAL_RUN_SEED BACK TO FALSE IN .ENV")
        # set PYVEJOURNAL_RUN_SEED=false
        