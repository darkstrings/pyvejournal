"""Command-line helpers:

    flask --app wsgi seed          wipe the database and load sample journals (local/dev use)
    flask --app wsgi demo-user     create/refresh only the shared demo account (safe in production)
"""

import secrets
from datetime import timedelta
from io import BytesIO

import click
from PIL import Image, ImageDraw, ImageFont

from .extensions import db
from .models import Comment, Post, User, Userpic, get_or_create_tags, utcnow

PALETTE = ["#3b5998", "#b5523b", "#2e7d5b", "#7b4fa1", "#c48a1f", "#22707f", "#a63d6d"]

SAMPLE_USERS = [
    dict(username="johndoe", display_name="John", email="johndoe@example.com", theme="theme-signalforge",
         location="Erie, PA", interests="guitars, flask, synthwave, coffee", bio="Writing code and riffs."),
    dict(username="janedoe", display_name="Jane", email="janedoe@example.com", theme="theme-neondrift",
         location="Pittsburgh, PA", interests="neon, css, night drives, cats", bio="Neon lights and late-night CSS."),
    dict(username="alexsmith", display_name="Alex", email="alexsmith@example.com", theme="theme-light",
         location="Cleveland, OH", interests="python, databases, hiking", bio="Databases by day, trails by weekend."),
    dict(username="mixtape_maven", display_name="Rae", email="rae@example.com", theme="theme-classic",
         location="Somewhere in 2004", interests="mixtapes, livejournal, away messages, emo",
         bio="Still mourning my AIM buddy list. Comments are love <3"),
]

SAMPLE_ENTRIES = [
    ("mixtape_maven", "first post!!1", "nostalgic", "Dashboard Confessional – Hands Down", "public", ["intro", "nostalgia"],
     "ok so I finally made one of these. hi internet!\n\nI'm going to post about music, my day, and probably way too many quiz results. "
     "<b>Friend me</b> if you want to read my friends-only stuff.\n\n<lj-cut text=\"my top 5 albums right now\">"
     "<ol><li>The Moon & Antarctica</li><li>Transatlanticism</li><li>Hands Down EP</li><li>Fever to Tell</li><li>Turn On the Bright Lights</li></ol>"
     "That's it. That's the post."),
    ("johndoe", "Flask blueprints finally clicked", "accomplished", "Daft Punk – Harder, Better, Faster, Stronger", "public", ["python", "flask"],
     "Spent the evening splitting the app into blueprints: <code>main</code>, <code>users</code>, <code>posts</code>.\n\n"
     "Everything feels less tangled now. Next up: comments and a friends page."),
    ("janedoe", "Night drive palette", "creative", "Kavinsky – Nightcall", "public", ["design", "css"],
     "Made a new theme tonight: deep navy, hot pink headlines, electric teal links. I'm calling it <i>Neon Drift</i>.\n\n"
     "Try it from the style menu up top and tell me what you think!"),
    ("alexsmith", "Model relationships, explained with pizza", "hungry", "", "public", ["python", "databases"],
     "A <b>User</b> has many <b>Posts</b> the same way a pizza has many slices.\n"
     "A many-to-many is toppings: lots of pizzas, lots of toppings, and a little table in the middle remembering who has what."),
    ("johndoe", "Gear update (friends only)", "excited", "Van Halen – Eruption", "friends", ["guitars"],
     "Picked up a used Les Paul today. Don't tell my wallet. Friends-only because I'm still in denial about the price."),
    ("mixtape_maven", "quiz: which 2000s browser are you?", "amused", "", "public", ["quizzes", "nostalgia"],
     "I got <b>Firefox 1.0</b>: \"You're open-minded, extensible and you hate pop-ups.\"\n\nhonestly accurate."),
    ("janedoe", "Rainy Sunday", "mellow", "Radiohead – Weird Fishes", "public", ["life"],
     "Tea, a blanket and a stack of library books. No screens until dinner. (This entry doesn't count.)"),
    ("alexsmith", "Note to self", "thoughtful", "", "private", ["notes"],
     "Private entry: remember to back up the database before running migrations."),
]

SAMPLE_COMMENTS = [
    (0, "janedoe", "welcome to the internet!! adding you :)", [("mixtape_maven", "yay thank you!! added back <3")]),
    (0, "johndoe", "Transatlanticism is a perfect album. No notes.", []),
    (1, "alexsmith", "Blueprints were the moment Flask clicked for me too.", [("johndoe", "Right? Feels like a real app now.")]),
    (2, "mixtape_maven", "this theme is giving myspace 2005 in the best way", []),
]


def make_userpic(letter: str, color: str) -> bytes:
    img = Image.new("RGB", (100, 100), color)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 56)
    except OSError:
        font = ImageFont.load_default(size=56)
    draw.text((50, 52), letter.upper(), fill="white", font=font, anchor="mm")
    out = BytesIO()
    img.save(out, "WEBP", quality=90)
    return out.getvalue()


def ensure_demo_user():
    demo = db.session.scalar(db.select(User).where(User.is_demo.is_(True)))
    if not demo:
        demo = User(username="demo_user", display_name="Demo visitor", email="demo@example.com",
                    theme="theme-classic", is_demo=True,
                    bio="The shared demo journal. Anything posted here is cleaned up after a couple of hours.")
        demo.set_password(secrets.token_hex(16))
        demo.userpics.append(Userpic(keyword="demo", data=make_userpic("D", "#555f73"), is_default=True))
        db.session.add(demo)
    # The demo account follows the sample journals so its friends page has something on it.
    for u in db.session.scalars(db.select(User).where(User.is_demo.is_(False), User.username.in_(
            [s["username"] for s in SAMPLE_USERS]))):
        if u not in demo.friends:
            demo.friends.append(u)
    db.session.commit()
    return demo


def register_cli(app):
    @app.cli.command("seed")
    @click.option("--yes", is_flag=True, help="Don't ask for confirmation.")
    def seed(yes):
        """Wipe ALL data and load sample journals."""
        if not yes:
            click.confirm("This deletes every user, entry and comment. Continue?", abort=True)
        db.drop_all()
        db.create_all()
        now = utcnow()
        users = {}
        for i, data in enumerate(SAMPLE_USERS):
            user = User(**data)
            user.set_password("password123")
            user.userpics.append(Userpic(keyword="default", data=make_userpic(data["username"][0], PALETTE[i]), is_default=True))
            db.session.add(user)
            users[user.username] = user

        # friendships (who reads whom)
        for a, bs in {"johndoe": ["janedoe", "alexsmith"], "janedoe": ["johndoe", "mixtape_maven"],
                      "alexsmith": ["johndoe"], "mixtape_maven": ["janedoe", "johndoe"]}.items():
            users[a].friends.extend(users[b] for b in bs)

        posts = []
        for i, (author, title, mood, music, security, tags, content) in enumerate(SAMPLE_ENTRIES):
            post = Post(author=users[author], title=title, content=content, mood=mood, music=music or None,
                        security=security, date_posted=now - timedelta(days=len(SAMPLE_ENTRIES) - i, hours=i * 3))
            post.tags = get_or_create_tags(tags)
            db.session.add(post)
            posts.append(post)
        db.session.flush()

        for idx, who, body, replies in SAMPLE_COMMENTS:
            c = Comment(post=posts[idx], author=users[who], body=body, created_at=posts[idx].date_posted + timedelta(hours=1))
            db.session.add(c)
            for j, (rwho, rbody) in enumerate(replies):
                db.session.add(Comment(post=posts[idx], author=users[rwho], body=rbody, parent=c,
                                       created_at=c.created_at + timedelta(minutes=20 * (j + 1))))
        db.session.commit()
        ensure_demo_user()
        click.echo("Seeded sample journals. Every sample account's password is: password123")

    @app.cli.command("demo-user")
    def demo_user():
        """Create or refresh the shared demo account (keeps all other data)."""
        demo = ensure_demo_user()
        click.echo(f"Demo account ready: {demo.username}")
