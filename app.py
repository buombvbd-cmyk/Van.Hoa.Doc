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

from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)

from werkzeug.utils import secure_filename

from supabase import create_client


# =========================================================
# CẤU HÌNH ỨNG DỤNG
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

if not SUPABASE_URL:
    raise RuntimeError("Thiếu SUPABASE_URL")

if not SUPABASE_SECRET_KEY:
    raise RuntimeError("Thiếu SUPABASE_SECRET_KEY")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY
)


# =========================================================
# STORAGE
# =========================================================

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
# HÀM KIỂM TRA FILE
# =========================================================

def allowed_file(filename, allowed_extensions):

    if not filename:
        return False

    if "." not in filename:
        return False

    extension = filename.rsplit(
        ".",
        1
    )[1].lower()

    return extension in allowed_extensions


# =========================================================
# UPLOAD FILE
# =========================================================

def upload_to_supabase(file_obj, allowed_extensions):

    if not file_obj:
        return ""

    if not file_obj.filename:
        return ""

    filename = secure_filename(
        file_obj.filename
    )

    if not allowed_file(
        filename,
        allowed_extensions
    ):
        return ""

    unique_filename = (
        os.urandom(8).hex()
        + "_"
        + filename
    )

    try:

        file_data = file_obj.read()

        content_type = (
            file_obj.content_type
            or "application/octet-stream"
        )

        supabase.storage.from_(
            BUCKET_NAME
        ).upload(
            unique_filename,
            file_data,
            {
                "content-type": content_type
            }
        )

        public_url = (
            f"{SUPABASE_URL}"
            f"/storage/v1/object/public/"
            f"{BUCKET_NAME}/"
            f"{unique_filename}"
        )

        return public_url

    except Exception as error:

        print(
            "UPLOAD ERROR:",
            error
        )

        return ""


# =========================================================
# ĐĂNG NHẬP BẮT BUỘC
# =========================================================

def login_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if "user_id" not in session:

            return redirect(
                url_for("login")
            )

        return view(
            *args,
            **kwargs
        )

    return wrapped


# =========================================================
# ADMIN BẮT BUỘC
# =========================================================

def admin_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if session.get("role") != "admin":

            abort(403)

        return view(
            *args,
            **kwargs
        )

    return wrapped


# =========================================================
# TẠO / CẬP NHẬT ADMIN
# =========================================================

def ensure_admin():

    try:

        result = (
            supabase
            .table("users")
            .select("*")
            .eq(
                "username",
                "admin"
            )
            .limit(1)
            .execute()
        )

        users = result.data or []

        password_hash = generate_password_hash(
            "Admin@123"
        )

        # -------------------------------------------------
        # CHƯA CÓ ADMIN
        # -------------------------------------------------

        if not users:

            supabase.table(
                "users"
            ).insert({

                "username": "admin",

                "password": password_hash,

                "full_name": "Quản trị viên",

                "role": "admin",

            }).execute()

            print(
                "ADMIN: Đã tạo tài khoản admin."
            )

            return

        # -------------------------------------------------
        # ĐÃ CÓ ADMIN
        # -------------------------------------------------

        user = users[0]

        password_valid = False

        try:

            password_valid = check_password_hash(
                user.get("password", ""),
                "Admin@123"
            )

        except Exception:

            password_valid = False

        # -------------------------------------------------
        # CẬP NHẬT ADMIN
        # -------------------------------------------------

        if (
            not password_valid
            or user.get("role") != "admin"
        ):

            supabase.table(
                "users"
            ).update({

                "password": password_hash,

                "full_name": "Quản trị viên",

                "role": "admin",

            }).eq(
                "id",
                user["id"]
            ).execute()

            print(
                "ADMIN: Đã cập nhật tài khoản admin."
            )

        else:

            print(
                "ADMIN: Tài khoản admin đã sẵn sàng."
            )

    except Exception as error:

        print(
            "ADMIN INIT ERROR:",
            error
        )


# =========================================================
# TRANG CHỦ
# =========================================================

@app.route("/")
def home():

    q = request.args.get(
        "q",
        ""
    ).strip()

    posts = []

    # -----------------------------------------------------
    # LẤY BÀI ĐĂNG
    # -----------------------------------------------------

    try:

        result = (
            supabase
            .table("posts")
            .select("*")
            .order(
                "id",
                desc=True
            )
            .execute()
        )

        posts = result.data or []

    except Exception as error:

        print(
            "HOME POSTS ERROR:",
            error
        )

    # -----------------------------------------------------
    # LẤY USERS
    # -----------------------------------------------------

    users = []

    try:

        result = (
            supabase
            .table("users")
            .select(
                "id,full_name"
            )
            .execute()
        )

        users = result.data or []

    except Exception as error:

        print(
            "HOME USERS ERROR:",
            error
        )

    user_map = {
        str(user["id"]): user
        for user in users
    }

    # -----------------------------------------------------
    # TÌM KIẾM
    # -----------------------------------------------------

    if q:

        keyword = q.lower()

        filtered_posts = []

        for post in posts:

            user = user_map.get(
                str(post.get("user_id")),
                {}
            )

            full_name = user.get(
                "full_name",
                ""
            )

            searchable_text = " ".join([
                str(
                    post.get(
                        "book_title",
                        ""
                    )
                ),
                str(
                    post.get(
                        "author",
                        ""
                    )
                ),
                str(
                    post.get(
                        "impression",
                        ""
                    )
                ),
                str(full_name),
            ]).lower()

            if keyword in searchable_text:

                filtered_posts.append(
                    post
                )

        posts = filtered_posts

    # -----------------------------------------------------
    # LIKE
    # -----------------------------------------------------

    likes = []

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

    except Exception as error:

        print(
            "LIKES ERROR:",
            error
        )

    # -----------------------------------------------------
    # COMMENT
    # -----------------------------------------------------

    all_comments = []

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

    except Exception as error:

        print(
            "COMMENTS ERROR:",
            error
        )

    # -----------------------------------------------------
    # CHUẨN BỊ DỮ LIỆU
    # -----------------------------------------------------

    comments = {}

    for post in posts:

        post_id = post["id"]

        post["full_name"] = (
            user_map
            .get(
                str(
                    post.get(
                        "user_id"
                    )
                ),
                {}
            )
            .get(
                "full_name",
                "Thành viên"
            )
        )

        post["like_count"] = sum(
            1
            for like in likes
            if like.get("post_id") == post_id
        )

        post["comment_count"] = sum(
            1
            for comment in all_comments
            if comment.get("post_id") == post_id
        )

        post_comments = []

        for comment in all_comments:

            if comment.get(
                "post_id"
            ) == post_id:

                comment_user = user_map.get(
                    str(
                        comment.get(
                            "user_id"
                        )
                    ),
                    {}
                )

                comment["full_name"] = (
                    comment_user.get(
                        "full_name",
                        "Thành viên"
                    )
                )

                post_comments.append(
                    comment
                )

        comments[post_id] = post_comments

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

            try:

                password_ok = check_password_hash(
                    user.get(
                        "password",
                        ""
                    ),
                    password
                )

            except Exception as error:

                print(
                    "PASSWORD CHECK ERROR:",
                    error
                )

                password_ok = False

            if not password_ok:

                flash(
                    "Sai tài khoản hoặc mật khẩu.",
                    "error"
                )

                return render_template(
                    "login.html"
                )

            # ---------------------------------------------
            # TẠO SESSION
            # ---------------------------------------------

            session.clear()

            session["user_id"] = user["id"]

            session["username"] = (
                user["username"]
            )

            session["full_name"] = (
                user.get(
                    "full_name",
                    "Thành viên"
                )
            )

            session["role"] = (
                user.get(
                    "role",
                    "member"
                )
            )

            flash(
                "Đăng nhập thành công.",
                "success"
            )

            return redirect(
                url_for("home")
            )

        except Exception as error:

            print(
                "LOGIN ERROR:",
                error
            )

            flash(
                "Không thể đăng nhập. Vui lòng thử lại.",
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

        # -------------------------------------------------
        # UPLOAD ẢNH
        # -------------------------------------------------

        image_url = upload_to_supabase(
            request.files.get("image"),
            ALLOWED_IMAGES
        )

        # -------------------------------------------------
        # UPLOAD VIDEO
        # -------------------------------------------------

        video_url = upload_to_supabase(
            request.files.get("video"),
            ALLOWED_VIDEOS
        )

        # -------------------------------------------------
        # UPLOAD FILE
        # -------------------------------------------------

        file_url = upload_to_supabase(
            request.files.get("file"),
            ALLOWED_FILES
        )

        try:

            supabase.table(
                "posts"
            ).insert({

                "user_id":
                    session["user_id"],

                "book_title":
                    title,

                "author":
                    author,

                "impression":
                    impression,

                "image":
                    image_url,

                "video":
                    video_url,

                "file_name":
                    file_url,

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

        except Exception as error:

            print(
                "CREATE POST ERROR:",
                error
            )

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

                "post_id":
                    post_id,

                "user_id":
                    user_id,

            }).execute()

    except Exception as error:

        print(
            "LIKE ERROR:",
            error
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
                    content,

            }).execute()

        except Exception as error:

            print(
                "COMMENT ERROR:",
                error
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
    # TẠO TÀI KHOẢN THÀNH VIÊN
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

                        "username":
                            username,

                        "password":
                            generate_password_hash(
                                password
                            ),

                        "full_name":
                            full_name,

                        "role":
                            "member",

                    }).execute()

                    flash(
                        "Đã cấp tài khoản thành viên.",
                        "success"
                    )

            except Exception as error:

                print(
                    "CREATE USER ERROR:",
                    error
                )

                flash(
                    "Không thể tạo tài khoản.",
                    "error"
                )

    # -----------------------------------------------------
    # USERS
    # -----------------------------------------------------

    users = []

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

    except Exception as error:

        print(
            "ADMIN USERS ERROR:",
            error
        )

    # -----------------------------------------------------
    # POSTS
    # -----------------------------------------------------

    posts = []

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

    except Exception as error:

        print(
            "ADMIN POSTS ERROR:",
            error
        )

    user_map = {
        str(user["id"]): user
        for user in users
    }

    for post in posts:

        user = user_map.get(
            str(
                post.get(
                    "user_id"
                )
            ),
            {}
        )

        post["full_name"] = user.get(
            "full_name",
            "Thành viên"
        )

    # -----------------------------------------------------
    # THỐNG KÊ
    # -----------------------------------------------------

    try:

        members_result = (
            supabase
            .table("users")
            .select(
                "id",
                count="exact"
            )
            .execute()
        )

        members = (
            members_result.count
            or 0
        )

    except Exception:

        members = len(users)

    try:

        posts_result = (
            supabase
            .table("posts")
            .select(
                "id",
                count="exact"
            )
            .execute()
        )

        post_count = (
            posts_result.count
            or 0
        )

    except Exception:

        post_count = len(posts)

    try:

        likes_result = (
            supabase
            .table("likes")
            .select(
                "id",
                count="exact"
            )
            .execute()
        )

        like_count = (
            likes_result.count
            or 0
        )

    except Exception:

        like_count = 0

    try:

        comments_result = (
            supabase
            .table("comments")
            .select(
                "id",
                count="exact"
            )
            .execute()
        )

        comment_count = (
            comments_result.count
            or 0
        )

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

    except Exception as error:

        print(
            "DELETE POST ERROR:",
            error
        )

        flash(
            "Không thể xóa bài đăng.",
            "error"
        )

    return redirect(
        url_for("admin")
    )


# =========================================================
# KIỂM TRA QUYỀN TRUY CẬP
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
                True,

        }

    except Exception as error:

        return {

            "service":
                "VanHoaDoc",

            "status":
                "error",

            "supabase":
                False,

            "message":
                str(error),

        }, 500


# =========================================================
# KHỞI ĐỘNG
# =========================================================

try:

    ensure_admin()

except Exception as error:

    print(
        "STARTUP ERROR:",
        error
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
