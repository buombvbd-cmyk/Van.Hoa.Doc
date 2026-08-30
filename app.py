import os
import json
import mimetypes
import urllib.request
import urllib.parse
import urllib.error

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


# =========================================================
# VAN HOA DOC - SUPABASE VERSION
# =========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "van-hoa-doc-change-me"
)

app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024


# =========================================================
# SUPABASE CONFIG
# =========================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")

STORAGE_BUCKET = "uploads"


# =========================================================
# ALLOWED FILES
# =========================================================

ALLOWED_IMAGES = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp",
}

ALLOWED_VIDEOS = {
    "mp4",
    "webm",
    "mov",
    "quicktime",
}

ALLOWED_FILES = {
    "pdf",
    "doc",
    "docx",
    "ppt",
    "pptx",
    "txt",
}


# =========================================================
# CHECK SUPABASE CONFIG
# =========================================================

def check_supabase_config():
    if not SUPABASE_URL:
        raise RuntimeError("Thiếu SUPABASE_URL")

    if not SUPABASE_SECRET_KEY:
        raise RuntimeError("Thiếu SUPABASE_SECRET_KEY")


# =========================================================
# SUPABASE REST HELPER
# =========================================================

def supabase_request(
    method,
    path,
    data=None,
    params=None,
    extra_headers=None,
):
    check_supabase_config()

    url = f"{SUPABASE_URL}{path}"

    if params:
        query = urllib.parse.urlencode(params)
        url = f"{url}?{query}"

    headers = {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    if extra_headers:
        headers.update(extra_headers)

    body = None

    if data is not None:
        body = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")

            if not raw:
                return []

            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")

        print(
            "SUPABASE ERROR:",
            e.code,
            error_body
        )

        return None

    except Exception as e:
        print("SUPABASE CONNECTION ERROR:", e)
        return None


# =========================================================
# DATABASE FUNCTIONS
# =========================================================

def supabase_get(table, params=None):
    return supabase_request(
        "GET",
        f"/rest/v1/{table}",
        params=params or {},
    )


def supabase_insert(table, data):
    return supabase_request(
        "POST",
        f"/rest/v1/{table}",
        data=data,
        extra_headers={
            "Prefer": "return=representation"
        },
    )


def supabase_update(table, filters, data):
    params = {}

    for key, value in filters.items():
        params[key] = f"eq.{value}"

    return supabase_request(
        "PATCH",
        f"/rest/v1/{table}",
        data=data,
        params=params,
        extra_headers={
            "Prefer": "return=representation"
        },
    )


def supabase_delete(table, filters):
    params = {}

    for key, value in filters.items():
        params[key] = f"eq.{value}"

    return supabase_request(
        "DELETE",
        f"/rest/v1/{table}",
        params=params,
    )


# =========================================================
# USER FUNCTIONS
# =========================================================

def get_user_by_id(user_id):
    result = supabase_get(
        "users",
        {
            "id": f"eq.{user_id}",
            "select": "*",
            "limit": "1",
        },
    )

    if result and isinstance(result, list):
        return result[0]

    return None


def get_user_by_username(username):
    result = supabase_get(
        "users",
        {
            "username": f"eq.{username}",
            "select": "*",
            "limit": "1",
        },
    )

    if result and isinstance(result, list):
        return result[0]

    return None


# =========================================================
# ADMIN INITIALIZATION
# =========================================================

def init_admin():
    try:
        admin = get_user_by_username("admin")

        if not admin:
            result = supabase_insert(
                "users",
                {
                    "username": "admin",
                    "password": generate_password_hash("Admin@123"),
                    "full_name": "Quản trị viên",
                    "role": "admin",
                },
            )

            print("ADMIN CREATED:", result)

    except Exception as e:
        print("ADMIN INIT ERROR:", e)


# =========================================================
# LOGIN REQUIRED
# =========================================================

def login_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if "user_id" not in session:
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped


# =========================================================
# ADMIN REQUIRED
# =========================================================

def admin_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if session.get("role") != "admin":
            abort(403)

        return view(*args, **kwargs)

    return wrapped


# =========================================================
# FILE UPLOAD TO SUPABASE STORAGE
# =========================================================

def save_upload(file_obj, allowed):

    if not file_obj:
        return ""

    if not file_obj.filename:
        return ""

    original_name = secure_filename(file_obj.filename)

    if not original_name:
        return ""

    if "." not in original_name:
        return ""

    ext = original_name.rsplit(".", 1)[-1].lower()

    if ext not in allowed:
        return ""

    unique_name = (
        f"{os.urandom(8).hex()}_{original_name}"
    )

    file_data = file_obj.read()

    content_type = (
        file_obj.mimetype
        or mimetypes.guess_type(original_name)[0]
        or "application/octet-stream"
    )

    path = (
        f"/storage/v1/object/"
        f"{STORAGE_BUCKET}/"
        f"{unique_name}"
    )

    try:

        result = supabase_request(
            "POST",
            path,
            data=None,
            extra_headers={
                "Content-Type": content_type,
                "x-upsert": "false",
            },
        )

        # Request above cannot send binary data.
        # Use direct urllib request instead.

        url = (
            f"{SUPABASE_URL}"
            f"/storage/v1/object/"
            f"{STORAGE_BUCKET}/"
            f"{unique_name}"
        )

        headers = {
            "apikey": SUPABASE_SECRET_KEY,
            "Authorization": (
                f"Bearer {SUPABASE_SECRET_KEY}"
            ),
            "Content-Type": content_type,
            "x-upsert": "false",
        }

        req = urllib.request.Request(
            url,
            data=file_data,
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(
            req,
            timeout=60
        ) as response:

            if response.status not in (200, 201):
                return ""

        return unique_name

    except Exception as e:

        print(
            "UPLOAD ERROR:",
            e
        )

        return ""


# =========================================================
# PUBLIC FILE URL
# =========================================================

def public_file_url(filename):

    if not filename:
        return ""

    return (
        f"{SUPABASE_URL}"
        f"/storage/v1/object/public/"
        f"{STORAGE_BUCKET}/"
        f"{urllib.parse.quote(filename)}"
    )


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    q = request.args.get(
        "q",
        ""
    ).strip()

    posts = supabase_get(
        "posts",
        {
            "select": "*",
            "order": "id.desc",
        },
    )

    if posts is None:
        posts = []

    if q:

        keyword = q.lower()

        posts = [
            post
            for post in posts
            if (
                keyword in str(
                    post.get("book_title", "")
                ).lower()
                or
                keyword in str(
                    post.get("author", "")
                ).lower()
                or
                keyword in str(
                    post.get("impression", "")
                ).lower()
            )
        ]

    users = supabase_get(
        "users",
        {
            "select": "id,full_name,username",
        },
    )

    if users is None:
        users = []

    user_map = {
        str(user["id"]): user
        for user in users
    }

    likes = supabase_get(
        "likes",
        {
            "select": "*",
        },
    )

    if likes is None:
        likes = []

    comments = supabase_get(
        "comments",
        {
            "select": "*",
            "order": "id.desc",
        },
    )

    if comments is None:
        comments = []

    for post in posts:

        user = user_map.get(
            str(post.get("user_id"))
        )

        post["full_name"] = (
            user["full_name"]
            if user
            else "Thành viên"
        )

        post["like_count"] = sum(
            1
            for like in likes
            if str(like.get("post_id"))
            == str(post.get("id"))
        )

        post["comment_count"] = sum(
            1
            for comment in comments
            if str(comment.get("post_id"))
            == str(post.get("id"))
        )

        if post.get("image"):
            post["image_url"] = public_file_url(
                post["image"]
            )

        if post.get("video"):
            post["video_url"] = public_file_url(
                post["video"]
            )

        if post.get("file_name"):
            post["file_url"] = public_file_url(
                post["file_name"]
            )

    comment_map = {}

    for comment in comments:

        post_id = str(
            comment.get("post_id")
        )

        user = user_map.get(
            str(comment.get("user_id"))
        )

        comment["full_name"] = (
            user["full_name"]
            if user
            else "Thành viên"
        )

        comment_map.setdefault(
            post_id,
            []
        ).append(comment)

    return render_template(
        "home.html",
        posts=posts,
        comments=comment_map,
        q=q,
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
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

        user = get_user_by_username(
            username
        )

        if user:

            try:

                valid = check_password_hash(
                    user["password"],
                    password
                )

            except Exception:
                valid = False

            if valid:

                session["user_id"] = user["id"]

                session["full_name"] = (
                    user["full_name"]
                )

                session["role"] = (
                    user.get(
                        "role",
                        "member"
                    )
                )

                return redirect(
                    url_for("home")
                )

        flash(
            "Sai tài khoản hoặc mật khẩu.",
            "error"
        )

    return render_template(
        "login.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# =========================================================
# SHARE BOOK
# =========================================================

@app.route(
    "/share",
    methods=["GET", "POST"]
)
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

            return render_template(
                "share.html"
            )

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

        result = supabase_insert(
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

        if result is None:

            flash(
                "Không thể lưu bài đăng. Kiểm tra Supabase.",
                "error"
            )

            return render_template(
                "share.html"
            )

        flash(
            "Đã chia sẻ trang sách thành công.",
            "success"
        )

        return redirect(
            url_for("home")
        )

    return render_template(
        "share.html"
    )


# =========================================================
# LIKE
# =========================================================

@app.post(
    "/post/<int:post_id>/like"
)
@login_required
def like(post_id):

    user_id = session["user_id"]

    existing = supabase_get(
        "likes",
        {
            "post_id": f"eq.{post_id}",
            "user_id": f"eq.{user_id}",
            "select": "id",
            "limit": "1",
        },
    )

    if existing:

        supabase_delete(
            "likes",
            {
                "id": existing[0]["id"]
            }
        )

    else:

        supabase_insert(
            "likes",
            {
                "post_id": post_id,
                "user_id": user_id,
            }
        )

    return redirect(
        request.referrer
        or url_for("home")
    )


# =========================================================
# COMMENT
# =========================================================

@app.post(
    "/post/<int:post_id>/comment"
)
@login_required
def comment(post_id):

    content = request.form.get(
        "content",
        ""
    ).strip()

    if content:

        supabase_insert(
            "comments",
            {
                "post_id": post_id,
                "user_id": session["user_id"],
                "content": content,
            },
        )

    return redirect(
        request.referrer
        or url_for("home")
    )


# =========================================================
# ADMIN
# =========================================================

@app.route(
    "/admin",
    methods=["GET", "POST"]
)
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

        if (
            not full_name
            or not username
            or not password
        ):

            flash(
                "Vui lòng điền đủ thông tin.",
                "error"
            )

        else:

            existing = get_user_by_username(
                username
            )

            if existing:

                flash(
                    "Tên tài khoản đã tồn tại.",
                    "error"
                )

            else:

                result = supabase_insert(
                    "users",
                    {
                        "username": username,
                        "password": (
                            generate_password_hash(
                                password
                            )
                        ),
                        "full_name": full_name,
                        "role": "member",
                    },
                )

                if result is not None:

                    flash(
                        "Đã cấp tài khoản thành viên.",
                        "success"
                    )

                else:

                    flash(
                        "Không thể tạo tài khoản.",
                        "error"
                    )

    users = supabase_get(
        "users",
        {
            "select": "id,full_name,username,role",
            "order": "id.desc",
        },
    )

    if users is None:
        users = []

    posts = supabase_get(
        "posts",
        {
            "select": "id,book_title,created_at,user_id",
            "order": "id.desc",
        },
    )

    if posts is None:
        posts = []

    user_map = {
        str(user["id"]): user
        for user in users
    }

    for post in posts:

        user = user_map.get(
            str(post.get("user_id"))
        )

        post["full_name"] = (
            user["full_name"]
            if user
            else "Thành viên"
        )

    all_likes = supabase_get(
        "likes",
        {
            "select": "id",
        },
    )

    all_comments = supabase_get(
        "comments",
        {
            "select": "id",
        },
    )

    if all_likes is None:
        all_likes = []

    if all_comments is None:
        all_comments = []

    stats = {
        "members": len(users),
        "posts": len(posts),
        "likes": len(all_likes),
        "comments": len(all_comments),
    }

    return render_template(
        "admin.html",
        users=users,
        posts=posts,
        stats=stats,
    )


# =========================================================
# DELETE POST
# =========================================================

@app.post(
    "/admin/post/<int:post_id>/delete"
)
@login_required
@admin_required
def delete_post(post_id):

    result = supabase_delete(
        "posts",
        {
            "id": post_id
        },
    )

    if result is not None:

        flash(
            "Đã xóa bài đăng.",
            "success"
        )

    else:

        flash(
            "Không thể xóa bài đăng.",
            "error"
        )

    return redirect(
        url_for("admin")
    )


# =========================================================
# 403
# =========================================================

@app.errorhandler(403)
def forbidden(_):

    return (
        "Bạn không có quyền truy cập.",
        403
    )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    return {
        "status": "ok",
        "service": "VanHoaDoc",
        "supabase": bool(
            SUPABASE_URL
            and SUPABASE_SECRET_KEY
        ),
    }


# =========================================================
# STARTUP
# =========================================================

try:
    init_admin()
except Exception as e:
    print("STARTUP ERROR:", e)


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
