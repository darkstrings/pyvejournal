import io

from PIL import Image
from sqlalchemy import func, select

from pyvejournal.content import render_entry
from pyvejournal.extensions import db
from pyvejournal.models import Comment, Post, Tag, Userpic

from .conftest import login, post_titled, user


# --- pages -----------------------------------------------------------------

def test_public_pages_render(client):
    for url in ["/", "/about", "/login", "/register", "/reset-password", "/tag/flask",
                "/journal/johndoe", "/journal/johndoe/profile", "/journal/johndoe/friends"]:
        assert client.get(url).status_code == 200, url


def test_unknown_journal_is_404(client):
    assert client.get("/journal/nobody-here").status_code == 404
    assert client.get("/definitely-not-a-page").status_code == 404


def test_security_headers(client):
    resp = client.get("/")
    assert "script-src 'self'" in resp.headers["Content-Security-Policy"]
    assert resp.headers["X-Content-Type-Options"] == "nosniff"


def test_old_urls_redirect(client):
    assert client.get("/user/johndoe").headers["Location"].endswith("/journal/johndoe")
    assert client.get("/post/2/update").status_code == 301


# --- accounts --------------------------------------------------------------

def test_register_logs_in_and_lands_on_new_entry(client):
    resp = client.post("/register", data={"username": "newbie", "email": "New@Example.com",
                                          "password": "longenough", "confirm_password": "longenough"})
    assert resp.headers["Location"].endswith("/post/new")
    assert user("newbie").email == "new@example.com"
    assert client.get("/post/new").status_code == 200


def test_register_rejects_duplicates_case_insensitively(client):
    resp = client.post("/register", data={"username": "JohnDoe", "email": "x@example.com",
                                          "password": "longenough", "confirm_password": "longenough"})
    assert resp.status_code == 200 and b"taken" in resp.data.lower()


def test_login_wrong_password(client):
    resp = login(client, "johndoe@example.com", "nope")
    assert resp.status_code == 200 and b"don&#39;t match" in resp.data


def test_login_ignores_offsite_next(client):
    resp = client.post("/login?next=https://evil.example/", data={"email": "johndoe@example.com",
                                                                  "password": "password123"})
    assert resp.headers["Location"].endswith("/journal/johndoe/friends")


def test_logout_requires_post(as_john):
    assert as_john.get("/logout").status_code == 405
    as_john.post("/logout")
    assert as_john.get("/post/new").status_code == 302


def test_password_reset_does_not_reveal_accounts(client):
    a = client.post("/reset-password", data={"email": "johndoe@example.com"}, follow_redirects=True)
    b = client.post("/reset-password", data={"email": "ghost@example.com"}, follow_redirects=True)
    assert a.status_code == b.status_code == 200
    assert b"If that email" in a.data and b"If that email" in b.data


def test_reset_token_works_once(app, client):
    john = user("johndoe")
    token = john.get_reset_token()
    resp = client.post(f"/reset-password/{token}", data={"password": "brandnewpass", "confirm_password": "brandnewpass"})
    assert resp.status_code == 302
    assert user("johndoe").check_password("brandnewpass")
    again = client.get(f"/reset-password/{token}")
    assert again.status_code == 302  # token is spent: the password hash it was tied to changed


# --- privacy ---------------------------------------------------------------

def test_friends_only_entry_hidden_from_strangers(client):
    gear = post_titled("Gear update (friends only)")
    assert client.get(f"/post/{gear.id}").status_code == 404
    assert b"Gear update" not in client.get("/journal/johndoe").data
    assert b"Gear update" not in client.get("/").data


def test_friends_only_entry_visible_to_people_the_author_added(client):
    gear = post_titled("Gear update (friends only)")
    login(client, "janedoe@example.com")  # johndoe added janedoe
    assert client.get(f"/post/{gear.id}").status_code == 200


def test_friendship_is_one_way(client):
    gear = post_titled("Gear update (friends only)")
    login(client, "rae@example.com")  # mixtape_maven added johndoe, but not the other way round
    assert client.get(f"/post/{gear.id}").status_code == 404


def test_private_entry_only_for_author(client):
    note = post_titled("Note to self")
    login(client, "johndoe@example.com")
    assert client.get(f"/post/{note.id}").status_code == 404
    client.post("/logout")
    login(client, "alexsmith@example.com")
    assert client.get(f"/post/{note.id}").status_code == 200


def test_hidden_entries_do_not_leak_through_tag_counts(client):
    page = client.get("/journal/alexsmith").data
    assert b"Note to self" not in page


def test_cannot_comment_on_hidden_entry(client):
    note = post_titled("Note to self")
    login(client, "johndoe@example.com")
    assert client.post(f"/post/{note.id}/comment", data={"body": "hi"}).status_code == 404


# --- entries ---------------------------------------------------------------

def test_create_entry_with_mood_music_tags(as_john):
    resp = as_john.post("/post/new", data={"title": "Hello", "content": "Some <b>bold</b> words",
                                           "mood": "nostalgic", "music": "Weezer — Say It Ain't So",
                                           "tags": "Music, 2004, music", "security": "public"})
    assert resp.status_code == 302
    post = post_titled("Hello")
    assert post.mood == "nostalgic"
    assert sorted(t.name for t in post.tags) == ["2004", "music"]
    page = as_john.get(f"/post/{post.id}").data
    assert b"Current mood" in page and b"Say It Ain" in page


def test_tags_are_not_duplicated(as_john):
    as_john.post("/post/new", data={"title": "A", "content": "x", "tags": "flask", "security": "public"})
    assert db.session.scalar(select(func.count()).select_from(Tag).where(Tag.name == "flask")) == 1


def test_only_author_can_edit_or_delete(client):
    post = post_titled("Night drive palette")  # janedoe's
    login(client, "johndoe@example.com")
    assert client.get(f"/post/{post.id}/edit").status_code == 403
    assert client.post(f"/post/{post.id}/delete").status_code == 403
    client.post("/logout")
    login(client, "janedoe@example.com")
    assert client.post(f"/post/{post.id}/delete").status_code == 302
    assert db.session.get(Post, post.id) is None


def test_edit_entry(client):
    post = post_titled("Night drive palette")
    login(client, "janedoe@example.com")
    client.post(f"/post/{post.id}/edit", data={"title": "Night drive v2", "content": "new", "security": "friends"})
    db.session.refresh(post)
    assert post.title == "Night drive v2" and post.security == "friends" and post.updated_at


def test_cannot_pick_someone_elses_userpic(client):
    janes = user("janedoe").userpics[0]
    login(client, "johndoe@example.com")
    client.post("/post/new", data={"title": "pic", "content": "x", "security": "public", "userpic_id": janes.id})
    assert post_titled("pic").userpic_id is None


# --- content rendering -----------------------------------------------------

def test_sanitizer_strips_scripts_and_handlers():
    html = str(render_entry('<script>alert(1)</script><img src=x onerror=alert(1)><a href="javascript:x">l</a>'))
    assert "<script" not in html and "onerror" not in html and "javascript:" not in html


def test_lj_cut_collapses_on_lists():
    text = 'Intro<lj-cut text="Read more…">secret part'
    short = str(render_entry(text, url="/post/1"))
    full = str(render_entry(text))
    assert "secret part" not in short and "Read more…" in short and 'href="/post/1#cutid1"' in short
    assert "secret part" in full


def test_plain_text_gets_paragraphs():
    html = str(render_entry("one\n\ntwo\nthree"))
    assert html.count("<p>") == 2 and "<br>" in html


# --- comments --------------------------------------------------------------

def test_threaded_replies_and_depth_cap(as_john):
    post = post_titled("Night drive palette")
    parent = None
    for i in range(8):
        data = {"body": f"level {i}"}
        if parent:
            data["parent_id"] = str(parent.id)
        as_john.post(f"/post/{post.id}/comment", data=data)
        parent = db.session.scalar(select(Comment).where(Comment.body == f"level {i}"))
    assert parent.depth <= Comment.MAX_DEPTH - 1


def test_comment_on_disabled_entry_forbidden(as_john):
    post = post_titled("Night drive palette")
    post.comments_disabled = True
    db.session.commit()
    assert as_john.post(f"/post/{post.id}/comment", data={"body": "hi"}).status_code == 403


def test_comment_html_is_escaped(as_john):
    post = post_titled("Night drive palette")
    as_john.post(f"/post/{post.id}/comment", data={"body": "<script>alert(1)</script>"})
    page = as_john.get(f"/post/{post.id}").data
    assert b"<script>alert(1)" not in page


def test_delete_comment_with_replies_soft_deletes(client):
    post = post_titled("Night drive palette")
    login(client, "johndoe@example.com")
    client.post(f"/post/{post.id}/comment", data={"body": "root"})
    root = db.session.scalar(select(Comment).where(Comment.body == "root"))
    client.post(f"/post/{post.id}/comment", data={"body": "reply", "parent_id": str(root.id)})
    client.post(f"/comment/{root.id}/delete")
    db.session.refresh(root)
    assert root.is_deleted and root.body == ""


def test_journal_owner_can_delete_any_comment_but_strangers_cannot(client):
    post = post_titled("Night drive palette")  # janedoe's
    login(client, "johndoe@example.com")
    client.post(f"/post/{post.id}/comment", data={"body": "by john"})
    c = db.session.scalar(select(Comment).where(Comment.body == "by john"))
    client.post("/logout")
    login(client, "alexsmith@example.com")
    assert client.post(f"/comment/{c.id}/delete").status_code == 403
    client.post("/logout")
    login(client, "janedoe@example.com")
    assert client.post(f"/comment/{c.id}/delete").status_code == 302
    assert db.session.get(Comment, c.id) is None


# --- friends ---------------------------------------------------------------

def test_add_and_remove_friend(client):
    login(client, "alexsmith@example.com")
    rae = user("mixtape_maven")
    client.post("/journal/mixtape_maven/friend")
    assert rae in user("alexsmith").friends
    client.post("/journal/mixtape_maven/friend")
    assert rae not in user("alexsmith").friends


def test_cannot_friend_yourself(as_john):
    as_john.post("/journal/johndoe/friend")
    assert user("johndoe") not in user("johndoe").friends


def test_friends_page_shows_friends_entries(as_john):
    page = as_john.get("/journal/johndoe/friends").data
    assert b"Night drive palette" in page  # janedoe is on john's list


# --- styles ----------------------------------------------------------------

def test_style_cookie_for_visitors(client):
    resp = client.post("/theme", data={"theme": "theme-neondrift"}, headers={"Accept": "application/json"})
    assert resp.json["theme"] == "theme-neondrift"
    assert b'data-theme="theme-neondrift"' in client.get("/").data


def test_unknown_style_rejected(client):
    assert client.post("/theme", data={"theme": "theme-evil"}).status_code == 400


def test_journal_uses_owners_style(client):
    # johndoe picked Signal Forge; visitors see his journal in it whatever their own style is.
    client.post("/theme", data={"theme": "theme-light"})
    assert b'data-theme="theme-signalforge"' in client.get("/journal/johndoe").data


def test_logged_in_style_saved_to_profile(as_john):
    as_john.post("/theme", data={"theme": "theme-classic"})
    assert user("johndoe").theme == "theme-classic"


# --- userpics --------------------------------------------------------------

def _png(size=(300, 200), color="red"):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    buf.seek(0)
    return buf


def test_upload_userpic_is_resized_to_webp(as_john):
    resp = as_john.post("/settings/userpics", data={"keyword": "red", "picture": (_png(), "red.png")},
                        content_type="multipart/form-data")
    assert resp.status_code == 302
    pic = db.session.scalar(select(Userpic).where(Userpic.keyword == "red"))
    img = Image.open(io.BytesIO(pic.data))
    assert img.format == "WEBP" and img.size == (100, 100)
    served = as_john.get(f"/userpic/{pic.id}")
    assert served.mimetype == "image/webp" and "immutable" in served.headers["Cache-Control"]


def test_userpic_rejects_non_images(as_john):
    as_john.post("/settings/userpics", data={"keyword": "bad", "picture": (io.BytesIO(b"not an image"), "x.png")},
                 content_type="multipart/form-data")
    assert db.session.scalar(select(Userpic).where(Userpic.keyword == "bad")) is None


def test_userpic_limit(as_john):
    for i in range(10):
        as_john.post("/settings/userpics", data={"keyword": f"p{i}", "picture": (_png(color="blue"), "b.png")},
                     content_type="multipart/form-data")
    assert len(user("johndoe").userpics) == Userpic.MAX_PER_USER


# --- demo account ----------------------------------------------------------

def test_demo_login_and_locked_settings(client):
    resp = client.post("/demo")
    assert resp.headers["Location"].endswith("/journal/demo_user/friends")
    demo = user("demo_user")
    client.post("/settings", data={"username": "hijacked", "email": demo.email, "submit": "1"})
    assert user("hijacked") is None
    client.post("/settings/password", data={"pw-current_password": "x", "pw-password": "newpassword",
                                            "pw-confirm_password": "newpassword", "pw-submit": "1"})
    assert not user("demo_user").check_password("newpassword")


def test_demo_can_update_bio(client):
    client.post("/demo")
    demo = user("demo_user")
    client.post("/settings", data={"username": demo.username, "email": demo.email, "bio": "hi from the demo",
                                   "theme": "theme-light", "submit": "1"})
    assert user("demo_user").bio == "hi from the demo"
