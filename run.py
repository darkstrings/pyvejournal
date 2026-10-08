"""Local development server: `python run.py` (or `flask --app wsgi run --debug`)."""
from dotenv import load_dotenv

load_dotenv()

from pyvejournal import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
