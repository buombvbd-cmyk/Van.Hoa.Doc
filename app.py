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


# =========================================================
# ĐĂNG NHẬP BẮT BUỘC
# =========================================================

def login_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if "user_id" not in session:
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped


# =========================================================
# ADMIN BẮT BUỘC
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

    try:

        posts_result = (
            supabase
            .table("posts")
            .select("*")
            .order("id", desc=True)
            .execute()
        )

        posts = posts_result.data or []

    except Exception as e:

        print("HOME ERROR:", e)
        posts = []

    try:

        users_result = (
            supabase
            .table("users")
            .select(
                "id,username,full_name,user_type,grade,class_name"
            )
            .execute()
        )

        users = users_result.data or []

    except Exception as e:

        print("USERS ERROR:", e)
        users = []

    user_map = {
        user["id"]: user
        for user in users
    }

    try:

        likes_result = (
            supabase
            .table("likes")
            .select("id,post_id,user_id")
            .execute()
        )

        likes = likes_result.data or []

    except Exception:

        likes = []

    try:

        comments_result = (
            supabase
            .table("comments")
            .select("*")
            .order("id", desc=True)
            .execute()
        )

        all_comments = comments_result.data or []

    except Exception:

        all_comments = []

    comments = {}

    for post in posts:

        post_id = post["id"]

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

        for comment in all_comments:

            if comment.get("post_id") == post_id:

                comment_user = user_map.get(
                    comment.get("user_id"),
                    {}
                )

                comment["full_name"] = comment_user.get(
                    "full_name",
                    "Thành viên"
                )

                post_comments.append(comment)

        comments[post_id] = post_comments

        post["comment_count"] = len(
            post_comments
        )

    return render_template(
        "home.html",
        posts=posts,
        comments=comments,
        q="",
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

            if user.get("status") == "locked":

                flash(
                    "Tài khoản đã bị khóa.",
                    "error"
                )

                return render_template(
                    "login.html"
                )

            if not check_password_hash(
                user.get("password", ""),
                password
            ):

                flash(
                    "Sai tài khoản hoặc mật khẩu.",
                    "error"
                )

                return render_template(
                    "login.html"
                )

            session.clear()

            session["user_id"] = user["id"]

            session["username"] = user["username"]

            session["full_name"] = user.get(
                "full_name",
                ""
            )

            session["role"] = user.get(
                "role",
                "member"
            )

            session["user_type"] = user.get(
                "user_type",
                "student"
            )

            session["grade"] = user.get(
                "grade",
                ""
            )

            session["class_name"] = user.get(
                "class_name",
                ""
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
                "Không thể đăng nhập.",
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
# QUẢN TRỊ - CẤP TÀI KHOẢN
# =========================================================

@app.route(
    "/admin",
    methods=["GET", "POST"]
)
@login_required
@admin_required
def admin():

    # -----------------------------------------------------
    # TẠO TÀI KHOẢN
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

        user_type = request.form.get(
            "user_type",
            "student"
        ).strip()

        grade = request.form.get(
            "grade",
            ""
        ).strip()

        class_name = request.form.get(
            "class_name",
            ""
        ).strip()

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
                            "member",

                        "user_type":
                            user_type,

                        "grade":
                            grade,

                        "class_name":
                            class_name,

                        "status":
                            "active",

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
    # DANH SÁCH TÀI KHOẢN
    # -----------------------------------------------------

    try:

        result = (
            supabase
            .table("users")
            .select(
                "id,full_name,username,role,user_type,"
                "grade,class_name,status"
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
    # DANH SÁCH BÀI
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

    except Exception:

        posts = []

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
            members_result.count or 0
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
            posts_result.count or 0
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
            likes_result.count or 0
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
            comments_result.count or 0
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
        stats=stats,
    )


# =========================================================
# KHÓA TÀI KHOẢN
# =========================================================

@app.post(
    "/admin/user/<int:user_id>/toggle"
)
@login_required
@admin_required
def toggle_user(user_id):

    if user_id == session.get("user_id"):

        flash(
            "Không thể khóa tài khoản admin đang đăng nhập.",
            "error"
        )

        return redirect(
            url_for("admin")
        )

    try:

        result = (
            supabase
            .table("users")
            .select("status")
            .eq(
                "id",
                user_id
            )
            .limit(1)
            .execute()
        )

        users = result.data or []

        if users:

            current_status = users[0].get(
                "status",
                "active"
            )

            new_status = (
                "locked"
                if current_status == "active"
                else "active"
            )

            supabase.table(
                "users"
            ).update({

                "status":
                    new_status

            }).eq(
                "id",
                user_id
            ).execute()

            flash(
                "Đã cập nhật trạng thái tài khoản.",
                "success"
            )

    except Exception as e:

        print(
            "TOGGLE USER ERROR:",
            e
        )

        flash(
            "Không thể cập nhật tài khoản.",
            "error"
        )

    return redirect(
        url_for("admin")
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
            "Không thể xóa bài.",
            "error"
        )

    return redirect(
        url_for("admin")
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
                    session["user_id"],

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
                    content,

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
            "status": "ok",
            "supabase": True
        }

    except Exception as e:

        return {
            "status": "error",
            "supabase": False,
            "message": str(e)
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
