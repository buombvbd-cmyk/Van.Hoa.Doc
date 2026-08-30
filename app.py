import os
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
from supabase import create_client


# =========================================================
# CẤU HÌNH
# =========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "van-hoa-doc-secret-key"
)

app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024


SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    raise RuntimeError(
        "Thiếu SUPABASE_URL hoặc SUPABASE_SECRET_KEY"
    )

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY
)


BUCKET_NAME = "uploads"

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
# HÀM TIỆN ÍCH
# =========================================================

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


def allowed_file(filename, allowed):
    if not filename or "." not in filename:
        return False

    ext = filename.rsplit(".", 1)[1].lower()

    return ext in allowed


def upload_to_supabase(file_obj, allowed):
    """
    Upload file lên Supabase Storage.
    Trả về URL công khai.
    """

    if not file_obj or not file_obj.filename:
        return ""

    filename = secure_filename(file_obj.filename)

    if not allowed_file(filename, allowed):
        return ""

    ext = filename.rsplit(".", 1)[1].lower()

    unique_name = (
        os.urandom(8).hex()
        + "_"
        + filename
    )

    path = f"{unique_name}"

    data = file_obj.read()

    try:
        supabase.storage.from_(BUCKET_NAME).upload(
            path,
            data,
            {
                "content-type": file_obj.content_type
                or "application/octet-stream"
            },
        )

        public_url = (
            f"{SUPABASE_URL}/storage/v1/object/public/"
            f"{BUCKET_NAME}/{path}"
        )

        return public_url

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return ""


# =========================================================
# TẠO ADMIN MẶC ĐỊNH
# =========================================================

def ensure_admin():
    """
    Đảm bảo tài khoản admin tồn tại.

    Tài khoản:
        username: admin
        password: Admin@123
    """

    try:
        result = (
            supabase
            .table("users")
            .select("*")
            .eq("username", "admin")
            .limit(1)
            .execute()
        )

        users = result.data or []

        password_hash = generate_password_hash(
            "Admin@123"
        )

        if not users:

            supabase.table("users").insert({
                "username": "admin",
                "password": password_hash,
                "full_name": "Quản trị viên",
                "role": "admin",
            }).execute()

            print("Đã tạo tài khoản admin.")

        else:

            user = users[0]

            # Nếu tài khoản admin đang có hash cũ
            # thì cập nhật về mật khẩu mặc định.
            try:
                valid = check_password_hash(
                    user["password"],
                    "Admin@123"
                )
            except Exception:
                valid = False

            if not valid:
                supabase.table("users").update({
                    "password": password_hash,
                    "role": "admin",
                    "full_name": "Quản trị viên",
                }).eq(
                    "id",
                    user["id"]
                ).execute()

                print(
                    "Đã cập nhật mật khẩu admin."
                )

    except Exception as e:
        print("ADMIN INIT ERROR:", e)


# =========================================================
# TRANG CHỦ
# =========================================================

@app.route("/")
def home():

    q = request.args.get(
        "q",
        ""
    ).strip()

    try:

        query = (
            supabase
            .table("posts")
            .select(
                "*, users!posts_user_id_fkey(full_name)"
            )
            .order(
                "id",
                desc=True
            )
        )

        result = query.execute()

        posts = result.data or []

    except Exception as e:

        print("HOME ERROR:", e)

        posts = []

    # Tìm kiếm phía Python
    if q:

        keyword = q.lower()

        filtered = []

        for post in posts:

            user = post.get("users") or {}

            full_name = user.get(
                "full_name",
                ""
            )

            text = " ".join([
                str(post.get("book_title", "")),
                str(post.get("author", "")),
                str(post.get("impression", "")),
                str(full_name),
            ]).lower()

            if keyword in text:
                filtered.append(post)

        posts = filtered

    # -----------------------------------------------------
    # LIKE + COMMENT
    # -----------------------------------------------------

    comments = {}

    for post in posts:

        post_id = post["id"]

        try:

            likes_result = (
                supabase
                .table("likes")
                .select("id")
                .eq("post_id", post_id)
                .execute()
            )

            post["like_count"] = len(
                likes_result.data or []
            )

        except Exception:

            post["like_count"] = 0

        try:

            comments_result = (
                supabase
                .table("comments")
                .select(
                    "*, users!comments_user_id_fkey(full_name)"
                )
                .eq(
                    "post_id",
                    post_id
                )
                .order(
                    "id",
                    desc=True
                )
                .execute()
            )

            rows = comments_result.data or []

            comments[post_id] = rows

            post["comment_count"] = len(rows)

        except Exception:

            comments[post_id] = []

            post["comment_count"] = 0

    return render_template(
        "home.html",
        posts=posts,
        comments=comments,
        q=q
    )


# =========================================================
# ĐĂNG NHẬP
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

        if not username or not password:

            flash(
                "Vui lòng nhập tài khoản và mật khẩu.",
                "error"
            )

            return render_template(
                "login.html"
            )

        try:

            result = (
                supabase
                .table("users")
                .select("*")
                .eq(
                    "username",
                    username
                )
                .limit(1)
                .execute()
            )

            users = result.data or []

            user = users[0] if users else None

        except Exception as e:

            print("LOGIN ERROR:", e)

            user = None

        if user:

            try:

                password_ok = check_password_hash(
                    user["password"],
                    password
                )

            except Exception:

                password_ok = False

            if password_ok:

                session["user_id"] = user["id"]

                session["username"] = (
                    user["username"]
                )

                session["full_name"] = (
                    user["full_name"]
                )

                session["role"] = (
                    user["role"]
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
# ĐĂNG XUẤT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# =========================================================
# CHIA SẺ TRANG SÁCH
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

        image = upload_to_supabase(
            request.files.get("image"),
            ALLOWED_IMAGES
        )

        video = upload_to_supabase(
            request.files.get("video"),
            ALLOWED_VIDEOS
        )

        file_url = upload_to_supabase(
            request.files.get("file"),
            ALLOWED_FILES
        )

        try:

            supabase.table("posts").insert({

                "user_id": session["user_id"],

                "book_title": title,

                "author": author,

                "impression": impression,

                "image": image,

                "video": video,

                "file_name": file_url,

                "url": external_url,

            }).execute()

            flash(
                "Đã chia sẻ trang sách thành công.",
                "success"
            )

            return redirect(
                url_for("home")
            )

        except Exception as e:

            print("POST ERROR:", e)

            flash(
                "Không thể đăng bài. Vui lòng thử lại.",
                "error"
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

    try:

        result = (
            supabase
            .table("likes")
            .select("id")
            .eq(
                "post_id",
                post_id
            )
            .eq(
                "user_id",
                user_id
            )
            .limit(1)
            .execute()
        )

        existing = result.data or []

        if existing:

            supabase.table(
                "likes"
            ).delete().eq(
                "id",
                existing[0]["id"]
            ).execute()

        else:

            supabase.table(
                "likes"
            ).insert({
                "post_id": post_id,
                "user_id": user_id
            }).execute()

    except Exception as e:

        print("LIKE ERROR:", e)

    return redirect(
        request.referrer
        or url_for("home")
    )


# =========================================================
# BÌNH LUẬN
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

        try:

            supabase.table(
                "comments"
            ).insert({

                "post_id": post_id,

                "user_id": session["user_id"],

                "content": content,

            }).execute()

        except Exception as e:

            print("COMMENT ERROR:", e)

    return redirect(
        request.referrer
        or url_for("home")
    )


# =========================================================
# QUẢN TRỊ
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

            try:

                existing = (
                    supabase
                    .table("users")
                    .select("id")
                    .eq(
                        "username",
                        username
                    )
                    .limit(1)
                    .execute()
                )

                if existing.data:

                    flash(
                        "Tên tài khoản đã tồn tại.",
                        "error"
                    )

                else:

                    supabase.table(
                        "users"
                    ).insert({

                        "username": username,

                        "password":
                            generate_password_hash(
                                password
                            ),

                        "full_name": full_name,

                        "role": "member",

                    }).execute()

                    flash(
                        "Đã cấp tài khoản thành viên.",
                        "success"
                    )

            except Exception as e:

                print("CREATE USER ERROR:", e)

                flash(
                    "Không thể tạo tài khoản.",
                    "error"
                )

    # -----------------------------------------------------
    # USERS
    # -----------------------------------------------------

    try:

        users_result = (
            supabase
            .table("users")
            .select(
                "id,full_name,username,role"
            )
            .order(
                "id",
                desc=True
            )
            .execute()
        )

        users = users_result.data or []

    except Exception:

        users = []

    # -----------------------------------------------------
    # POSTS
    # -----------------------------------------------------

    try:

        posts_result = (
            supabase
            .table("posts")
            .select(
                "id,book_title,created_at,"
                "users!posts_user_id_fkey(full_name)"
            )
            .order(
                "id",
                desc=True
            )
            .execute()
        )

        posts = posts_result.data or []

    except Exception:

        posts = []

    # -----------------------------------------------------
    # STATS
    # -----------------------------------------------------

    try:

        members = (
            supabase
            .table("users")
            .select("id", count="exact")
            .execute()
            .count
            or 0
        )

    except Exception:

        members = 0

    try:

        post_count = (
            supabase
            .table("posts")
            .select("id", count="exact")
            .execute()
            .count
            or 0
        )

    except Exception:

        post_count = 0

    try:

        like_count = (
            supabase
            .table("likes")
            .select("id", count="exact")
            .execute()
            .count
            or 0
        )

    except Exception:

        like_count = 0

    try:

        comment_count = (
            supabase
            .table("comments")
            .select("id", count="exact")
            .execute()
            .count
            or 0
        )

    except Exception:

        comment_count = 0

    stats = {

        "members": members,

        "posts": post_count,

        "likes": like_count,

        "comments": comment_count,

    }

    return render_template(
        "admin.html",
        users=users,
        posts=posts,
        stats=stats
    )


# =========================================================
# XÓA BÀI
# =========================================================

@app.post(
    "/admin/post/<int:post_id>/delete"
)
@login_required
@admin_required
def delete_post(post_id):

    try:

        supabase.table(
            "posts"
        ).delete().eq(
            "id",
            post_id
        ).execute()

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

    return redirect(
        url_for("admin")
    )


# =========================================================
# LỖI 403
# =========================================================

@app.errorhandler(403)
def forbidden(_):

    return (
        "Bạn không có quyền truy cập.",
        403
    )


# =========================================================
# KIỂM TRA SUPABASE
# =========================================================

@app.route("/health")
def health():

    try:

        result = (
            supabase
            .table("users")
            .select("id")
            .limit(1)
            .execute()
        )

        return {
            "service": "VanHoaDoc",
            "status": "ok",
            "supabase": True,
        }

    except Exception as e:

        return {
            "service": "VanHoaDoc",
            "status": "error",
            "supabase": False,
            "message": str(e),
        }, 500


# =========================================================
# KHỞI ĐỘNG
# =========================================================

try:
    ensure_admin()
except Exception as e:
    print("STARTUP ERROR:", e)


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
