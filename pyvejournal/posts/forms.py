from flask_wtf import FlaskForm
from wtforms import BooleanField, HiddenField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from ..models import SECURITY_LEVELS


class PostForm(FlaskForm):
    title = StringField("Subject", validators=[DataRequired(), Length(max=100)])
    content = TextAreaField("Entry", validators=[DataRequired(), Length(max=50_000)])
    mood = StringField("Current mood", validators=[Optional(), Length(max=40)])
    music = StringField("Current music", validators=[Optional(), Length(max=120)])
    tags = StringField("Tags", validators=[Optional(), Length(max=300)], description="Comma-separated")
    security = SelectField("Who can read this?", choices=list(SECURITY_LEVELS.items()), default="public")
    userpic_id = SelectField("Userpic", coerce=int, choices=[], validate_choice=False)
    comments_disabled = BooleanField("Disable comments")
    submit = SubmitField("Post to journal")


class CommentForm(FlaskForm):
    body = TextAreaField("Comment", validators=[DataRequired(), Length(max=5000)])
    parent_id = HiddenField()
    submit = SubmitField("Post comment")
