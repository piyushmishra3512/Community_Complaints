# Community Maintenance — Minimal Flask App 🏘️

This project is a small Flask app for reporting community or campus maintenance issues. It was forked/converted from a simple "hostel complaints" app and rebranded to "Community Maintenance" with a few UX improvements.

What’s new / key features ✨
- Rebranded UI and improved styling — modern hero, cards, and micro-interactions (hover lift on buttons).
- Added fields for reporter contact and location: `address` and `phone` (stored in the database).
- Success UX: subtle toasts for flash messages and confetti on successful submission/status change 🎉.
- Admin CSV/JSON exports now include `address` and `phone`.
- Simple file upload support for images attached to reports.

Quick start 🚀

1. (Optional) Create a virtualenv and activate it:

```bash
python -m venv .venv
source .venv/Scripts/activate    # on Windows (Git Bash) or use .venv\Scripts\activate
```
2. Install dependencies:

```bash
pip install -r requirements.txt
```
3. Initialize the database (creates `instance/complaints.db`):

```bash
python init_db.py
```
4. Run the app locally:

```bash
python app.py
```
Then open link in your browser.

Configuration & secrets 🔐
- The app reads environment variables and a local `.env` file (loaded via `python-dotenv`).
- Supported env vars:
	- `SECRET_KEY` — Flask secret key (default: `dev_secret`).
	- `ADMIN_PASSWORD` — admin login password (default: `admin`). Please change this before deploying.

Example `.env` file:

```text
ADMIN_PASSWORD=YourStrongAdminPassword
SECRET_KEY=some-production-secret
```

Management helper
- You can set the admin password using the helper in `manage.py` (if present):

```bash
python manage.py set-admin-password MyNewPass
```

Database notes 🗄️
- New fields `address` and `phone` were added to the `complaints` table. If you already have an existing `instance/complaints.db`, the app will add the columns automatically (SQLite `ALTER TABLE ADD COLUMN`).

Admin UI & exports 📋
- Admin interface: http://127.0.0.1:5000/admin/login (default password: `admin` unless you set `ADMIN_PASSWORD`).
- Export endpoints (available from admin UI):
	- CSV export: `/admin/export` — CSV now contains `address` and `phone` columns.
	- JSON export: `/admin/export.json` — JSON objects include `address` and `phone`.

UX & front-end notes 🎨
- Toasts: flash messages are converted into Bootstrap toasts and shown at the top-right.
- Confetti: `canvas-confetti` is loaded from CDN to celebrate successful submissions / status updates.
- File storage: uploaded images are saved to the `uploads/` folder.

Security & deployment notes ⚠️
- Do not use the default `admin` password in production. Set `ADMIN_PASSWORD` to a strong secret.
- Keep `SECRET_KEY` secret and do not commit `.env` to source control.

Want more?
- I can:
	- Vendor `canvas-confetti` into `static/` (remove CDN dependency).
	- Add role-based authentication for admin users.
	- Add tests or CI steps for deployment.

Enjoy — and tell me if you want the README expanded with screenshots or a quick deploy guide for e.g. Heroku / Docker 🐳
