from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from pyvejournal.models import User


# REGISTRATION

class RegistrationForm(FlaskForm):
    username = StringField("Username",
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField("Email",validators=[DataRequired(), Email()])
    password = PasswordField("Password",validators=[DataRequired()])
    confirm_password = PasswordField("Confirm Password",
                                     validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Sign Up")
    def validate_username(self, username):
        userdupe = User.query.filter_by(username=username.data).first()
        if userdupe:
            raise ValidationError("That username is taken. Please choose a different one.")
        
    def validate_email(self, email):
        emaildupe = User.query.filter_by(email=email.data).first()
        if emaildupe:
            raise ValidationError("That E-Mail address is taken. Please choose a different one or sign in if you already have an account.")    

# LOGIN

class LoginForm(FlaskForm):
    email = StringField("Email",validators=[DataRequired(), Email()])
    password = PasswordField("Password",validators=[DataRequired()])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Log In")

# UPDATE

class UpdateAccountForm(FlaskForm):
    username = StringField("Username",
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField("Email",validators=[DataRequired(), Email()])
    picture = FileField("Update Profile Picture", validators =[FileAllowed(["jpg", "png"])])
    submit = SubmitField("Update")

    def validate_username(self, username):
        if username.data != current_user.username:
            user_dupe = User.query.filter_by(username=username.data).first()
            if user_dupe:
                raise ValidationError("That username is taken. Please choose a different one.")
        
    def validate_email(self, email):
        if email.data != current_user.email:
            email_dupe = User.query.filter_by(email=email.data).first()
            if email_dupe:
                raise ValidationError("That E-mail address is taken. Please choose a different one or sign in if you already have an account.")  
# do an else for the instance where the username or email matches the one they already have and alert with a flash message without clearing the fields.

class RequestResetForm(FlaskForm):
    email = StringField("Email",validators=[DataRequired(), Email()])
    submit = SubmitField("Request Password Reset")

    def validate_email(self, email):
        normalized_email = email.data.strip().lower()
        user = User.query.filter_by(email=normalized_email).first()
        print("Checking email:", normalized_email)
        print("User found:", user)
        if user is None:
            raise ValidationError("There is no account with that E-Mail. You must register first")
   

class ResetPasswordForm(FlaskForm):
    password = PasswordField("Password",validators=[DataRequired()])
    confirm_password = PasswordField("Confirm Password",
                                     validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Reset Password")