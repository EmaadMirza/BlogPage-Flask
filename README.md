# BlogPage-Flask

A full-featured personal dev blog built with **Flask**, **SQLAlchemy**, and **Bootstrap 5**. Supports user registration and authentication, rich-text post creation via CKEditor, threaded comments, Gravatar avatars, paginated post listings, a contact form powered by Resend, and deployment-ready configuration for Render with PostgreSQL.

---

## Features

- **User Authentication** — Register, log in, and log out with Flask-Login. Passwords are hashed using Werkzeug's `pbkdf2:sha256`.
- **Role-based Access** — The first registered user (ID = 1) is automatically the admin. Only the admin can create, edit, and delete posts.
- **Full CRUD on Posts** — Create and edit posts using a CKEditor rich-text editor. Posts are paginated (5 per page) on the home feed.
- **Comments** — Authenticated users can comment on posts. Authors and the admin can delete their own comments. Comments are sanitized with `bleach` before storage.
- **Gravatar Avatars** — User avatars are auto-generated from email hashes via Gravatar with an identicon fallback.
- **Contact Form** — Sends emails via the [Resend](https://resend.com) API.
- **Dual Database Support** — Uses SQLite locally and PostgreSQL (via psycopg3) in production. Handles legacy `postgres://` URL prefixes and adds SSL automatically.
- **Error Pages** — Custom 404 and 500 handlers with graceful DB session rollback on server errors.
- **Production Ready** — Includes a `Procfile` for Gunicorn deployment on Render.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask 3.1 |
| ORM | SQLAlchemy 2.0, Flask-SQLAlchemy |
| Auth | Flask-Login, Werkzeug |
| Forms | Flask-WTF, WTForms |
| Rich Text | Flask-CKEditor |
| Frontend | Bootstrap 5 (Bootstrap-Flask) |
| Database | SQLite (dev), PostgreSQL via psycopg3 (prod) |
| Email | Resend API |
| Sanitization | bleach |
| Deployment | Gunicorn, Render |

---

## Project Structure

```
BlogPage-Flask/
├── main.py              # App factory, routes, models
├── forms.py             # WTForms form definitions
├── requirements.txt     # Python dependencies
├── Procfile             # Gunicorn entry point for Render
├── .env.example         # Environment variable template
├── .gitignore
├── static/              # CSS, JS, images
└── templates/           # Jinja2 HTML templates
    ├── index.html
    ├── post.html
    ├── make-post.html
    ├── register.html
    ├── login.html
    ├── about.html
    ├── contact.html
    ├── 404.html
    └── 500.html
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
git clone https://github.com/EmaadMirza/BlogPage-Flask.git
cd BlogPage-Flask
pip install -r requirements.txt
```

### Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `FLASK_KEY` | Secret key for Flask sessions. A random key is generated as fallback if missing. |
| `SQLALCHEMY_DATABASE_URI` | Full PostgreSQL connection string (production). Leave unset to use SQLite locally. |
| `RESEND_API_KEY` | API key from [resend.com](https://resend.com) for the contact form. |
| `EMAIL_ADDRESS` | Destination email address for contact form submissions. |

### Running Locally

```bash
python main.py
```

The app will start on `http://localhost:5002`. A local `posts.db` SQLite file is created automatically on first run.

---

## Deployment (Render)

1. Push the repo to GitHub.
2. Create a new **Web Service** on [Render](https://render.com) and connect the repo.
3. Set the **Start Command** to:
   ```
   gunicorn main:app
   ```
4. Add a **PostgreSQL** database on Render and copy the connection string into the `SQLALCHEMY_DATABASE_URI` environment variable.
5. Set the remaining environment variables (`FLASK_KEY`, `RESEND_API_KEY`, `EMAIL_ADDRESS`) in the Render dashboard.

The app handles the `postgres://` → `postgresql+psycopg://` URL rewrite and SSL configuration automatically.

---

## Admin Access

The **first user to register** becomes the admin (user ID = 1). The admin account has exclusive access to:

- Creating new blog posts (`/new-post`)
- Editing existing posts (`/edit-post/<id>`)
- Deleting posts (`/delete/<id>`)

All other registered users can read posts and leave comments.

---

## License

This project is open source.
