from flask import Blueprint,render_template, request
from pyvejournal.models import Post
from flask_login import current_user

main = Blueprint('main', __name__)

@main.route("/")
@main.route("/home")
def home():
    post_count = Post.query.all().__len__()
    user_post_count = 0
    
    if current_user.is_authenticated:
        user_post_count = Post.query.filter_by(author=current_user).count()
    page = request.args.get("page", 1, type = int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page = page, per_page = 5)
    print(post_count)
    # The method order_by(Post.date_posted.desc()) is how we put the latest post on top. (desc means descending) then we just chain paginate() to it
    return render_template("home.html", posts = posts, post_count=post_count, user_post_count=user_post_count)

@main.route("/about")
def about():
    return render_template("about.html", title = "About")

