from flask import Blueprint, render_template

errors = Blueprint("errors", __name__)

MESSAGES = {
    400: ("Bad request", "Something about that request didn't look right."),
    403: ("Not allowed", "You don't have permission to do that."),
    404: ("Page not found", "This entry or journal doesn't exist — or it's not visible to you."),
    413: ("File too large", "That upload is too big. Userpics need to be under 3 MB."),
    429: ("Slow down", "You're doing that a lot. Take a breath and try again in a minute."),
    500: ("Something broke", "That's on us. Please try again in a moment."),
}


def _render(code):
    title, message = MESSAGES[code]
    return render_template("errors/error.html", title=title, code=code, message=message), code


for _code in MESSAGES:
    errors.app_errorhandler(_code)(lambda e, c=_code: _render(c))
