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
# UPLOAD
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)

ALLOWED_IMAGES = {
    "png", "jpg", "jpeg", "gif", "webp"
}

ALLOWED_VIDEOS = {
    "mp4", "webm", "mov"
}

ALLOWED_FILES = {
    "pdf", "doc", "docx", "ppt", "pptx", "txt"
}


def allowed_file(filename, extensions):

    if not filename:
        return False

    if "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()

    return extension in extensions


def save_upload(file_obj, extensions):

    if not file_obj:
        return ""

    if not file_obj.filename:
        return ""

    if not allowed_file(file_obj.filename, extensions):
        return ""

    filename = secure_filename(file_obj.filename)

    if not filename:
        return ""

    unique_name = (
        os.urandom(12).hex()
        + "_"
        + filename
    )

    path = os.path.join(
        UPLOAD_DIR,
        unique_name
    )

    try:

        file_obj.save(path)

        return unique_name

    except Exception as error:

        print("UPLOAD ERROR:", error)

        return ""


# =========================================================
# LOGIN REQUIRED
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
# TRANG CHỦ
# =========================================================

@app.route("/")
def home():

    q = request.args.get("q", "").strip()

    # -----------------------------------------------------
    # CHỈ LẤY BÀI ĐÃ DUYỆT
    # -----------------------------------------------------

    try:

        result = (
            supabase
            .table("posts")
            .select("*")
            .eq("status", "approved")
            .order("id", desc=True)
            .execute()
        )

        posts = result.data or []

    except Exception as error:

        print("HOME POSTS ERROR:", error)

        posts = []

    # -----------------------------------------------------
    # USERS
    # -----------------------------------------------------

    try:

        result = (
            supabase
            .table("users")
            .select(
                "id,username,full_name,role,"
                "user_type,grade,class_name,status"
            )
            .execute()
        )

        users = result.data or []

    except Exception as error:

        print("HOME USERS ERROR:", error)

        users = []

    user_map = {
        user["id"]: user
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
                post.get("user_id"),
                {}
            )

            searchable_text = " ".join([
                str(post.get("book_title", "")),
                str(post.get("author", "")),
                str(post.get("impression", "")),
                str(user.get("full_name", "")),
            ]).lower()

            if keyword in searchable_text:
                filtered_posts.append(post)

        posts = filtered_posts

    # -----------------------------------------------------
    # LIKES
    # -----------------------------------------------------

    try:

        result = (
            supabase
            .table("likes")
            .select("id,post_id,user_id")
            .execute()
        )

        likes = result.data or []

    except Exception as error:

        print("HOME LIKES ERROR:", error)

        likes = []

    # -----------------------------------------------------
    # COMMENTS
    # -----------------------------------------------------

    try:

        result = (
            supabase
            .table("comments")
            .select("*")
            .order("id", desc=True)
            .execute()
        )

        all_comments = result.data or []

    except Exception as error:

        print("HOME COMMENTS ERROR:", error)

        all_comments = []

    # -----------------------------------------------------
    # GHÉP DỮ LIỆU
    # -----------------------------------------------------

    comments = {}

    for post in posts:

        post_id = post.get("id")

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

            if comment_item.get("post_id") == post_id:

                comment_user = user_map.get(
                    comment_item.get("user_id"),
                    {}
                )

                comment_item["full_name"] = (
                    comment_user.get(
                        "full_name",
                        "Thành viên"
                    )
                )

                post_comments.append(comment_item)

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

            return render_template("login.html")

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

            if not users:

                flash(
                    "Sai tài khoản hoặc mật khẩu.",
                    "error"
                )

                return render_template("login.html")

            user = users[0]

            # ---------------------------------------------
            # KIỂM TRA TÀI KHOẢN KHÓA
            # ---------------------------------------------

            if user.get("status") == "locked":

                flash(
                    "Tài khoản đã bị khóa.",
                    "error"
                )

                return render_template("login.html")

            # ---------------------------------------------
            # KIỂM TRA MẬT KHẨU
            # ---------------------------------------------

            try:

                password_ok = check_password_hash(
                    user.get("password", ""),
                    password
                )

            except Exception:

                password_ok = False

            if not password_ok:

                flash(
                    "Sai tài khoản hoặc mật khẩu.",
                    "error"
                )

                return render_template("login.html")

            # ---------------------------------------------
            # SESSION
            # ---------------------------------------------

            session.clear()

            session["user_id"] = user["id"]
            session["username"] = user.get("username", "")
            session["full_name"] = user.get("full_name", "")
            session["role"] = user.get("role", "member")
            session["user_type"] = user.get("user_type", "student")
            session["grade"] = user.get("grade", "")
            session["class_name"] = user.get("class_name", "")

            return redirect(
                url_for("home")
            )

        except Exception as error:

            print("LOGIN ERROR:", error)

            flash(
                "Không thể đăng nhập.",
                "error"
            )

    return render_template("login.html")


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
# CHIA SẺ BÀI
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

            return render_template("share.html")

        if not impression:

            flash(
                "Vui lòng nhập điều bạn ấn tượng.",
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

            supabase.table(
                "posts"
            ).insert({

                "user_id": session["user_id"],
                "book_title": book_title,
                "author": author,
                "impression": impression,
                "image": image,
                "video": video,
                "file_name": file_name,
                "url": external_url,
                "status": "pending",

            }).execute()

            flash(
                "Bài đã được gửi và đang chờ quản trị viên duyệt.",
                "success"
            )

            return redirect(
                url_for("home")
            )

        except Exception as error:

            print("SHARE ERROR:", error)

            flash(
                "Không thể chia sẻ bài viết.",
                "error"
            )

    return render_template("share.html")


# =========================================================
# LIKE
# =========================================================

@app.post("/post/<int:post_id>/like")
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
                "user_id": session["user_id"]
            }).execute()

    except Exception as error:

        print("LIKE ERROR:", error)

    return redirect(
        request.referrer
        or url_for("home")
    )


# =========================================================
# BÌNH LUẬN
# =========================================================

@app.post("/post/<int:post_id>/comment")
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
                "content": content
            }).execute()

        except Exception as error:

            print("COMMENT ERROR:", error)

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

        if not full_name or not username or not password:

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
                    .eq("username", username)
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
                        "user_type": user_type,
                        "grade": grade,
                        "class_name": class_name,
                        "status": "active"

                    }).execute()

                    flash(
                        "Đã cấp tài khoản thành công.",
                        "success"
                    )

            except Exception as error:

                print("CREATE USER ERROR:", error)

                flash(
                    "Không thể tạo tài khoản.",
                    "error"
                )

    # -----------------------------------------------------
    # DANH SÁCH USER
    # -----------------------------------------------------

    try:

        result = (
            supabase
            .table("users")
            .select(
                "id,full_name,username,role,"
                "user_type,grade,class_name,status"
            )
            .order("id", desc=True)
            .execute()
        )

        users = result.data or []

    except Exception as error:

        print("ADMIN USERS ERROR:", error)

        users = []

    # -----------------------------------------------------
    # DANH SÁCH POSTS
    # -----------------------------------------------------
    # ĐÃ SỬA: THÊM impression
    # -----------------------------------------------------

    try:

        result = (
            supabase
            .table("posts")
            .select(
                "id,book_title,created_at,"
                "user_id,status,author,impression"
            )
            .order("id", desc=True)
            .execute()
        )

        posts = result.data or []

    except Exception as error:

        print("ADMIN POSTS ERROR:", error)

        posts = []

    # -----------------------------------------------------
    # GÁN TÊN NGƯỜI ĐĂNG
    # -----------------------------------------------------

    user_map = {
        user["id"]: user
        for user in users
    }

    for post in posts:

        user = user_map.get(
            post.get("user_id"),
            {}
        )

        post["full_name"] = user.get(
            "full_name",
            "Thành viên"
        )

    # =====================================================
    # DANH SÁCH BÌNH LUẬN
    # =====================================================

    try:

        result = (
            supabase
            .table("comments")
            .select(
                "id,post_id,user_id,content,created_at"
            )
            .order("id", desc=True)
            .execute()
        )

        comments = result.data or []

    except Exception as error:

        print("ADMIN COMMENTS ERROR:", error)

        comments = []

    # -----------------------------------------------------
    # GÁN NGƯỜI BÌNH LUẬN + BÀI VIẾT
    # -----------------------------------------------------

    post_map = {
        post["id"]: post
        for post in posts
    }

    for comment_item in comments:

        comment_user = user_map.get(
            comment_item.get("user_id"),
            {}
        )

        comment_post = post_map.get(
            comment_item.get("post_id"),
            {}
        )

        comment_item["full_name"] = (
            comment_user.get(
                "full_name",
                "Thành viên"
            )
        )

        comment_item["book_title"] = (
            comment_post.get(
                "book_title",
                "Bài viết không tồn tại"
            )
        )

    # -----------------------------------------------------
    # THỐNG KÊ THÀNH VIÊN
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

    # -----------------------------------------------------
    # THỐNG KÊ BÀI VIẾT
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # THỐNG KÊ LIKE
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # THỐNG KÊ BÌNH LUẬN
    # -----------------------------------------------------

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

        comment_count = len(comments)

    # -----------------------------------------------------
    # BÀI CHỜ DUYỆT
    # -----------------------------------------------------

    pending_posts = [
        post
        for post in posts
        if post.get("status") == "pending"
    ]

    # -----------------------------------------------------
    # STATS
    # -----------------------------------------------------

    stats = {
        "members": members,
        "posts": post_count,
        "likes": like_count,
        "comments": comment_count,
        "pending": len(pending_posts),
    }

    return render_template(
        "admin.html",
        users=users,
        posts=posts,
        pending_posts=pending_posts,
        comments=comments,
        stats=stats
    )


# =========================================================
# KHÓA / MỞ TÀI KHOẢN
# =========================================================

@app.post("/admin/user/<int:user_id>/toggle")
@login_required
@admin_required
def toggle_user(user_id):

    if user_id == session.get("user_id"):

        flash(
            "Không thể khóa tài khoản đang đăng nhập.",
            "error"
        )

        return redirect(url_for("admin"))

    try:

        result = (
            supabase
            .table("users")
            .select("id,status,role")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )

        users = result.data or []

        if not users:

            flash(
                "Không tìm thấy tài khoản.",
                "error"
            )

            return redirect(url_for("admin"))

        user = users[0]

        if user.get("role") == "admin":

            flash(
                "Không thể khóa tài khoản quản trị.",
                "error"
            )

            return redirect(url_for("admin"))

        current_status = user.get(
            "status",
            "active"
        )

        if current_status == "locked":
            new_status = "active"
        else:
            new_status = "locked"

        supabase.table(
            "users"
        ).update({
            "status": new_status
        }).eq(
            "id",
            user_id
        ).execute()

        flash(
            "Đã cập nhật trạng thái tài khoản.",
            "success"
        )

    except Exception as error:

        print("TOGGLE USER ERROR:", error)

        flash(
            "Không thể cập nhật tài khoản.",
            "error"
        )

    return redirect(url_for("admin"))


# =========================================================
# XÓA TÀI KHOẢN
# =========================================================

@app.post("/admin/user/<int:user_id>/delete")
@login_required
@admin_required
def delete_user(user_id):

    if user_id == session.get("user_id"):

        flash(
            "Không thể xóa tài khoản đang đăng nhập.",
            "error"
        )

        return redirect(url_for("admin"))

    try:

        result = (
            supabase
            .table("users")
            .select("role")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )

        users = result.data or []

        if users and users[0].get("role") == "admin":

            flash(
                "Không thể xóa tài khoản quản trị.",
                "error"
            )

        else:

            supabase.table(
                "users"
            ).delete().eq(
                "id",
                user_id
            ).execute()

            flash(
                "Đã xóa tài khoản.",
                "success"
            )

    except Exception as error:

        print("DELETE USER ERROR:", error)

        flash(
            "Không thể xóa tài khoản.",
            "error"
        )

    return redirect(url_for("admin"))


# =========================================================
# DUYỆT BÀI
# =========================================================

@app.post("/admin/post/<int:post_id>/approve")
@login_required
@admin_required
def approve_post(post_id):

    try:

        supabase.table(
            "posts"
        ).update({
            "status": "approved"
        }).eq(
            "id",
            post_id
        ).execute()

        flash(
            "Đã duyệt bài viết.",
            "success"
        )

    except Exception as error:

        print("APPROVE ERROR:", error)

        flash(
            "Không thể duyệt bài.",
            "error"
        )

    return redirect(url_for("admin"))


# =========================================================
# TỪ CHỐI BÀI
# =========================================================

@app.post("/admin/post/<int:post_id>/reject")
@login_required
@admin_required
def reject_post(post_id):

    try:

        supabase.table(
            "posts"
        ).update({
            "status": "rejected"
        }).eq(
            "id",
            post_id
        ).execute()

        flash(
            "Đã từ chối bài viết.",
            "success"
        )

    except Exception as error:

        print("REJECT ERROR:", error)

        flash(
            "Không thể từ chối bài.",
            "error"
        )

    return redirect(url_for("admin"))


# =========================================================
# XÓA BÀI
# =========================================================

@app.post("/admin/post/<int:post_id>/delete")
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

        print("DELETE POST ERROR:", error)

        flash(
            "Không thể xóa bài đăng.",
            "error"
        )

    return redirect(url_for("admin"))


# =========================================================
# XÓA BÌNH LUẬN - ADMIN
# =========================================================

@app.post("/admin/comment/<int:comment_id>/delete")
@login_required
@admin_required
def delete_comment(comment_id):

    try:

        result = (
            supabase
            .table("comments")
            .select("id")
            .eq("id", comment_id)
            .limit(1)
            .execute()
        )

        comments = result.data or []

        if not comments:

            flash(
                "Không tìm thấy bình luận.",
                "error"
            )

            return redirect(url_for("admin"))

        supabase.table(
            "comments"
        ).delete().eq(
            "id",
            comment_id
        ).execute()

        flash(
            "Đã xóa bình luận.",
            "success"
        )

    except Exception as error:

        print("DELETE COMMENT ERROR:", error)

        flash(
            "Không thể xóa bình luận.",
            "error"
        )

    return redirect(url_for("admin"))


# =========================================================
# HIỂN THỊ FILE UPLOAD
# =========================================================

@app.route("/uploads/<path:name>")
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
            "status": "ok",
            "supabase": True
        }

    except Exception as error:

        return {
            "status": "error",
            "supabase": False,
            "message": str(error)
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
# CHẠY
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
