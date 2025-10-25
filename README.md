# PyveJournal 📝🎨

PyveJournal is a Flask-powered publishing platform with dynamic theming, modular CSS architecture, and expressive UX. Built with Bootstrap 5 and Jinja2, it features user authentication, post creation, and a live theme switcher with cookie-based previews for guests and also saved to the db for created accounts. Every detail is crafted to feel intentional.

---

## 🚀 Features

- 🎨 Dynamic theme switcher with dropdown UX (With more themes on the way)
- 🧠 Modular layout and scalable CSS theme architecture
- 🔐 User authentication and session management
- 📝 Post creation and sitewide post stats
- 📬 Email support via secure app password
- 🧾 Sidebar and dropdowns fully themed for dark/light modes
- 🧼 Repo hygiene with `.gitignore` and environment variable security

---

## 🧰 Tech Stack

| Layer       | Tools & Libraries                          |
|-------------|---------------------------------------------|
| **Backend** | Flask, Flask-Login, Flask-SQLAlchemy, Flask-Migrate, Flask-WTF |
| **Frontend**| Bootstrap 5, Jinja2, Custom CSS, JavaScript |
| **Database**| SQLite (development), PostgreSQL (production-ready) |
| **Security**| App password via environment variables (`.env`) |
| **Deployment**| [Your platform here — e.g., Render, Heroku] |

---

## 📦 Installation

```bash
git clone https://github.com/yourusername/pyvejournal.git
cd pyvejournal
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

Pull requests welcome! For major changes, open an issue first to discuss what you’d like to change.
