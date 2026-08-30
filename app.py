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
    send_from_directory,
    abort,
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)

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
# THƯ MỤC UPLOAD
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

UPLOAD_DIR = os.path.join(
    BASE_DIR,
    "uploads"
)

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


# =========================================================
# FILE ĐƯỢC PHÉP
# =========================================================

ALLOWED_IMAGES = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp"
}

ALLOWED_VIDEOS = {
    "mp4",
    "webm",
    "mov"
}

ALLOWED_FILES = {
    "pdf",
    "doc",
    "docx",
    "ppt",
    "pptx",
    "txt"
}


# =========================================================
# SUPABASE
# =========================================================

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL"
)

SUPABASE_SECRET_KEY = os.environ.get(
    "SUPABASE_SECRET_KEY"
)

if not SUPABASE_URL:
    raise RuntimeError(
        "Thiếu SUPABASE_URL"
    )

if not SUPABASE_SECRET_KEY:
    raise RuntimeError(
        "Thiếu SUPABASE_SECRET_KEY"
    )


supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY
)


# =========================================================
# HÀM KIỂM TRA ĐĂNG NHẬP
# =========================================================

def login_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if "user_id" not in session:
            return redirect(
                url_for("login")
            )

        return view(*args, **kwargs)

    return wrapped


# =========================================================
# HÀM KIỂM TRA ADMIN
# =========================================================

def admin_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if session.get("role") != "admin":
            abort(403)

        return view(*args, **kwargs)

    return wrapped


# =========================================================
# LƯU FILE
# =========================================================

def save_upload(file_obj, allowed_extensions):

    if not file_obj:
        return ""

    if not file_obj.filename:
        return ""

    original_name = file_obj.filename

    if "." not in original_name:
        return ""

    extension = (
        original_name
        .rsplit(".", 1)[-1]
        .lower()
    )

    if extension not in allowed_extensions:
        return ""

    safe_name = secure_filename(
        original_name
    )

    if not safe_name:
        return ""

    unique_name = (
        os.urandom(12).hex()
        + "_"
        + safe_name
    )

    file_path = os.path.join(
        UPLOAD_DIR,
        unique_name
    )

    file_obj.save(file_path)

    return unique_name


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
            .select("*")
            .order(
                "id",
                desc=True
            )
        )

        if q:

            result = query.execute()

            all_posts = result.data or []

            posts = []

            search_text = q.lower()

            for post in all_posts:

                book_title = str(
                    post.get(
                        "book_title",
                        ""
                    )
                ).lower()

                author = str(
                    post.get(
                        "author",
                        ""
                    )
                ).lower()

                impression = str(
                    post.get(
                        "impression",
                        ""
                    )
                ).lower()

                if (
                    search_text in book_title
                    or search_text in author
                    or search_text in impression
                ):

                    posts.append(post)

        else:

            result = query.execute()

            posts = result.data or []

    except Exception as e:

        print(
            "HOME POSTS ERROR:",
            e
        )

        posts = []

    # -----------------------------------------------------
    # LẤY USERS
    # -----------------------------------------------------

    try:

        result = (
            supabase
            .table("users")
            .select(
                "id,username,full_name,role"
            )
            .execute()
        )

        users = result.data or []

    except Exception as e:

        print(
            "HOME USERS ERROR:",
            e
        )

        users = []

    user_map = {
        user["id"]: user
        for user in users
    }

    # -----------------------------------------------------
    # LẤY LIKES
    # -----------------------------------------------------

    try:

        result = (
            supabase
            .table("likes")
            .select(
                "id,post_id,user_id"
            )
            .execute()
        )

        likes = result.data or []

    except Exception as e:

        print(
            "HOME LIKES ERROR:",
            e
        )

        likes = []

    # -----------------------------------------------------
    # LẤY COMMENTS
    # -----------------------------------------------------

    try:

        result = (
            supabase
            .table("comments")
            .select("*")
            .order(
                "id",
                desc=True
            )
            .execute()
        )

        all_comments = result.data or []

    except Exception as e:

        print(
            "HOME COMMENTS ERROR:",
            e
        )

        all_comments = []

    comments = {}

    # -----------------------------------------------------
    # GHÉP DỮ LIỆU
    # -----------------------------------------------------

    for post in posts:

        post_id = post.get(
            "id"
        )

        user = user_map.get(
            post.get("user_id"),
            {}
        )

        post["full_name"] = user.get(
            "full_name",
            "Thành viên"
        )

        post["like_count"] = sum(
            1
            for like in likes
            if like.get("post_id") == post_id
        )

        post_comments = []

        for comment_item in all_comments:

            if comment_item.get(
                "post_id"
            ) == post_id:

                comment_user = user_map.get(
                    comment_item.get(
                        "user_id"
                    ),
                    {}
                )

                comment_item["full_name"] = (
                    comment_user.get(
                        "full_name",
                        "Thành viên"
                    )
                )

                post_comments.append(
                    comment_item
                )

        comments[post_id] = post_comments

        post["comment_count"] = len(
            post_comments
        )

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

            if not users:

                flash(
                    "Sai tài khoản hoặc mật khẩu.",
                    "error"
                )

                return render_template(
                    "login.html"
                )

            user = users[0]

            stored_password = user.get(
                "password",
                ""
            )

            if not check_password_hash(
                stored_password,
                password
            ):

                flash(
                    "Sai tài khoản hoặc mật khẩu.",
                    "error"
                )

                return render_template(
                    "login.html"
                )

            # XÓA SESSION CŨ
            session.clear()

            # TẠO SESSION MỚI
            session["user_id"] = user["id"]

            session["username"] = user.get(
                "username",
                ""
            )

            session["full_name"] = user.get(
                "full_name",
                ""
            )

            session["role"] = user.get(
                "role",
                "member"
            )

            return redirect(
                url_for("home")
            )

        except Exception as e:

            print(
                "LOGIN ERROR:",
                e
            )

            flash(
                "Không thể đăng nhập. Vui lòng kiểm tra hệ thống.",
                "error"
            )

            return render_template(
                "login.html"
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

        book_title = request.form.get(
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

        if not book_title:

            flash(
                "Vui lòng nhập tên sách.",
                "error"
            )

            return render_template(
                "share.html"
            )

        if not impression:

            flash(
                "Vui lòng nhập điều bạn ấn tượng về sách.",
                "error"
            )

            return render_template(
                "share.html"
            )

        try:

            image_name = save_upload(
                request.files.get("image"),
                ALLOWED_IMAGES
            )

            video_name = save_upload(
                request.files.get("video"),
                ALLOWED_VIDEOS
            )

            file_name = save_upload(
                request.files.get("file"),
                ALLOWED_FILES
            )

            supabase.table(
                "posts"
            ).insert({

                "user_id":
                    session["user_id"],

                "book_title":
                    book_title,

                "author":
                    author,

                "impression":
                    impression,

                "image":
                    image_name,

                "video":
                    video_name,

                "file_name":
                    file_name,

                "url":
                    external_url,

            }).execute()

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
                e
            )

            flash(
                "Không thể chia sẻ bài viết.",
                "error"
            )

    return render_template(
        "share.html"
    )


# =========================================================
# LIKE BÀI VIẾT
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
            .eq(
                "post_id",
                post_id
            )
            .eq(
                "user_id",
                session["user_id"]
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

                "post_id":
                    post_id,

                "user_id":
                    session["user_id"]

            }).execute()

    except Exception as e:

        print(
            "LIKE ERROR:",
            e
        )

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

                "post_id":
                    post_id,

                "user_id":
                    session["user_id"],

                "content":
                    content

            }).execute()

        except Exception as e:

            print(
                "COMMENT ERROR:",
                e
            )

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

    # -----------------------------------------------------
    # CẤP TÀI KHOẢN
    # -----------------------------------------------------

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
                "Vui lòng nhập đầy đủ thông tin.",
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

                        "username":
                            username,

                        "password":
                            generate_password_hash(
                                password
                            ),

                        "full_name":
                            full_name,

                        "role":
                            "member"

                    }).execute()

                    flash(
                        "Đã cấp tài khoản thành công.",
                        "success"
                    )

            except Exception as e:

                print(
                    "CREATE ACCOUNT ERROR:",
                    e
                )

                flash(
                    "Không thể tạo tài khoản.",
                    "error"
                )

    # -----------------------------------------------------
    # DANH SÁCH USERS
    # -----------------------------------------------------

    try:

        result = (
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

        users = result.data or []

    except Exception as e:

        print(
            "ADMIN USERS ERROR:",
            e
        )

        users = []

    # -----------------------------------------------------
    # DANH SÁCH POSTS
    # -----------------------------------------------------

    try:

        result = (
            supabase
            .table("posts")
            .select(
                "id,book_title,created_at,user_id"
            )
            .order(
                "id",
                desc=True
            )
            .execute()
        )

        posts = result.data or []

    except Exception as e:

        print(
            "ADMIN POSTS ERROR:",
            e
        )

        posts = []

    # -----------------------------------------------------
    # THỐNG KÊ
    # -----------------------------------------------------

    try:

        result = (
            supabase
            .table("users")
            .select(
                "id",
                count="exact"
            )
            .execute()
        )

        members = result.count or 0

    except Exception:

        members = len(users)

    try:

        result = (
            supabase
            .table("posts")
            .select(
                "id",
                count="exact"
            )
            .execute()
        )

        post_count = result.count or 0

    except Exception:

        post_count = len(posts)

    try:

        result = (
            supabase
            .table("likes")
            .select(
                "id",
                count="exact"
            )
            .execute()
        )

        like_count = result.count or 0

    except Exception:

        like_count = 0

    try:

        result = (
            supabase
            .table("comments")
            .select(
                "id",
                count="exact"
            )
            .execute()
        )

        comment_count = result.count or 0

    except Exception:

        comment_count = 0

    stats = {

        "members":
            members,

        "posts":
            post_count,

        "likes":
            like_count,

        "comments":
            comment_count,

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

        print(
            "DELETE POST ERROR:",
            e
        )

        flash(
            "Không thể xóa bài đăng.",
            "error"
        )

    return redirect(
        url_for("admin")
    )


# =========================================================
# HIỂN THỊ FILE UPLOAD
# =========================================================

@app.route(
    "/uploads/<path:name>"
)
def uploads(name):

    return send_from_directory(
        UPLOAD_DIR,
        name
    )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    try:

        (
            supabase
            .table("users")
            .select("id")
            .limit(1)
            .execute()
        )

        return {
            "service":
                "VanHoaDoc",

            "status":
                "ok",

            "supabase":
                True
        }

    except Exception as e:

        print(
            "HEALTH ERROR:",
            e
        )

        return {
            "service":
                "VanHoaDoc",

            "status":
                "error",

            "supabase":
                False,

            "message":
                str(e)
        }, 500


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
# LỖI 500
# =========================================================

@app.errorhandler(500)
def server_error(_):

    return (
        "Hệ thống đang gặp lỗi. Vui lòng thử lại.",
        500
    )


# =========================================================
# CHẠY SERVER
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
