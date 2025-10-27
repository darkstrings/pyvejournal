import os

class Config:
    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("PYVEJOURNAL_EMAIL_USER")  # "eagleaxe"
    MAIL_PASSWORD = os.environ.get("PYVEJOURNAL_EMAIL_PASS")  # 
    SECRET_KEY = os.environ.get("PYVEJOURNAL_SECRET_KEY") 
    SQLALCHEMY_DATABASE_URI = 'sqlite:///C:\\Users\darks\PycharmProjects\pyvejournal-project\\pyvejournal\\site.db'

    # This is a local path that wont work deployed