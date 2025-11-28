from flask import jsonify, make_response, render_template, url_for, flash, redirect, request, Blueprint
from flask_login import login_user, current_user, logout_user, login_required
from pyvejournal import db, bcrypt
from pyvejournal.models import User, Post
from pyvejournal.users.forms import (RegistrationForm, LoginForm, UpdateAccountForm,
                                   RequestResetForm, ResetPasswordForm)
from pyvejournal.users.utils import save_picture, send_reset_email
users = Blueprint('users', __name__)

VALID_THEMES = ['theme-default', 'theme-signalforge', 'theme-neondrift']

# ACCOUNT INFO
# As of right now, there's no way to change either of these values individually....You have to change both.
# This is because we're using the same validators as when you make a new account. The validator we need here needs to yes, check to not use something taken by another user but keep the user or email if it's their own. If you're logged in with that, you can keep it.
@users.route("/account", methods = ["GET", "POST"])
@login_required
# login_required makes sure that you're logged in before even accessing the page. It's also initialized in __init__
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            # call the save_picture function above and save its return to a var
            picture_file = save_picture(form.picture.data)
            # take that return and use it to set the new image in the DB
            current_user.image_file = picture_file

        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash("Update Successful", "success")
        return redirect(url_for("users.account"))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.email.data = current_user.email

    # image_file = url_for("static", filename ="profile_pics/" + "current_user.image_file")
    image_file = url_for("static", filename  = f"profile_pics/{current_user.image_file}")
    return render_template("account.html", 
                           title = "Account", 
                           image_file = image_file, 
                           form = form
                           )


@users.route("/register", methods = ["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        theme_cookie = request.cookies.get("theme")
        user_theme = theme_cookie or "theme-light"
        user = User(
            username = form.username.data, 
            email = form.email.data, 
            password = hashed_password, 
            theme = user_theme
            )
        db.session.add(user)
        db.session.commit()
        flash(f"Thank you for registering, {user.username}! You can now log in.","success")
        return redirect(url_for("users.login"))
    return render_template("register.html", title = "Register", form = form)

@users.route("/login" , methods = ["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email = form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember = form.remember.data)
            next_page = request.args.get("next")
            flash("Logged in successfully","info")
            # there's a parameter when you try to go to a page when you're not logged into.
            # next_page will contain it so that when you do log in, it'll take you there instead of home if next_page is Truthy....it exists...etc.
            return redirect("account") if next_page else redirect(url_for("main.home"))
            # ternary: |do stuff| |conditional| |otherwise do this instead|
        else:
            flash("Login failed. Please check for typos etc.","danger")
    return render_template("login.html", title = "Log in", form = form)

@users.route("/logout")
def logout():
    logout_user()
    flash("Logout Successful.","success")
    return redirect(url_for("main.home"))


@users.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get("page", 1, type = int)
    user = User.query.filter_by(username = username).first_or_404()
    posts = Post.query\
        .filter_by(author = user)\
        .order_by(Post.date_posted.desc())\
        .paginate(page = page, per_page = 5)
    return render_template("user_posts.html", posts = posts, user = user)
# the \ lets you start a new line if the line has lots of chaining and gets long. 

# user enters their email to reset the password
@users.route("/reset_password", methods=["GET", "POST"])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_reset_email(user)
        # Optional: use this message to avoid email enumeration
        flash("If an account with that email exists, a reset link has been sent.", "info")
        return redirect(url_for("users.login"))
    return render_template("reset_request.html", title="Reset Password", form=form)


# This is where the user resets their password with the token active
@users.route("/reset_password/<token>", methods = ["GET", "POST"])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    user = User.verify_reset_token(token)
    if user is None:
        flash("That is an invalid or expired token", "warning")
        return redirect(url_for("users.reset_request"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash("Password updated!","success")
        return redirect(url_for("users.login"))
    return render_template("reset_token.html", title = "Reset Password", form = form)


@users.route('/set-theme/<theme_name>')
def set_theme(theme_name):
    if current_user.is_authenticated:
        if theme_name != current_user.theme:
            current_user.theme = theme_name
            db.session.commit()
            return jsonify({
                "message": "Theme updated and saved to your account!",
                "category": "success"
            })
        else:
            return make_response('', 204)  # No change
    else:
        cookie_theme = request.cookies.get('theme')
        if theme_name != cookie_theme:
            resp = jsonify({
                "message": "Theme preview applied!",
                "category": "info"
            })
            resp.set_cookie('theme', theme_name, max_age=60*60*24*7)
            return resp
        else:
            return make_response('', 204)  # No change





