from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from sqlalchemy import func, select
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import URL, DataRequired, Email, EqualTo, Length, Optional, Regexp, ValidationError

from ..extensions import db
from ..models import THEMES, User

USERNAME_RULES = [
    DataRequired(),
    Length(min=2, max=20),
    Regexp(r"^[A-Za-z0-9_]+$", message="Letters, numbers and underscores only."),
]


def _taken(column, value, exclude_id=None):
    q = select(User.id).where(func.lower(column) == value.strip().lower())
    if exclude_id:
        q = q.where(User.id != exclude_id)
    return db.session.scalar(q) is not None


class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=USERNAME_RULES)
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, message="At least 8 characters.")])
    confirm_password = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Create my journal")

    def validate_username(self, field):
        if _taken(User.username, field.data):
            raise ValidationError("That username is taken.")

    def validate_email(self, field):
        if _taken(User.email, field.data):
            raise ValidationError("That email already has an account. Try logging in.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember me")
    submit = SubmitField("Log in")


class ProfileForm(FlaskForm):
    username = StringField("Username", validators=USERNAME_RULES)
    display_name = StringField("Display name", validators=[Optional(), Length(max=50)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    location = StringField("Location", validators=[Optional(), Length(max=80)])
    website = StringField("Website", validators=[Optional(), URL(), Length(max=200)])
    interests = StringField("Interests", validators=[Optional(), Length(max=400)],
                            description="Comma-separated, e.g. guitars, python, 3d printing")
    bio = TextAreaField("Bio", validators=[Optional(), Length(max=2000)])
    theme = SelectField("Journal style", choices=list(THEMES.items()))
    submit = SubmitField("Save profile")

    def validate_username(self, field):
        if _taken(User.username, field.data, current_user.id):
            raise ValidationError("That username is taken.")

    def validate_email(self, field):
        if _taken(User.email, field.data, current_user.id):
            raise ValidationError("That email is used by another account.")


class PasswordForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired()])
    password = PasswordField("New password", validators=[DataRequired(), Length(min=8, message="At least 8 characters.")])
    confirm_password = PasswordField("Confirm new password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Change password")


class UserpicForm(FlaskForm):
    picture = FileField("Image", validators=[FileRequired(), FileAllowed(["jpg", "jpeg", "png", "gif", "webp"], "Images only.")])
    keyword = StringField("Keyword", validators=[DataRequired(), Length(max=40)], description="e.g. happy, guitar, sleepy")
    submit = SubmitField("Upload userpic")


class RequestResetForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Send reset link")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("New password", validators=[DataRequired(), Length(min=8, message="At least 8 characters.")])
    confirm_password = PasswordField("Confirm new password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Reset password")
