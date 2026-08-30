import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "database.db")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "van-hoa-doc-change-me")
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

ALLOWED_IMAGES = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_VIDEOS = {"mp4", "webm", "mov"}
ALLOWED_FILES = {"pdf", "doc", "docx", "ppt", "pptx", "txt"}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'member'
    );

    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        book_title TEXT NOT NULL,
        author TEXT DEFAULT '',
        impression TEXT NOT NULL,
        image TEXT DEFAULT '',
        video TEXT DEFAULT '',
        file_name TEXT DEFAULT '',
        url TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        UNIQUE(post_id, user_id),
        FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    admin = conn.execute("SELECT id FROM users WHERE username = ?", ("admin",)).fetchone()
    if not admin:
        conn.execute(
            "INSERT INTO users(username,password,full_name,role) VALUES(?,?,?,?)",
            ("admin", generate_password_hash("Admin@123"), "Quản trị viên", "admin")
        )
    conn.commit()
    conn.close()

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped

def save_upload(file_obj, allowed):
    if not file_obj or not file_obj.filename:
        return ""
    ext = file_obj.filename.rsplit(".", 1)[-1].lower()
    if ext not in allowed:
        return ""
    safe = secure_filename(file_obj.filename)
    unique = f"{os.urandom(8).hex()}_{safe}"
    file_obj.save(os.path.join(UPLOAD_DIR, unique))
    return unique

@app.context_processor
def inject_counts():
    return {}

@app.route("/")
def home():
    q = request.args.get("q", "").strip()
    conn = get_db()

    base = """
        SELECT p.*, u.full_name,
        (SELECT COUNT(*) FROM likes l WHERE l.post_id=p.id) AS like_count,
        (SELECT COUNT(*) FROM comments c WHERE c.post_id=p.id) AS comment_count
        FROM posts p JOIN users u ON u.id=p.user_id
    """
    if q:
        posts = conn.execute(
            base + """
            WHERE p.book_title LIKE ? OR p.author LIKE ? OR p.impression LIKE ? OR u.full_name LIKE ?
            ORDER BY p.id DESC
            """,
            tuple(f"%{q}%" for _ in range(4))
        ).fetchall()
    else:
        posts = conn.execute(base + " ORDER BY p.id DESC").fetchall()

    comments = {}
    for post in posts:
        comments[post["id"]] = conn.execute("""
            SELECT c.*, u.full_name
            FROM comments c JOIN users u ON u.id=c.user_id
            WHERE c.post_id=?
            ORDER BY c.id DESC
        """, (post["id"],)).fetchall()

    conn.close()
    return render_template("home.html", posts=posts, comments=comments, q=q)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]
            return redirect(url_for("home"))

        flash("Sai tài khoản hoặc mật khẩu.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/share", methods=["GET", "POST"])
@login_required
def share():
    if request.method == "POST":
        title = request.form.get("book_title", "").strip()
        author = request.form.get("author", "").strip()
        impression = request.form.get("impression", "").strip()
        external_url = request.form.get("url", "").strip()

        if not title or not impression:
            flash("Vui lòng nhập tên sách và điều bạn ấn tượng.", "error")
            return render_template("share.html")

        image = save_upload(request.files.get("image"), ALLOWED_IMAGES)
        video = save_upload(request.files.get("video"), ALLOWED_VIDEOS)
        file_name = save_upload(request.files.get("file"), ALLOWED_FILES)

        conn = get_db()
        conn.execute("""
            INSERT INTO posts(user_id,book_title,author,impression,image,video,file_name,url)
            VALUES(?,?,?,?,?,?,?,?)
        """, (
            session["user_id"], title, author, impression,
            image, video, file_name, external_url
        ))
        conn.commit()
        conn.close()
        flash("Đã chia sẻ trang sách thành công.", "success")
        return redirect(url_for("home"))

    return render_template("share.html")

@app.post("/post/<int:post_id>/like")
@login_required
def like(post_id):
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM likes WHERE post_id=? AND user_id=?",
        (post_id, session["user_id"])
    ).fetchone()
    if existing:
        conn.execute("DELETE FROM likes WHERE id=?", (existing["id"],))
    else:
        conn.execute(
            "INSERT OR IGNORE INTO likes(post_id,user_id) VALUES(?,?)",
            (post_id, session["user_id"])
        )
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("home"))

@app.post("/post/<int:post_id>/comment")
@login_required
def comment(post_id):
    content = request.form.get("content", "").strip()
    if content:
        conn = get_db()
        conn.execute(
            "INSERT INTO comments(post_id,user_id,content) VALUES(?,?,?)",
            (post_id, session["user_id"], content)
        )
        conn.commit()
        conn.close()
    return redirect(request.referrer or url_for("home"))

@app.route("/admin", methods=["GET", "POST"])
@login_required
@admin_required
def admin():
    conn = get_db()

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not full_name or not username or not password:
            flash("Vui lòng điền đủ thông tin.", "error")
        else:
            try:
                conn.execute(
                    "INSERT INTO users(username,password,full_name,role) VALUES(?,?,?,'member')",
                    (username, generate_password_hash(password), full_name)
                )
                conn.commit()
                flash("Đã cấp tài khoản thành viên.", "success")
            except sqlite3.IntegrityError:
                flash("Tên tài khoản đã tồn tại.", "error")

    users = conn.execute(
        "SELECT id,full_name,username,role FROM users ORDER BY id DESC"
    ).fetchall()
    posts = conn.execute("""
        SELECT p.id,p.book_title,p.created_at,u.full_name
        FROM posts p JOIN users u ON u.id=p.user_id
        ORDER BY p.id DESC
    """).fetchall()
    stats = {
        "members": conn.execute("SELECT COUNT(*) n FROM users").fetchone()["n"],
        "posts": conn.execute("SELECT COUNT(*) n FROM posts").fetchone()["n"],
        "likes": conn.execute("SELECT COUNT(*) n FROM likes").fetchone()["n"],
        "comments": conn.execute("SELECT COUNT(*) n FROM comments").fetchone()["n"],
    }
    conn.close()
    return render_template("admin.html", users=users, posts=posts, stats=stats)

@app.post("/admin/post/<int:post_id>/delete")
@login_required
@admin_required
def delete_post(post_id):
    conn = get_db()
    conn.execute("DELETE FROM posts WHERE id=?", (post_id,))
    conn.commit()
    conn.close()
    flash("Đã xóa bài đăng.", "success")
    return redirect(url_for("admin"))

@app.route("/uploads/<path:name>")
def uploads(name):
    return send_from_directory(UPLOAD_DIR, name)

@app.errorhandler(403)
def forbidden(_):
    return "Bạn không có quyền truy cập.", 403

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
