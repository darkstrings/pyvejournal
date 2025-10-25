import secrets
import os
from PIL import Image
from flask import  url_for
from pyvejournal import mail
from flask_mail import Message
from flask import current_app 
# current app is used to get the app context when using application factories and blueprints. See the __init__.py file for more info.


# PROFILE PIC UPDATE
def save_picture(form_picture):
    # We're changing the name of the file incase there's already a file with that name using secrets

    # Here's the new first part:
    random_hex = secrets.token_hex(8)

    # grab the file name they're uploading. Saving the extension as a new var and make=ing a throw away _ var for the first part since we're not using it...
    _, f_ext = os.path.splitext(form_picture.filename)

    # now crush the new name and ext to make a new file name
    picture_fn = random_hex + f_ext

    # Now make the full path of where it's going to be saved using the OS module.
    picture_path = os.path.join(current_app.root_path, "static/profile_pics" , picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    
    # upload the file (remember, that doesn't make it the profile picture yet, it has to be set in the DB now that it's uploadted)
    i.save(picture_path)
    # send pack the filename so that we can then use that string to set it in the DB back in the route where we're calling it
    return picture_fn



def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message("Password Reset Request", 
                  sender = "Flask Blog Admin",
                  recipients=[user.email])
    msg.body = f"""To reset your password, visit the following link:
{url_for('users.reset_token', token=token, _external=True)}
If you did not make this request then simply ignore this email and no changes will be made.
"""
    mail.send(msg)
# jinja has template for emails too, but this is fine for now