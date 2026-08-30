import os
import requests
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    abort,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


# ============================================================
# CẤU HÌNH
# ============================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "van-hoa-doc-change-me"
)

app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")

STORAGE_BUCKET = "uploads"

ALLOWED_IMAGES = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_VIDEOS = {"mp4", "webm", "mov"}
ALLOWED_FILES = {"pdf", "doc", "docx", "ppt", "pptx", "txt"}


# ============================================================
# KIỂM TRA SUPABASE
# ============================================================

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    print("WARNING: Chưa cấu hình SUPABASE_URL hoặc SUPABASE_SECRET_KEY")


# ============================================================
# SUPABASE REST API
# ============================================================

def supabase_headers():
    return {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def supabase_get(table, params=None):
    url = f"{SUPABASE_URL}/rest/v1/{table}"

    response = requests.get(
        url,
        headers=supabase_headers(),
        params=params or {},
        timeout=30,
    )

    if not response.ok:
        print("SUPABASE GET ERROR:", response.text)

    response.raise_for_status()
    return response.json()


def supabase_post(table, data):
    url = f"{SUPABASE_URL}/rest/v1/{table}"

    headers = supabase_headers()
    headers["Prefer"] = "return=representation"

    response = requests.post(
        url,
        headers=headers,
        json=data,
        timeout=30,
    )

    if not response.ok:
        print("SUPABASE POST ERROR:", response.text)

    response.raise_for_status()
    return response.json()


def supabase_delete(table, params):
    url = f"{SUPABASE_URL}/rest/v1/{table}"

    response = requests.delete(
        url,
        headers=supabase_headers(),
        params=params,
        timeout=30,
    )

    if not response.ok:
        print("SUPABASE DELETE ERROR:", response.text)

    response.raise_for_status()
    return response


# ============================================================
# STORAGE
# ============================================================

def save_upload(file_obj, allowed):
    """
    Upload file lên Supabase Storage.
    Trả về URL công khai của file.
    """

    if not file_obj or not file_obj.filename:
        return ""

    original_name = secure_filename(file_obj.filename)

    if not original_name:
        return ""

    if "." not in original_name:
        return ""

    ext = original_name.rsplit(".", 1)[-1].lower()

    if ext not in allowed:
        return ""

    unique_name = f"{os.urandom(8).hex()}_{original_name}"

    file_bytes = file_obj.read()

    content_type = file_obj.mimetype or "application/octet-stream"

    upload_url = (
        f"{SUPABASE_URL}/storage/v1/object/"
        f"{STORAGE_BUCKET}/{unique_name}"
    )

    headers = {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
        "Content-Type": content_type,
        "x-upsert": "false",
    }

    response = requests.post(
        upload_url,
        headers=headers,
        data=file_bytes,
        timeout=120,
    )

    if not response.ok:
        print("STORAGE UPLOAD ERROR:", response.text)
        return ""

    # Bucket uploads của bạn đang là PUBLIC
    public_url = (
        f"{SUPABASE_URL}/storage/v1/object/public/"
        f"{STORAGE_BUCKET}/{unique_name}"
    )

    return public_url


def delete_storage_file(public_url):
    """
    Xóa file trên Supabase Storage nếu có.
    """

    if not public_url:
        return

    marker = f"/storage/v1/object/public/{STORAGE_BUCKET}/"

    if marker not in public_url:
        return

    file_path = public_url.split(marker, 1)[1]

    delete_url = (
        f"{SUPABASE_URL}/storage/v1/object/"
        f"{STORAGE_BUCKET}/{file_path}"
    )

    headers = {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
    }

    try:
        response = requests.delete(
            delete_url,
            headers=headers,
            timeout=30,
        )

        if not response.ok:
            print("STORAGE DELETE ERROR:", response.text)

    except Exception as e:
        print("STORAGE DELETE EXCEPTION:", e)


# ============================================================
# KHỞI TẠO ADMIN
# ============================================================

def init_admin():
    try:
        users = supabase_get(
            "users",
            {
                "select": "id,username",
                "username": "eq.admin",
                "limit": "1",
            },
        )

        if users:
            return

        supabase_post(
            "users",
            {
                "username": "admin",
                "password": generate_password_hash("Admin@123"),
                "full_name": "Quản trị viên",
                "role": "admin",
            },
        )

        print("Đã tạo tài khoản admin.")

    except Exception as e:
        print("INIT ADMIN ERROR:", e)


# ============================================================
# ĐĂNG NHẬP
# ============================================================

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


# ============================================================
# TRANG CHỦ
# ============================================================

@app.route("/")
def home():

    q = request.args.get("q", "").strip().lower()

    try:

        posts = supabase_get(
            "posts",
            {
                "select": "*,users(id,full_name)",
                "order": "created_at.desc",
            },
        )

        # Chuẩn hóa dữ liệu user
        for post in posts:

            user_data = post.get("users") or {}

            post["full_name"] = user_data.get(
                "full_name",
                "Thành viên"
            )

            # Like count
            likes = supabase_get(
                "likes",
                {
                    "select": "id",
                    "post_id": f"eq.{post['id']}",
                },
            )

            post["like_count"] = len(likes)

            # Comment count
            comments = supabase_get(
                "comments",
                {
                    "select": "id",
                    "post_id": f"eq.{post['id']}",
                },
            )

            post["comment_count"] = len(comments)

        # Tìm kiếm
        if q:

            filtered_posts = []

            for post in posts:

                text = " ".join(
                    [
                        str(post.get("book_title", "")),
                        str(post.get("author", "")),
                        str(post.get("impression", "")),
                        str(post.get("full_name", "")),
                    ]
                ).lower()

                if q in text:
                    filtered_posts.append(post)

            posts = filtered_posts

        # Lấy comments
        comments = {}

        for post in posts:

            post_comments = supabase_get(
                "comments",
                {
                    "select": "*,users(full_name)",
                    "post_id": f"eq.{post['id']}",
                    "order": "created_at.desc",
                },
            )

            for comment in post_comments:

                user_data = comment.get("users") or {}

                comment["full_name"] = user_data.get(
                    "full_name",
                    "Thành viên"
                )

            comments[post["id"]] = post_comments

        return render_template(
            "home.html",
            posts=posts,
            comments=comments,
            q=q,
        )

    except Exception as e:

        print("HOME ERROR:", e)

        flash(
            "Không thể tải dữ liệu. Vui lòng thử lại.",
            "error"
        )

        return render_template(
            "home.html",
            posts=[],
            comments={},
            q=q,
        )


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        try:

            users = supabase_get(
                "users",
                {
                    "select": "*",
                    "username": f"eq.{username}",
                    "limit": "1",
                },
            )

            user = users[0] if users else None

        except Exception as e:

            print("LOGIN ERROR:", e)

            flash(
                "Không thể kết nối cơ sở dữ liệu.",
                "error"
            )

            return render_template("login.html")

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]

            return redirect(url_for("home"))

        flash(
            "Sai tài khoản hoặc mật khẩu.",
            "error"
        )

    return render_template("login.html")


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# ============================================================
# CHIA SẺ TRANG SÁCH
# ============================================================

@app.route("/share", methods=["GET", "POST"])
@login_required
def share():

    if request.method == "POST":

        title = request.form.get(
            "book_title",
            ""
        ).strip()

        author = request.form.get(
            "author",
            ""
        ).strip()

        impression = request.form.get(
            "impression",
            ""
        ).strip()

        external_url = request.form.get(
            "url",
            ""
        ).strip()

        if not title or not impression:

            flash(
                "Vui lòng nhập tên sách và điều bạn ấn tượng.",
                "error"
            )

            return render_template("share.html")

        try:

            image = save_upload(
                request.files.get("image"),
                ALLOWED_IMAGES
            )

            video = save_upload(
                request.files.get("video"),
                ALLOWED_VIDEOS
            )

            file_name = save_upload(
                request.files.get("file"),
                ALLOWED_FILES
            )

            supabase_post(
                "posts",
                {
                    "user_id": session["user_id"],
                    "book_title": title,
                    "author": author,
                    "impression": impression,
                    "image": image,
                    "video": video,
                    "file_name": file_name,
                    "url": external_url,
                },
            )

            flash(
                "Đã chia sẻ trang sách thành công.",
                "success"
            )

            return redirect(url_for("home"))

        except Exception as e:

            print("SHARE ERROR:", e)

            flash(
                "Không thể đăng bài. Vui lòng kiểm tra lại.",
                "error"
            )

            return render_template("share.html")

    return render_template("share.html")


# ============================================================
# LIKE
# ============================================================

@app.post("/post/<int:post_id>/like")
@login_required
def like(post_id):

    try:

        existing = supabase_get(
            "likes",
            {
                "select": "id",
                "post_id": f"eq.{post_id}",
                "user_id": f"eq.{session['user_id']}",
                "limit": "1",
            },
        )

        if existing:

            supabase_delete(
                "likes",
                {
                    "id": f"eq.{existing[0]['id']}"
                },
            )

        else:

            supabase_post(
                "likes",
                {
                    "post_id": post_id,
                    "user_id": session["user_id"],
                },
            )

    except Exception as e:

        print("LIKE ERROR:", e)

    return redirect(
        request.referrer or url_for("home")
    )


# ============================================================
# COMMENT
# ============================================================

@app.post("/post/<int:post_id>/comment")
@login_required
def comment(post_id):

    content = request.form.get(
        "content",
        ""
    ).strip()

    if content:

        try:

            supabase_post(
                "comments",
                {
                    "post_id": post_id,
                    "user_id": session["user_id"],
                    "content": content,
                },
            )

        except Exception as e:

            print("COMMENT ERROR:", e)

    return redirect(
        request.referrer or url_for("home")
    )


# ============================================================
# ADMIN
# ============================================================

@app.route("/admin", methods=["GET", "POST"])
@login_required
@admin_required
def admin():

    if request.method == "POST":

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if not full_name or not username or not password:

            flash(
                "Vui lòng điền đủ thông tin.",
                "error"
            )

        else:

            try:

                existing = supabase_get(
                    "users",
                    {
                        "select": "id",
                        "username": f"eq.{username}",
                        "limit": "1",
                    },
                )

                if existing:

                    flash(
                        "Tên tài khoản đã tồn tại.",
                        "error"
                    )

                else:

                    supabase_post(
                        "users",
                        {
                            "username": username,
                            "password": generate_password_hash(password),
                            "full_name": full_name,
                            "role": "member",
                        },
                    )

                    flash(
                        "Đã cấp tài khoản thành viên.",
                        "success"
                    )

            except Exception as e:

                print("ADMIN USER ERROR:", e)

                flash(
                    "Không thể tạo tài khoản.",
                    "error"
                )

    try:

        users = supabase_get(
            "users",
            {
                "select": "id,full_name,username,role",
                "order": "id.desc",
            },
        )

        posts = supabase_get(
            "posts",
            {
                "select": "id,book_title,created_at,users(full_name)",
                "order": "created_at.desc",
            },
        )

        for post in posts:

            user_data = post.get("users") or {}

            post["full_name"] = user_data.get(
                "full_name",
                "Thành viên"
            )

        likes = supabase_get(
            "likes",
            {
                "select": "id"
            },
        )

        comments = supabase_get(
            "comments",
            {
                "select": "id"
            },
        )

        stats = {
            "members": len(users),
            "posts": len(posts),
            "likes": len(likes),
            "comments": len(comments),
        }

        return render_template(
            "admin.html",
            users=users,
            posts=posts,
            stats=stats,
        )

    except Exception as e:

        print("ADMIN ERROR:", e)

        flash(
            "Không thể tải trang quản trị.",
            "error"
        )

        return redirect(url_for("home"))


# ============================================================
# XÓA BÀI
# ============================================================

@app.post("/admin/post/<int:post_id>/delete")
@login_required
@admin_required
def delete_post(post_id):

    try:

        posts = supabase_get(
            "posts",
            {
                "select": "image,video,file_name",
                "id": f"eq.{post_id}",
                "limit": "1",
            },
        )

        if posts:

            post = posts[0]

            delete_storage_file(
                post.get("image", "")
            )

            delete_storage_file(
                post.get("video", "")
            )

            delete_storage_file(
                post.get("file_name", "")
            )

        # Xóa comments
        supabase_delete(
            "comments",
            {
                "post_id": f"eq.{post_id}"
            },
        )

        # Xóa likes
        supabase_delete(
            "likes",
            {
                "post_id": f"eq.{post_id}"
            },
        )

        # Xóa post
        supabase_delete(
            "posts",
            {
                "id": f"eq.{post_id}"
            },
        )

        flash(
            "Đã xóa bài đăng.",
            "success"
        )

    except Exception as e:

        print("DELETE POST ERROR:", e)

        flash(
            "Không thể xóa bài đăng.",
            "error"
        )

    return redirect(url_for("admin"))


# ============================================================
# ERROR
# ============================================================

@app.errorhandler(403)
def forbidden(_):

    return "Bạn không có quyền truy cập.", 403


# ============================================================
# START
# ============================================================

init_admin()


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
    )
