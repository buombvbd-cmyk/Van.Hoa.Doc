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
    send_from_directory,
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


# =========================================================
# SUPABASE
# =========================================================

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


# =========================================================
# FILE CHO PHÉP
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
# KIỂM TRA FILE
# =========================================================

def allowed_file(filename, allowed):
    if not filename or "." not in filename:
        return False

    ext = filename.rsplit(".", 1)[-1].lower()

    return ext in allowed


# =========================================================
# UPLOAD FILE LÊN SUPABASE
# =========================================================

def save_upload(file_obj, allowed):
    if not file_obj:
        return ""

    if not file_obj.filename:
        return ""

    if not allowed_file(file_obj.filename, allowed):
        return ""

    original_name = secure_filename(file_obj.filename)

    ext = ""
    if "." in original_name:
        ext = original_name.rsplit(".", 1)[-1].lower()

    unique_name = (
        os.urandom(12).hex()
        + "."
        + ext
    )

    try:
        file_data = file_obj.read()

        content_type = (
            file_obj.content_type
            or "application/octet-stream"
        )

        supabase.storage.from_(BUCKET_NAME).upload(
            unique_name,
            file_data,
            {
                "content-type": content_type,
                "upsert": "false",
            },
        )

        return unique_name

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return ""


# =========================================================
# LẤY URL FILE TỪ SUPABASE
# =========================================================

def get_storage_url(filename):
    if not filename:
        return ""

    try:
        return supabase.storage.from_(
            BUCKET_NAME
        ).get_public_url(filename)

    except Exception as e:
        print("STORAGE URL ERROR:", e)
        return ""


# =========================================================
# LOGIN
# =========================================================

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):

        if "user_id" not in session:
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped


# =========================================================
# ADMIN
# =========================================================

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):

        if session.get("role") != "admin":
            abort(403)

        return view(*args, **kwargs)

    return wrapped


# =========================================================
# TRANG CHỦ
# =========================================================

@app.route("/")
def home():

    q = request.args.get("q", "").strip()

    try:

        # ---------------------------------------------
        # LẤY BÀI VIẾT
        # ---------------------------------------------

        query = (
            supabase
            .table("posts")
            .select("*")
            .order("id", desc=True)
        )

        if q:
            # Tìm theo tên sách
            result = (
                supabase
                .table("posts")
                .select("*")
                .ilike("book_title", f"%{q}%")
                .order("id", desc=True)
                .execute()
            )
        else:
            result = query.execute()

        posts = result.data or []


        # ---------------------------------------------
        # LẤY USERS
        # ---------------------------------------------

        users_result = (
            supabase
            .table("users")
            .select("id, username, full_name, role")
            .execute()
        )

        users = users_result.data or []

        users_map = {
            user["id"]: user
            for user in users
        }


        # ---------------------------------------------
        # LẤY LIKES
        # ---------------------------------------------

        likes_result = (
            supabase
            .table("likes")
            .select("id, post_id, user_id")
            .execute()
        )

        likes = likes_result.data or []


        # ---------------------------------------------
        # ĐẾM LIKE
        # ---------------------------------------------

        like_counts = {}

        for like in likes:

            post_id = like["post_id"]

            like_counts[post_id] = (
                like_counts.get(post_id, 0) + 1
            )


        # ---------------------------------------------
        # LẤY COMMENTS
        # ---------------------------------------------

        comments_result = (
            supabase
            .table("comments")
            .select("*")
            .order("id", desc=True)
            .execute()
        )

        all_comments = comments_result.data or []


        # ---------------------------------------------
        # GẮN THÔNG TIN CHO BÀI
        # ---------------------------------------------

        comments = {}

        for post in posts:

            post_id = post["id"]

            post_user = users_map.get(
                post.get("user_id")
            )

            post["full_name"] = (
                post_user["full_name"]
                if post_user
                else "Thành viên"
            )

            post["like_count"] = like_counts.get(
                post_id,
                0
            )

            post["comment_count"] = 0

            comments[post_id] = []


        # ---------------------------------------------
        # GẮN COMMENT
        # ---------------------------------------------

        for comment in all_comments:

            post_id = comment["post_id"]

            if post_id not in comments:
                comments[post_id] = []

            comment_user = users_map.get(
                comment.get("user_id")
            )

            comment["full_name"] = (
                comment_user["full_name"]
                if comment_user
                else "Thành viên"
            )

            comments[post_id].append(comment)

        # Đếm comment
        for post in posts:

            post["comment_count"] = len(
                comments.get(post["id"], [])
            )

        return render_template(
            "home.html",
            posts=posts,
            comments=comments,
            q=q,
            get_storage_url=get_storage_url,
        )

    except Exception as e:

        print("HOME ERROR:", repr(e))

        return (
            "Lỗi trang chủ: " + str(e),
            500
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

        username = (
            request.form
            .get("username", "")
            .strip()
        )

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
                .eq("username", username)
                .limit(1)
                .execute()
            )

            users = result.data or []

            user = (
                users[0]
                if users
                else None
            )

            if user and check_password_hash(
                user["password"],
                password
            ):

                session["user_id"] = user["id"]

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

        except Exception as e:

            print(
                "LOGIN ERROR:",
                repr(e)
            )

            flash(
                "Không thể kết nối cơ sở dữ liệu.",
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

        title = (
            request.form
            .get("book_title", "")
            .strip()
        )

        author = (
            request.form
            .get("author", "")
            .strip()
        )

        impression = (
            request.form
            .get("impression", "")
            .strip()
        )

        external_url = (
            request.form
            .get("url", "")
            .strip()
        )

        if not title or not impression:

            flash(
                "Vui lòng nhập tên sách và điều bạn ấn tượng.",
                "error"
            )

            return render_template(
                "share.html"
            )


        # ---------------------------------------------
        # UPLOAD ẢNH
        # ---------------------------------------------

        image = save_upload(
            request.files.get("image"),
            ALLOWED_IMAGES
        )


        # ---------------------------------------------
        # UPLOAD VIDEO
        # ---------------------------------------------

        video = save_upload(
            request.files.get("video"),
            ALLOWED_VIDEOS
        )


        # ---------------------------------------------
        # UPLOAD FILE
        # ---------------------------------------------

        file_name = save_upload(
            request.files.get("file"),
            ALLOWED_FILES
        )


        try:

            supabase.table("posts").insert(
                {
                    "user_id": session["user_id"],
                    "book_title": title,
                    "author": author,
                    "impression": impression,
                    "image": image,
                    "video": video,
                    "file_name": file_name,
                    "url": external_url,
                }
            ).execute()

            flash(
                "Đã chia sẻ trang sách thành công.",
                "success"
            )

            return redirect(
                url_for("home")
            )

        except Exception as e:

            print(
                "SHARE ERROR:",
                repr(e)
            )

            flash(
                "Không thể lưu bài viết.",
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

    try:

        result = (
            supabase
            .table("likes")
            .select("id")
            .eq("post_id", post_id)
            .eq("user_id", session["user_id"])
            .limit(1)
            .execute()
        )

        existing = result.data or []

        if existing:

            supabase.table("likes").delete().eq(
                "id",
                existing[0]["id"]
            ).execute()

        else:

            supabase.table("likes").insert(
                {
                    "post_id": post_id,
                    "user_id": session["user_id"],
                }
            ).execute()

    except Exception as e:

        print(
            "LIKE ERROR:",
            repr(e)
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

    content = (
        request.form
        .get("content", "")
        .strip()
    )

    if content:

        try:

            supabase.table("comments").insert(
                {
                    "post_id": post_id,
                    "user_id": session["user_id"],
                    "content": content,
                }
            ).execute()

        except Exception as e:

            print(
                "COMMENT ERROR:",
                repr(e)
            )

    return redirect(
        request.referrer
        or url_for("home")
    )


# =========================================================
# TRANG QUẢN TRỊ
# =========================================================

@app.route(
    "/admin",
    methods=["GET", "POST"]
)
@login_required
@admin_required
def admin():

    try:

        # ---------------------------------------------
        # TẠO TÀI KHOẢN
        # ---------------------------------------------

        if request.method == "POST":

            full_name = (
                request.form
                .get("full_name", "")
                .strip()
            )

            username = (
                request.form
                .get("username", "")
                .strip()
            )

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

                    supabase.table("users").insert(
                        {
                            "username": username,
                            "password": generate_password_hash(
                                password
                            ),
                            "full_name": full_name,
                            "role": "member",
                        }
                    ).execute()

                    flash(
                        "Đã cấp tài khoản thành viên.",
                        "success"
                    )

                except Exception as e:

                    print(
                        "CREATE USER ERROR:",
                        repr(e)
                    )

                    flash(
                        "Tên tài khoản có thể đã tồn tại.",
                        "error"
                    )


        # ---------------------------------------------
        # USERS
        # ---------------------------------------------

        users_result = (
            supabase
            .table("users")
            .select(
                "id,full_name,username,role"
            )
            .order("id", desc=True)
            .execute()
        )

        users = users_result.data or []


        # ---------------------------------------------
        # POSTS
        # ---------------------------------------------

        posts_result = (
            supabase
            .table("posts")
            .select(
                "id,book_title,created_at,user_id"
            )
            .order("id", desc=True)
            .execute()
        )

        posts = posts_result.data or []


        users_map = {
            user["id"]: user
            for user in users
        }

        for post in posts:

            user = users_map.get(
                post.get("user_id")
            )

            post["full_name"] = (
                user["full_name"]
                if user
                else "Thành viên"
            )


        # ---------------------------------------------
        # THỐNG KÊ
        # ---------------------------------------------

        members_result = (
            supabase
            .table("users")
            .select("id", count="exact")
            .execute()
        )

        posts_count_result = (
            supabase
            .table("posts")
            .select("id", count="exact")
            .execute()
        )

        likes_count_result = (
            supabase
            .table("likes")
            .select("id", count="exact")
            .execute()
        )

        comments_count_result = (
            supabase
            .table("comments")
            .select("id", count="exact")
            .execute()
        )


        stats = {

            "members":
                members_result.count or 0,

            "posts":
                posts_count_result.count or 0,

            "likes":
                likes_count_result.count or 0,

            "comments":
                comments_count_result.count or 0,
        }


        return render_template(
            "admin.html",
            users=users,
            posts=posts,
            stats=stats,
        )

    except Exception as e:

        print(
            "ADMIN ERROR:",
            repr(e)
        )

        return (
            "Lỗi trang quản trị: "
            + str(e),
            500
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

        # Lấy bài để biết file cần xóa
        result = (
            supabase
            .table("posts")
            .select(
                "image,video,file_name"
            )
            .eq("id", post_id)
            .limit(1)
            .execute()
        )

        posts = result.data or []

        if posts:

            post = posts[0]

            files_to_delete = []

            if post.get("image"):
                files_to_delete.append(
                    post["image"]
                )

            if post.get("video"):
                files_to_delete.append(
                    post["video"]
                )

            if post.get("file_name"):
                files_to_delete.append(
                    post["file_name"]
                )

            if files_to_delete:

                try:

                    supabase.storage.from_(
                        BUCKET_NAME
                    ).remove(files_to_delete)

                except Exception as e:

                    print(
                        "DELETE FILE ERROR:",
                        repr(e)
                    )


        # Xóa bài
        supabase.table("posts").delete().eq(
            "id",
            post_id
        ).execute()

        flash(
            "Đã xóa bài đăng.",
            "success"
        )

    except Exception as e:

        print(
            "DELETE POST ERROR:",
            repr(e)
        )

        flash(
            "Không thể xóa bài đăng.",
            "error"
        )

    return redirect(
        url_for("admin")
    )


# =========================================================
# ROUTE UPLOADS
# =========================================================
# Đây chính là phần sửa lỗi:
# "Could not build url for endpoint 'uploads'"
# =========================================================

@app.route(
    "/uploads/<path:name>"
)
def uploads(name):

    try:

        public_url = get_storage_url(name)

        if public_url:

            return redirect(public_url)

        abort(404)

    except Exception as e:

        print(
            "UPLOAD URL ERROR:",
            repr(e)
        )

        abort(404)


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
# LỖI 404
# =========================================================

@app.errorhandler(404)
def not_found(_):

    return (
        "Không tìm thấy trang.",
        404
    )


# =========================================================
# CHẠY APP
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
