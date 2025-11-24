"""Restored clean Flask app (app_restored.py).

If you want this to be `app.py`, run the rename steps I provide.
"""

import os
import sqlite3
import uuid
from datetime import datetime
from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    send_from_directory, session, Response, jsonify
)
from werkzeug.utils import secure_filename
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf, CSRFError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
DB_PATH = os.path.join(BASE_DIR, 'instance', 'complaints.db')

load_dotenv(os.path.join(BASE_DIR, '.env'))

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['DATABASE'] = DB_PATH
    app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD', 'admin')

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.dirname(app.config['DATABASE']), exist_ok=True)

    csrf = CSRFProtect()
    csrf.init_app(app)
    app.jinja_env.globals['csrf_token'] = lambda: generate_csrf()

    def get_db_connection():
        conn = sqlite3.connect(app.config['DATABASE'])
        conn.row_factory = sqlite3.Row
        return conn

    def init_db():
        conn = get_db_connection()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                room TEXT,
                title TEXT,
                description TEXT,
                image TEXT,
                access_code TEXT,
                status TEXT DEFAULT 'open',
                created_at TEXT
            )
        ''')
        cur = conn.execute("PRAGMA table_info(complaints)")
        cols = [r[1] for r in cur.fetchall()]
        if 'access_code' not in cols:
            conn.execute('ALTER TABLE complaints ADD COLUMN access_code TEXT')
        conn.commit()
        conn.close()

    init_db()

    @app.route('/')
    def index():
        return redirect(url_for('submit'))

    @app.route('/submit', methods=['GET', 'POST'])
    def submit():
        if request.method == 'POST':
            name = request.form.get('name')
            room = request.form.get('room')
            title = request.form.get('title')
            description = request.form.get('description')

            image_filename = None
            file = request.files.get('image')
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
                filename = f"{timestamp}_{filename}"
                path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(path)
                image_filename = filename

            access_code = uuid.uuid4().hex[:10]
            conn = get_db_connection()
            cur = conn.execute(
                'INSERT INTO complaints (name, room, title, description, image, access_code, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (name, room, title, description, image_filename, access_code, datetime.utcnow().isoformat())
            )
            conn.commit()
            complaint_id = cur.lastrowid
            conn.close()
            return render_template('submit_success.html', complaint_id=complaint_id, access_code=access_code)
        return render_template('submit.html')

    @app.route('/track', methods=['GET', 'POST'])
    def track():
        complaint_id = request.values.get('id')
        access_code = request.values.get('code') or request.values.get('access_code')
        if not complaint_id or not access_code:
            return render_template('track.html')
        try:
            cid = int(complaint_id)
        except Exception:
            flash('Invalid complaint id', 'warning')
            return render_template('track.html')
        conn = get_db_connection()
        row = conn.execute('SELECT id, title, status, created_at FROM complaints WHERE id = ? AND access_code = ?', (cid, access_code)).fetchone()
        conn.close()
        if not row:
            flash('No matching complaint found. Check your ID and access code.', 'danger')
            return render_template('track.html')
        return render_template('track.html', c=row)

    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    def admin_required(func):
        from functools import wraps

        @wraps(func)
        def wrapper(*args, **kwargs):
            if not session.get('admin'):
                return redirect(url_for('admin_login'))
            return func(*args, **kwargs)

        return wrapper

    @app.route('/admin/login', methods=['GET', 'POST'])
    def admin_login():
        if request.method == 'POST':
            pwd = request.form.get('password')
            if pwd == app.config['ADMIN_PASSWORD']:
                session['admin'] = True
                return redirect(url_for('admin_list'))
            flash('Invalid password', 'danger')
        return render_template('admin_login.html')

    @app.route('/admin/logout')
    def admin_logout():
        session.pop('admin', None)
        flash('Logged out', 'info')
        return redirect(url_for('admin_login'))

    @app.route('/admin/list')
    @admin_required
    def admin_list():
        conn = get_db_connection()
        rows = conn.execute('SELECT * FROM complaints ORDER BY created_at DESC').fetchall()
        conn.close()
        return render_template('admin_list.html', complaints=rows)

    @app.route('/admin/complaint/<int:complaint_id>')
    @admin_required
    def view_complaint(complaint_id):
        conn = get_db_connection()
        row = conn.execute('SELECT * FROM complaints WHERE id = ?', (complaint_id,)).fetchone()
        conn.close()
        if not row:
            flash('Complaint not found', 'warning')
            return redirect(url_for('admin_list'))
        return render_template('view_complaint.html', c=row)

    @app.route('/admin/complaint/<int:complaint_id>/status', methods=['POST'])
    @admin_required
    def update_status(complaint_id):
        new_status = request.form.get('status')
        if new_status not in ('open', 'in-progress', 'closed'):
            flash('Invalid status', 'danger')
            return redirect(request.referrer or url_for('admin_list'))
        conn = get_db_connection()
        conn.execute('UPDATE complaints SET status = ? WHERE id = ?', (new_status, complaint_id))
        conn.commit()
        conn.close()
        flash('Status updated', 'success')
        return redirect(request.referrer or url_for('admin_list'))

    @app.route('/admin/complaint/<int:complaint_id>/delete', methods=['POST'])
    @admin_required
    def delete_complaint(complaint_id):
        conn = get_db_connection()
        row = conn.execute('SELECT image FROM complaints WHERE id = ?', (complaint_id,)).fetchone()
        if row and row['image']:
            try:
                img_path = os.path.join(app.config['UPLOAD_FOLDER'], row['image'])
                if os.path.exists(img_path):
                    os.remove(img_path)
            except Exception:
                pass
        conn.execute('DELETE FROM complaints WHERE id = ?', (complaint_id,))
        conn.commit()
        conn.close()
        flash('Complaint deleted', 'success')
        return redirect(url_for('admin_list'))

    @app.route('/admin/export')
    @admin_required
    def admin_export():
        conn = get_db_connection()
        rows = conn.execute('SELECT id, name, room, title, description, image, status, created_at FROM complaints ORDER BY created_at DESC').fetchall()
        conn.close()
        import csv, io
        si = io.StringIO()
        w = csv.writer(si)
        w.writerow(['id', 'name', 'room', 'title', 'description', 'image', 'status', 'created_at'])
        for r in rows:
            w.writerow([r['id'], r['name'] or '', r['room'] or '', r['title'] or '', r['description'] or '', r['image'] or '', r['status'] or '', r['created_at'] or ''])
        resp = Response(si.getvalue(), mimetype='text/csv')
        resp.headers.set('Content-Disposition', 'attachment', filename='complaints.csv')
        return resp

    @app.route('/admin/export.json')
    @admin_required
    def admin_export_json():
        conn = get_db_connection()
        rows = conn.execute('SELECT id, name, room, title, description, image, status, created_at FROM complaints ORDER BY created_at DESC').fetchall()
        conn.close()
        items = [dict(r) for r in rows]
        return jsonify(items)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        flash('Security token missing or invalid. Please retry the action.', 'danger')
        return redirect(request.referrer or url_for('submit'))

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='127.0.0.1', port=5000)
