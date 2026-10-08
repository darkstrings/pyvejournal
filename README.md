# PyveJournal ✎

A LiveJournal-style blogging site built with Python and Flask: personal journals with a **current mood** and **current music** on every entry, friends-only posts, threaded comments, userpics, tags, `<lj-cut>`, and a style picker that lets every journal wear its own look.

It's a homage to mid-2000s journaling, rebuilt with a modern, secure stack.

## Features

- **Journals.** Each user gets `/journal/<username>`, with Recent entries, a Friends page and a User info page, in the classic LJ layout.
- **Entries.** Each entry has a subject, mood (with emoji), music, tags and a userpic. Basic HTML works, and `<lj-cut text="Read more…">` folds long posts on list pages.
- **Security levels.**
  - **Public:** anyone can read it.
  - **Friends only:** readable by people *you* added.
  - **Private:** only you can read it.
- **Friends.** Friending is one-way, like LJ: adding someone puts their entries on your Friends page.
- **Comments.** Threaded replies up to 5 levels deep. Commenters and journal owners can delete comments. A deleted comment that has replies stays as a placeholder, so the thread keeps its shape.
- **Userpics.** Upload up to 6. Each is cropped to 100×100 and saved as WebP in the database, so nothing is lost when Render restarts. Pick one per entry.
- **Four styles.** Classic (LJ blue), Light, Signal Forge and Neon Drift. Visitors see your journal in *your* chosen style, and guests' picks are stored in a cookie.
- **Demo account.** "Try the demo" logs visitors in to a shared account. Its posts and comments are cleaned up after 2 hours, and its username, email and password are locked.
- **Responsive.** No Bootstrap, just plain modern CSS with theme tokens. It works without JavaScript; the JS only adds niceties.

## Security

- CSRF protection on every form, and logout uses POST.
- bcrypt password hashing.
- Rate limiting on login, register, password reset and comments.
- Entry HTML is sanitized with `nh3`, an allow-list sanitizer, and comments are escaped.
- Strict Content-Security-Policy: no inline scripts or styles.
- Password reset links:
  - expire after 30 minutes;
  - stop working once the password is changed;
  - never reveal whether an email has an account.
- Uploaded images are verified and re-encoded, and oversized images are rejected.
- Secure session cookies in production.

## Run it locally

```bash
python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements-dev.txt
copy .env.example .env           # macOS/Linux: cp .env.example .env  (then set SECRET_KEY)

flask --app wsgi db upgrade      # create/upgrade the database
flask --app wsgi seed --yes      # optional: sample journals (wipes the database!)
python run.py                    # http://127.0.0.1:5000
```

Sample accounts are `johndoe@example.com`, `janedoe@example.com`, `alexsmith@example.com` and `rae@example.com`. All of them use the password `password123`.

| Command | What it does |
| --- | --- |
| `flask --app wsgi seed --yes` | Rebuilds the DB with sample journals, comments and the demo user |
| `flask --app wsgi demo-user` | Creates or refreshes just the demo account (safe on a live DB) |
| `pytest` | Runs the test suite |

## Deploy on Render

`render.yaml` is ready. Set these environment variables:

- `SECRET_KEY`: a long random string, e.g. from `python -c "import secrets; print(secrets.token_hex(32))"`.
- `DATABASE_URL`: a Postgres URL. Render Postgres works, and `postgres://` URLs are handled.
- Optional, for password-reset emails: `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_SERVER` (default: Gmail SMTP).
- Optional: `DEMO_ENABLED=0` to turn off the demo account.

On every deploy the start command runs `flask db upgrade` before starting gunicorn. Run `flask --app wsgi demo-user` once from the Render shell to create the demo account.

## Stack

- Flask 3.1 with blueprints and an app factory.
- SQLAlchemy 2 (typed models) and Flask-Migrate.
- Flask-Login, Flask-WTF and Flask-Limiter.
- nh3 and Pillow.
- Postgres in production, SQLite locally.
- gunicorn.

Built by [Lucien Gaydos](https://github.com/darkstrings).
