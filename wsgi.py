from pyvejournal import create_app
from flask_migrate import upgrade
import os

app = create_app()

if os.environ.get("FLASK_RUN_MIGRATE") == "1":
    try:
        with app.app_context():
            upgrade()
    except Exception as e:
        print(f"Migration skipped or failed: {e}")
