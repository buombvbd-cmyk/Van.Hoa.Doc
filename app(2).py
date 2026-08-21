import os, sqlite3
from functools import wraps
from flask import Flask, request, redirect, url_for, session, flash, render_template_string, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
DB = "database.db"
UPLOAD = "uploads"
os.makedirs(UPLOAD, exist_ok=True)

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    c = db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
      password TEXT NOT NULL, full_name TEXT NOT NULL, role TEXT DEFAULT 'member'
    );
    CREATE TABLE IF NOT EXISTS posts(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
      book_title TEXT NOT NULL, author TEXT, impression TEXT NOT NULL,
      image TEXT, video TEXT, file TEXT, url TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS likes(
      id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, user_id INTEGER,
      UNIQUE(post_id,user_id)
    );
    CREATE TABLE IF NOT EXISTS comments(
      id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, user_id INTEGER,
      content TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    if not c.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
        c.execute("INSERT INTO users(username,password,full_name,role) VALUES(?,?,?,?)",
                  ("admin", generate_password_hash("Admin@123"), "Quản trị viên", "admin"))
    c.commit(); c.close()

def login_required(f):
    @wraps(f)
    def w(*a,**k):
        if "uid" not in session: return redirect(url_for("login"))
        return f(*a,**k)
    return w

def admin_required(f):
    @wraps(f)
    def w(*a,**k):
        if session.get("role") != "admin": abort(403)
        return f(*a,**k)
    return w

def save(f, allowed):
    if not f or not f.filename: return ""
    ext = f.filename.rsplit(".",1)[-1].lower()
    if ext not in allowed: return ""
    name = secure_filename(os.urandom(8).hex()+"."+ext)
    f.save(os.path.join(UPLOAD,name))
    return name

BASE = """
<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{title}}</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;background:#f4f8f3;color:#173c22}
nav{height:68px;background:#fff;border-bottom:1px solid #dce8dc;display:flex;align-items:center;justify-content:space-between;padding:0 5%;position:sticky;top:0;z-index:20}
nav a{margin-left:18px;text-decoration:none;color:#23452b;font-size:14px}.brand{font-weight:800;font-size:18px;color:#206b35}
main{max-width:1100px;margin:auto;padding:28px 18px 70px}
.hero{background:linear-gradient(120deg,#e8f5e7,#fff);border-radius:28px;padding:55px;min-height:300px;display:flex;justify-content:space-between;align-items:center}
h1{font-size:46px;margin:10px 0;color:#173c22}h1 em{color:#3c9951;font-style:normal}
.btn{display:inline-block;padding:12px 18px;border-radius:12px;background:#287a3e;color:#fff;text-decoration:none;border:0;font-weight:700;cursor:pointer}
.feedhead{display:flex;justify-content:space-between;align-items:end;margin:35px 0 12px}
.feed{height:calc(100vh - 180px);min-height:560px;overflow-y:auto;scroll-snap-type:y mandatory;scroll-behavior:smooth;border-radius:22px}
.card{height:calc(100vh - 190px);min-height:540px;scroll-snap-align:start;position:relative;background:#101510;color:#fff;margin-bottom:14px;border-radius:22px;overflow:hidden}
.card img,.card video{width:100%;height:100%;object-fit:contain;background:#101510}
.overlay{position:absolute;inset:auto 0 0;padding:28px 120px 28px 25px;background:linear-gradient(transparent,rgba(0,0,0,.9));min-height:40%}
.overlay h2{margin:5px 0;font-size:25px}.overlay p{margin:8px 0;color:#f2f6f2}
.actions{position:absolute;right:22px;bottom:85px;display:flex;flex-direction:column;gap:12px}
.action{width:58px;height:58px;border:0;border-radius:50%;background:#fff;color:#222;font-size:14px;cursor:pointer}
.action span{display:block;font-size:22px}
.comment-panel{position:absolute;right:0;top:0;height:100%;width:min(390px,90%);background:#fff;color:#222;z-index:10;transform:translateX(100%);transition:.25s;display:flex;flex-direction:column}
.card.comments-open .comment-panel{transform:translateX(0)}
.comment-head{padding:18px;border-bottom:1px solid #ddd;display:flex;justify-content:space-between;font-weight:800}
.comment-list{flex:1;overflow:auto;padding:12px}.comment{padding:10px 4px;border-bottom:1px solid #eee}.comment small{color:#777}
.comment-form{display:flex;padding:12px;border-top:1px solid #ddd;gap:7px}.comment-form input{flex:1;padding:11px;border:1px solid #ddd;border-radius:20px}.comment-form button{border:0;border-radius:20px;background:#287a3e;color:white;padding:0 16px}
.form{max-width:760px;margin:auto;background:#fff;padding:28px;border-radius:22px}.form input,.form textarea{width:100%;padding:12px;margin:7px 0 15px;border:1px solid #dce8dc;border-radius:12px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:15px}
.auth{max-width:430px;margin:70px auto;background:#fff;padding:35px;border-radius:22px}.auth input{width:100%;padding:12px;margin:8px 0 16px;border:1px solid #ddd;border-radius:10px}
table{width:100%;background:#fff;border-collapse:collapse}td,th{padding:12px;border-bottom:1px solid #ddd;text-align:left}
.alert{padding:12px;background:#e7f5e5;margin-bottom:15px;border-radius:10px}
@media(max-width:700px){nav{padding:0 15px}nav a{margin-left:8px;font-size:12px}.hero{padding:30px}.hero h1{font-size:35px}.feed{height:calc(100vh - 145px)}.card{height:calc(100vh - 155px)}.grid{grid-template-columns:1fr}.overlay{padding-right:85px}.comment-panel{width:100%}}
</style></head><body>
<nav><a class="brand" href="{{url_for('home')}}">📖 VĂN HÓA ĐỌC</a><div>
<a href="{{url_for('home')}}">🏠 Trang chủ</a>{% if session.get('uid') %}
<a href="{{url_for('new_post')}}">➕ Chia sẻ</a>
{% if session.get('role')=='admin' %}<a href="{{url_for('admin')}}">⚙️ Admin</a>{% endif %}
<a href="{{url_for('logout')}}">Đăng xuất</a>{% else %}<a href="{{url_for('login')}}">Đăng nhập</a>{% endif %}
</div></nav><main>
{% with m=get_flashed_messages() %}{% for x in m %}<div class="alert">{{x}}</div>{% endfor %}{% endwith %}
{{content|safe}}</main></body></html>
"""

HOME = """
<section class="hero"><div><b>🌱 CỘNG ĐỒNG ĐỌC SÁCH</b><h1>Mỗi trang sách<br><em>một điều để nhớ.</em></h1><p>Cuộn lên xuống để khám phá từng trang sách và cảm nhận của mọi người.</p>{% if session.get('uid') %}<a class="btn" href="{{url_for('new_post')}}">📸 Chia sẻ trang sách</a>{% endif %}</div><div style="font-size:130px">📖🌿</div></section>
<div class="feedhead"><h2>Khám phá trang sách</h2><form><input name="q" value="{{q}}" placeholder="🔍 Tìm sách, tác giả, người chia sẻ..." style="padding:12px;border:1px solid #ddd;border-radius:12px"><button class="btn">Tìm</button></form></div>
<div class="feed" id="feed">
{% for p in posts %}
<article class="card" data-id="{{p.id}}">
{% if p.image %}<img src="{{url_for('up',name=p.image)}}">{% elif p.video %}<video src="{{url_for('up',name=p.video)}}" controls loop></video>{% else %}<div style="height:100%;display:grid;place-items:center;font-size:100px">📖</div>{% endif %}
<div class="overlay"><div>👤 {{p.full_name}}</div><h2>📚 {{p.book_title}}</h2>{% if p.author %}<small>Tác giả: {{p.author}}</small>{% endif %}<p>💭 {{p.impression}}</p></div>
<div class="actions"><form method="post" action="{{url_for('like',id=p.id)}}"><button class="action">❤️<span>{{p.likes}}</span></button></form><button class="action comment-btn">💬<span>{{p.comments}}</span></button></div>
<div class="comment-panel"><div class="comment-head">💬 Bình luận <button type="button" class="close-comment">✕</button></div><div class="comment-list">
{% for c in comments[p.id] %}<div class="comment"><b>{{c.full_name}}</b><div>{{c.content}}</div><small>{{c.created_at}}</small></div>{% else %}<p>Chưa có bình luận.</p>{% endfor %}
</div>{% if session.get('uid') %}<form class="comment-form" method="post" action="{{url_for('comment',id=p.id)}}"><input name="content" required placeholder="Viết bình luận..."><button>Gửi</button></form>{% else %}<div style="padding:15px">Hãy đăng nhập để bình luận.</div>{% endif %}</div>
</article>
{% else %}<div style="padding:80px;text-align:center;background:white;border-radius:20px">📖<h2>Chưa có bài chia sẻ</h2></div>{% endfor %}
</div>
<script>
document.querySelectorAll('.card').forEach(card=>{
 const btn=card.querySelector('.comment-btn'), close=card.querySelector('.close-comment');
 btn?.addEventListener('click',()=>card.classList.add('comments-open'));
 close?.addEventListener('click',()=>card.classList.remove('comments-open'));
});
const obs=new IntersectionObserver(es=>es.forEach(e=>{const v=e.target.querySelector('video');if(v){if(e.isIntersecting)v.play().catch(()=>{});else v.pause()}}),{threshold:.7});
document.querySelectorAll('.card').forEach(c=>obs.observe(c));
</script>
"""

LOGIN = """<div class="auth"><h1>🌿 Đăng nhập</h1><form method="post"><label>Tài khoản</label><input name="username" required><label>Mật khẩu</label><input type="password" name="password" required><button class="btn">Đăng nhập</button></form><p style="color:#777">Admin ban đầu: <b>admin</b> / <b>Admin@123</b></p></div>"""
FORM = """<div class="form"><h1>📸 Chia sẻ trang sách</h1><form method="post" enctype="multipart/form-data"><div class="grid"><div><label>Tên sách *</label><input name="book_title" required></div><div><label>Tác giả</label><input name="author"></div></div><label>Ảnh trang sách</label><input type="file" name="image" accept="image/*"><label>💭 Điều tôi ấn tượng *</label><textarea name="impression" rows="7" required></textarea><div class="grid"><div><label>Video</label><input type="file" name="video" accept="video/*"></div><div><label>File</label><input type="file" name="file"></div></div><label>URL</label><input name="url" type="url"><button class="btn">🌿 Đăng bài</button></form></div>"""

@app.route("/")
def home():
    c=db(); q=request.args.get("q","").strip()
    sql="""SELECT p.*,u.full_name,(SELECT COUNT(*) FROM likes l WHERE l.post_id=p.id) likes,(SELECT COUNT(*) FROM comments x WHERE x.post_id=p.id) comments FROM posts p JOIN users u ON u.id=p.user_id"""
    if q: rows=c.execute(sql+" WHERE p.book_title LIKE ? OR p.author LIKE ? OR p.impression LIKE ? ORDER BY p.id DESC",(f"%{q}%",f"%{q}%",f"%{q}%")).fetchall()
    else: rows=c.execute(sql+" ORDER BY p.id DESC").fetchall()
    cs={p["id"]:c.execute("SELECT x.*,u.full_name FROM comments x JOIN users u ON u.id=x.user_id WHERE x.post_id=? ORDER BY x.id DESC",(p["id"],)).fetchall() for p in rows}
    c.close(); return render_template_string(BASE,title="Văn Hóa Đọc",content=render_template_string(HOME,posts=rows,comments=cs,q=q))

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        c=db(); u=c.execute("SELECT * FROM users WHERE username=?",(request.form["username"],)).fetchone(); c.close()
        if u and check_password_hash(u["password"],request.form["password"]):
            session.update(uid=u["id"],name=u["full_name"],role=u["role"]); return redirect(url_for("home"))
        flash("Sai tài khoản hoặc mật khẩu.")
    return render_template_string(BASE,title="Đăng nhập",content=LOGIN)

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("home"))

@app.route("/post/new",methods=["GET","POST"])
@login_required
def new_post():
    if request.method=="POST":
        c=db(); img=save(request.files.get("image"),{"png","jpg","jpeg","gif","webp"}); vid=save(request.files.get("video"),{"mp4","webm","mov"}); fil=save(request.files.get("file"),{"pdf","doc","docx","ppt","pptx","txt"})
        c.execute("INSERT INTO posts(user_id,book_title,author,impression,image,video,file,url) VALUES(?,?,?,?,?,?,?,?)",(session["uid"],request.form["book_title"],request.form.get("author",""),request.form["impression"],img,vid,fil,request.form.get("url",""))); c.commit(); c.close(); return redirect(url_for("home"))
    return render_template_string(BASE,title="Chia sẻ",content=FORM)

@app.post("/post/<int:id>/like")
@login_required
def like(id):
    c=db(); x=c.execute("SELECT id FROM likes WHERE post_id=? AND user_id=?",(id,session["uid"])).fetchone()
    if x:c.execute("DELETE FROM likes WHERE id=?",(x["id"],))
    else:c.execute("INSERT OR IGNORE INTO likes(post_id,user_id) VALUES(?,?)",(id,session["uid"]))
    c.commit();c.close();return redirect(url_for("home"))

@app.post("/post/<int:id>/comment")
@login_required
def comment(id):
    text=request.form.get("content","").strip()
    if text:
        c=db();c.execute("INSERT INTO comments(post_id,user_id,content) VALUES(?,?,?)",(id,session["uid"],text));c.commit();c.close()
    return redirect(url_for("home"))

@app.route("/admin",methods=["GET","POST"])
@login_required
@admin_required
def admin():
    c=db()
    if request.method=="POST":
        try:c.execute("INSERT INTO users(username,password,full_name) VALUES(?,?,?)",(request.form["username"],generate_password_hash(request.form["password"]),request.form["full_name"]));c.commit();flash("Đã tạo tài khoản.")
        except sqlite3.IntegrityError:flash("Tên tài khoản đã tồn tại.")
    users=c.execute("SELECT username,full_name,role FROM users ORDER BY id DESC").fetchall();posts=c.execute("SELECT p.*,u.full_name FROM posts p JOIN users u ON u.id=p.user_id ORDER BY p.id DESC").fetchall();c.close()
    html="""<h1>⚙️ Bảng điều khiển</h1><div class="form"><h2>👥 Cấp tài khoản</h2><form method="post"><input name="full_name" placeholder="Họ và tên" required><input name="username" placeholder="Tên tài khoản" required><input name="password" placeholder="Mật khẩu" required><button class="btn">Tạo tài khoản</button></form></div><br><div class="form"><h2>👥 Thành viên</h2><table><tr><th>Họ tên</th><th>Tài khoản</th><th>Quyền</th></tr>{% for u in users %}<tr><td>{{u.full_name}}</td><td>{{u.username}}</td><td>{{u.role}}</td></tr>{% endfor %}</table></div>"""
    return render_template_string(BASE,title="Admin",content=render_template_string(html,users=users,posts=posts))

@app.route("/uploads/<name>")
def up(name): return __import__("flask").send_from_directory(UPLOAD,name)

init()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))