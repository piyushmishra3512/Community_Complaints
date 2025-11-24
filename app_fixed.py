import os
import sqlite3
import uuid
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session, Response, jsonify
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
        conn.execute(
            '''
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
            '''
        )
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

    # Admin routes
    @app.route('/admin/login', methods=['GET', 'POST'])
    def admin_login():
        if request.method == 'POST':
            pwd = request.form.get('password')
            if pwd == app.config['ADMIN_PASSWORD']:
                session['admin'] = True
                return redirect(url_for('admin_list'))
            flash('Invalid password', 'danger')
        return render_template('admin_login.html')

    def admin_required(func):
        from functools import wraps
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not session.get('admin'):
                return redirect(url_for('admin_login'))
            return func(*args, **kwargs)
        return wrapper

    @app.route('/admin/list')
    @admin_required
    def admin_list():
        status = request.args.get('status')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')

        sql = 'SELECT * FROM complaints'
        where = []
        params = []
        if status:
            where.append('status = ?')
            params.append(status)
        if date_from:
            where.append('created_at >= ?')
            params.append(date_from)
        if date_to:
            where.append('created_at <= ?')
            params.append(date_to + 'T23:59:59')
        if where:
            sql += ' WHERE ' + ' AND '.join(where)
        sql += ' ORDER BY created_at DESC'

        conn = get_db_connection()
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return render_template('admin_list.html', complaints=rows)

    @app.route('/admin/status')
    @admin_required
    def admin_status():
        db_path = app.config['DATABASE']
        info = {'db_path': db_path, 'exists': False, 'size_bytes': None, 'complaint_count': 0}
        try:
            if os.path.exists(db_path):
                info['exists'] = True
                info['size_bytes'] = os.path.getsize(db_path)
                conn = get_db_connection()
                cur = conn.execute('SELECT COUNT(*) FROM complaints')
                info['complaint_count'] = cur.fetchone()[0]
                conn.close()
        except Exception:
            pass
        return render_template('admin_status.html', info=info)

    @app.route('/admin/check_password', methods=['GET', 'POST'])
    def admin_check_password():
        if request.remote_addr not in ('127.0.0.1', '::1', 'localhost'):
            return ('Forbidden', 403)
        if request.method == 'POST':
            candidate = request.form.get('password') or (request.json and request.json.get('password'))
            ok = (candidate == app.config.get('ADMIN_PASSWORD'))
            if request.content_type and 'application/x-www-form-urlencoded' in request.content_type:
                flash('Password match: {}'.format(ok), 'info')
                return redirect(url_for('admin_login'))
            return jsonify({'match': ok})
        return render_template('admin_check_password.html')

    @app.route('/admin/export')
    @admin_required
    def admin_export():
        status = request.args.get('status')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')

        sql = 'SELECT id, name, room, title, description, image, status, created_at FROM complaints'
        where = []
        params = []
        if status:
            where.append('status = ?')
            params.append(status)
        if date_from:
            where.append('created_at >= ?')
            params.append(date_from)
        if date_to:
            where.append('created_at <= ?')
            params.append(date_to + 'T23:59:59')
        if where:
            sql += ' WHERE ' + ' AND '.join(where)
        sql += ' ORDER BY created_at DESC'

        conn = get_db_connection()
        rows = conn.execute(sql, params).fetchall()
        conn.close()

        import csv, io
        si = io.StringIO()
        writer = csv.writer(si)
        writer.writerow(['id', 'name', 'room', 'title', 'description', 'image', 'status', 'created_at'])
        for r in rows:
            writer.writerow([
                r['id'],
                r['name'] or '',
                r['room'] or '',
                r['title'] or '',
                r['description'] or '',
                r['image'] or '',
                r['status'] or '',
                r['created_at'] or ''
            ])
        csv_data = si.getvalue()
        resp = Response(csv_data, mimetype='text/csv')
        resp.headers.set('Content-Disposition', 'attachment', filename='complaints.csv')
        return resp

        
*** End Patch