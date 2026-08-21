# --- AUTO-CREATE WEB ASSETS ---
from pathlib import Path as _Path
_BASE = _Path(__file__).resolve().parent
_ASSETS = {'templates/base.html': '<!DOCTYPE html>\n<html lang="vi">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>{% block title %}Văn Hóa Đọc{% endblock %}</title>\n    <link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/style.css\') }}">\n</head>\n<body>\n<header class="topbar">\n    <a class="brand" href="{{ url_for(\'home\') }}">\n        <span class="brand-icon">📖</span>\n        <span><strong>VĂN HÓA ĐỌC</strong><small>Mỗi trang sách · Một điều ý nghĩa</small></span>\n    </a>\n    <nav>\n        <a href="{{ url_for(\'home\') }}">🏠 Trang chủ</a>\n        {% if current_user %}\n            <a href="{{ url_for(\'new_post\') }}">➕ Chia sẻ</a>\n            <a href="{{ url_for(\'profile\') }}">👤 {{ current_user }}</a>\n            {% if is_admin %}<a href="{{ url_for(\'admin\') }}">⚙️ Admin</a>{% endif %}\n            <a class="nav-login" href="{{ url_for(\'logout\') }}">Đăng xuất</a>\n        {% else %}\n            <a class="nav-login" href="{{ url_for(\'login\') }}">Đăng nhập</a>\n        {% endif %}\n    </nav>\n</header>\n\n<main class="page">\n    {% with messages = get_flashed_messages(with_categories=true) %}\n      {% for category, message in messages %}\n        <div class="alert {{ category }}">{{ message }}</div>\n      {% endfor %}\n    {% endwith %}\n    {% block content %}{% endblock %}\n</main>\n\n<footer>\n    <div>🌿 <strong>Văn Hóa Đọc</strong></div>\n    <span>Đọc để hiểu · Hiểu để sống đẹp hơn</span>\n</footer>\n</body>\n</html>\n', 'templates/post_detail.html': '{% extends "base.html" %}\n{% block title %}{{ post.book_title }}{% endblock %}\n{% block content %}\n<div class="detail">\n    <a class="back" href="{{ url_for(\'home\') }}">← Quay lại bảng tin</a>\n    <article class="detail-card">\n        <div class="post-meta">\n            <div class="avatar">{{ post.full_name[0]|upper }}</div>\n            <div><strong>{{ post.full_name }}</strong><small>{{ post.created_at }}</small></div>\n        </div>\n        <h1>📚 {{ post.book_title }}</h1>\n        {% if post.author %}<p class="author">Tác giả: {{ post.author }}</p>{% endif %}\n        {% if post.image_filename %}\n            <img class="detail-image" src="{{ url_for(\'uploads\', filename=post.image_filename) }}" alt="Trang sách">\n        {% endif %}\n        <div class="impression large">\n            <span>💭 Điều tôi ấn tượng</span>\n            <p>{{ post.impression }}</p>\n        </div>\n        {% if post.video_filename %}\n        <video class="post-video" controls><source src="{{ url_for(\'uploads\', filename=post.video_filename) }}"></video>\n        {% endif %}\n        {% if post.external_url %}<a class="link-card" href="{{ post.external_url }}" target="_blank">🔗 {{ post.external_url }}</a>{% endif %}\n        {% if post.file_filename %}<a class="file-card" href="{{ url_for(\'uploads\', filename=post.file_filename) }}">📎 Xem tài liệu</a>{% endif %}\n\n        <div class="post-actions">\n            {% if current_user %}\n            <form method="post" action="{{ url_for(\'like_post\', post_id=post.id) }}"><button class="action-btn">❤️ {{ post.like_count }} thích</button></form>\n            {% else %}<span>❤️ {{ post.like_count }} thích</span>{% endif %}\n        </div>\n\n        <section class="comments">\n            <h2>💬 Bình luận</h2>\n            {% if current_user %}\n            <form method="post" action="{{ url_for(\'comment_post\', post_id=post.id) }}" class="comment-form">\n                <textarea name="content" rows="3" required placeholder="Viết điều bạn muốn chia sẻ..."></textarea>\n                <button class="btn primary">Gửi bình luận</button>\n            </form>\n            {% endif %}\n            {% for c in comments %}\n            <div class="comment"><div class="avatar small">{{ c.full_name[0]|upper }}</div><div><strong>{{ c.full_name }}</strong><p>{{ c.content }}</p><small>{{ c.created_at }}</small></div></div>\n            {% else %}<p class="muted">Chưa có bình luận.</p>{% endfor %}\n        </section>\n    </article>\n</div>\n{% endblock %}\n', 'templates/home.html': '{% extends "base.html" %}\n{% block title %}Trang chủ · Văn Hóa Đọc{% endblock %}\n{% block content %}\n<section class="hero hero-compact">\n    <div>\n        <span class="eyebrow">🌱 CỘNG ĐỒNG ĐỌC SÁCH</span>\n        <h1>Mỗi trang sách<br><em>một điều để nhớ.</em></h1>\n        <p>Cuộn lên xuống để khám phá từng trang sách và cảm nhận của mọi người.</p>\n        {% if current_user %}\n            <a class="btn primary" href="{{ url_for(\'new_post\') }}">📸 Chia sẻ trang sách</a>\n        {% else %}\n            <a class="btn primary" href="{{ url_for(\'login\') }}">🔐 Đăng nhập để chia sẻ</a>\n        {% endif %}\n    </div>\n    <div class="hero-art"><div class="leaf">🌿</div><div class="open-book">📖</div><div class="spark">✦</div></div>\n</section>\n\n<section class="feed-head">\n    <div>\n        <span class="eyebrow">BẢNG TIN DỌC</span>\n        <h2>Khám phá trang sách</h2>\n    </div>\n    <form class="search" method="get">\n        <input name="q" value="{{ q }}" placeholder="🔍 Tìm sách, tác giả, người chia sẻ...">\n        <button>Tìm</button>\n    </form>\n</section>\n\n<div class="tiktok-hint">↕️ Vuốt lên / xuống hoặc dùng con lăn để chuyển bài</div>\n\n<div class="feed tiktok-feed" id="readingFeed">\n{% for post in posts %}\n<article class="post-card tiktok-post">\n    <div class="tiktok-media">\n        {% if post.image_filename %}\n            <img class="post-image tiktok-image" src="{{ url_for(\'uploads\', filename=post.image_filename) }}" alt="Trang sách {{ post.book_title }}">\n        {% elif post.video_filename %}\n            <video class="post-video tiktok-video" muted loop playsinline preload="metadata">\n                <source src="{{ url_for(\'uploads\', filename=post.video_filename) }}">\n            </video>\n        {% else %}\n            <div class="book-placeholder">📖<span>{{ post.book_title }}</span></div>\n        {% endif %}\n        <div class="media-gradient"></div>\n        <div class="tiktok-info">\n            <div class="post-meta">\n                <div class="avatar">{{ post.full_name[0]|upper }}</div>\n                <div><strong>{{ post.full_name }}</strong><small>{{ post.created_at }}</small></div>\n            </div>\n            <div class="book-title">📚 {{ post.book_title }}</div>\n            {% if post.author %}<div class="author">Tác giả: {{ post.author }}</div>{% endif %}\n            <div class="impression">\n                <span>💭 Điều tôi ấn tượng</span>\n                <p>{{ post.impression }}</p>\n            </div>\n        </div>\n\n        <div class="tiktok-actions">\n            {% if current_user %}\n            <form method="post" action="{{ url_for(\'like_post\', post_id=post.id) }}">\n                <button class="round-action" aria-label="Thích bài viết">❤️<b>{{ post.like_count }}</b></button>\n            </form>\n            {% else %}\n                <a class="round-action" href="{{ url_for(\'login\') }}">❤️<b>{{ post.like_count }}</b></a>\n            {% endif %}\n            <button type="button" class="round-action comment-open" data-post-id="{{ post.id }}" data-book-title="{{ post.book_title|e }}" aria-label="Mở bình luận">💬<b>{{ post.comment_count }}</b></button>\n            {% if post.external_url %}<a class="round-action" href="{{ post.external_url }}" target="_blank" rel="noopener">🔗<b>Link</b></a>{% endif %}\n            {% if post.file_filename %}<a class="round-action" href="{{ url_for(\'uploads\', filename=post.file_filename) }}" target="_blank">📎<b>File</b></a>{% endif %}\n        </div>\n    </div>\n</article>\n{% else %}\n<div class="empty"><div>📖</div><h3>Chưa có bài chia sẻ</h3><p>Hãy là người đầu tiên chia sẻ một trang sách.</p></div>\n{% endfor %}\n</div>\n\n<div class="comments-modal" id="commentsModal" aria-hidden="true">\n    <div class="comments-backdrop" data-close-comments></div>\n    <section class="comments-panel" role="dialog" aria-modal="true" aria-labelledby="commentsTitle">\n        <header class="comments-header">\n            <div><span class="eyebrow">💬 BÌNH LUẬN</span><h2 id="commentsTitle">Cảm nhận về bài đọc</h2></div>\n            <button type="button" class="comments-close" data-close-comments aria-label="Đóng">×</button>\n        </header>\n        <div class="comments-list" id="commentsList"><div class="comments-loading">Đang tải bình luận...</div></div>\n        {% if current_user %}\n        <form class="comments-compose" id="commentsForm">\n            <textarea id="commentInput" rows="2" maxlength="1000" placeholder="Viết bình luận của bạn..." required></textarea>\n            <button class="btn primary" type="submit">Gửi bình luận</button>\n        </form>\n        {% else %}\n        <div class="comments-login">Bạn cần <a href="{{ url_for(\\\'login\\\') }}">đăng nhập</a> để bình luận.</div>\n        {% endif %}\n    </section>\n</div>\n\n<script>\n(() => {\n    const feed = document.getElementById(\'readingFeed\');\n    if (!feed) return;\n\n    const posts = [...feed.querySelectorAll(\'.tiktok-post\')];\n\n    const playVisibleVideo = () => {\n        const videos = feed.querySelectorAll(\'.tiktok-video\');\n        videos.forEach(v => {\n            const r = v.getBoundingClientRect();\n            const visible = r.top < window.innerHeight * 0.75 && r.bottom > window.innerHeight * 0.25;\n            if (visible) v.play().catch(() => {});\n            else v.pause();\n        });\n    };\n\n    if (\'IntersectionObserver\' in window) {\n        const observer = new IntersectionObserver(entries => {\n            entries.forEach(entry => {\n                const video = entry.target.querySelector(\'.tiktok-video\');\n                if (!video) return;\n                if (entry.isIntersecting && entry.intersectionRatio >= 0.65) {\n                    video.play().catch(() => {});\n                } else {\n                    video.pause();\n                }\n            });\n        }, {root: feed, threshold: [0.2, 0.65, 0.9]});\n        posts.forEach(post => observer.observe(post));\n    }\n\n    feed.addEventListener(\'scroll\', () => {\n        window.requestAnimationFrame(playVisibleVideo);\n    }, {passive: true});\n\n    let wheelLock = false;\n    feed.addEventListener(\'wheel\', e => {\n        if (Math.abs(e.deltaY) < 10 || wheelLock) return;\n        e.preventDefault();\n        wheelLock = true;\n        const current = Math.round(feed.scrollTop / Math.max(feed.clientHeight, 1));\n        const next = e.deltaY > 0 ? current + 1 : current - 1;\n        const target = Math.max(0, Math.min(posts.length - 1, next));\n        feed.scrollTo({top: target * feed.clientHeight, behavior: \'smooth\'});\n        setTimeout(() => wheelLock = false, 650);\n    }, {passive: false});\n})();\n\\n(() => {\n    const modal = document.getElementById(\'commentsModal\');\n    const list = document.getElementById(\'commentsList\');\n    const form = document.getElementById(\'commentsForm\');\n    const input = document.getElementById(\'commentInput\');\n    const title = document.getElementById(\'commentsTitle\');\n    if (!modal || !list) return;\n    let activePostId = null;\n    const esc = (v) => { const d=document.createElement(\'div\'); d.textContent=v ?? \'\'; return d.innerHTML; };\n    const render = (items) => {\n        if (!items.length) { list.innerHTML=\'<div class="comments-empty">🌱 Chưa có bình luận. Hãy là người đầu tiên chia sẻ cảm nhận!</div>\'; return; }\n        list.innerHTML=items.map(c=>`<div class="live-comment"><div class="avatar">${esc((c.full_name||\'?\').charAt(0).toUpperCase())}</div><div class="live-comment-body"><strong>${esc(c.full_name)}</strong><p>${esc(c.content)}</p><small>${esc(c.created_at)}</small></div></div>`).join(\'\');\n        list.scrollTop=list.scrollHeight;\n    };\n    const load = async (id) => {\n        list.innerHTML=\'<div class="comments-loading">Đang tải bình luận...</div>\';\n        try { const r=await fetch(`/post/${id}/comments`,{headers:{Accept:\'application/json\'}}); if(!r.ok) throw new Error(); render((await r.json()).comments||[]); }\n        catch(e){ list.innerHTML=\'<div class="comments-error">Không tải được bình luận. Hãy thử lại.</div>\'; }\n    };\n    const close = () => { modal.classList.remove(\'open\'); modal.setAttribute(\'aria-hidden\',\'true\'); document.body.classList.remove(\'comments-open\'); activePostId=null; };\n    document.querySelectorAll(\'.comment-open\').forEach(btn=>btn.addEventListener(\'click\',e=>{e.preventDefault();e.stopPropagation();activePostId=btn.dataset.postId;title.textContent=`Bình luận · ${btn.dataset.bookTitle||\'Bài đọc\'}`;modal.classList.add(\'open\');modal.setAttribute(\'aria-hidden\',\'false\');document.body.classList.add(\'comments-open\');load(activePostId);setTimeout(()=>input?.focus(),150);}));\n    modal.querySelectorAll(\'[data-close-comments]\').forEach(el=>el.addEventListener(\'click\',close));\n    document.addEventListener(\'keydown\',e=>{if(e.key===\'Escape\'&&modal.classList.contains(\'open\'))close();});\n    form?.addEventListener(\'submit\',async e=>{\n        e.preventDefault(); if(!activePostId||!input.value.trim()) return;\n        const btn=form.querySelector(\'button\'), content=input.value.trim(); btn.disabled=true; btn.textContent=\'Đang gửi...\';\n        try {\n            const r=await fetch(`/post/${activePostId}/comment`,{method:\'POST\',headers:{\'Content-Type\':\'application/x-www-form-urlencoded;charset=UTF-8\',Accept:\'application/json\'},body:new URLSearchParams({content})});\n            if(!r.ok) throw new Error(); const data=await r.json(); render(data.comments||[]); input.value=\'\';\n            const counter=document.querySelector(`.comment-open[data-post-id="${CSS.escape(String(activePostId))}"] b`); if(counter&&data.count!==undefined) counter.textContent=data.count;\n        } catch(e){ alert(\'Không thể gửi bình luận. Vui lòng thử lại.\'); }\n        finally{ btn.disabled=false; btn.textContent=\'Gửi bình luận\'; }\n    });\n})();\\n</script>\n{% endblock %}\n', 'templates/admin.html': '{% extends "base.html" %}\n{% block title %}Quản trị · Văn Hóa Đọc{% endblock %}\n{% block content %}\n<div class="admin-head">\n    <div><span class="eyebrow">⚙️ QUẢN TRỊ</span><h1>Bảng điều khiển</h1></div>\n</div>\n\n<div class="stats">\n    <div><strong>{{ stats.users }}</strong><span>Thành viên</span></div>\n    <div><strong>{{ stats.posts }}</strong><span>Bài chia sẻ</span></div>\n    <div><strong>{{ stats.likes }}</strong><span>Lượt thích</span></div>\n    <div><strong>{{ stats.comments }}</strong><span>Bình luận</span></div>\n</div>\n\n<div class="admin-grid">\n<section class="admin-card">\n    <h2>👥 Cấp tài khoản</h2>\n    <form method="post" action="{{ url_for(\'create_user\') }}">\n        <input name="full_name" required placeholder="Họ và tên">\n        <input name="username" required placeholder="Tên tài khoản">\n        <input name="password" required minlength="6" placeholder="Mật khẩu">\n        <button class="btn primary full">＋ Tạo tài khoản</button>\n    </form>\n</section>\n\n<section class="admin-card">\n    <h2>👥 Thành viên</h2>\n    <div class="table-wrap"><table><tr><th>Họ tên</th><th>Tài khoản</th><th>Quyền</th></tr>\n    {% for u in users %}<tr><td>{{ u.full_name }}</td><td>{{ u.username }}</td><td>{{ u.role }}</td></tr>{% endfor %}\n    </table></div>\n</section>\n</div>\n\n<section class="admin-card">\n<h2>📝 Bài đăng</h2>\n<div class="table-wrap"><table><tr><th>Sách</th><th>Người đăng</th><th></th></tr>\n{% for p in posts %}\n<tr><td>{{ p.book_title }}</td><td>{{ p.full_name }}</td><td><form method="post" action="{{ url_for(\'delete_post\', post_id=p.id) }}" onsubmit="return confirm(\'Xóa bài này?\')"><button class="danger-btn">Xóa</button></form></td></tr>\n{% endfor %}\n</table></div>\n</section>\n{% endblock %}\n', 'templates/login.html': '{% extends "base.html" %}\n{% block title %}Đăng nhập · Văn Hóa Đọc{% endblock %}\n{% block content %}\n<div class="auth-wrap">\n    <div class="auth-card">\n        <div class="auth-logo">📖</div>\n        <span class="eyebrow">VĂN HÓA ĐỌC</span>\n        <h1>Chào mừng trở lại</h1>\n        <p class="muted">Tài khoản được cấp bởi quản trị viên.</p>\n        <form method="post">\n            <label>Tên tài khoản</label>\n            <input name="username" required autofocus placeholder="Nhập tài khoản">\n            <label>Mật khẩu</label>\n            <input type="password" name="password" required placeholder="Nhập mật khẩu">\n            <button class="btn primary full">Đăng nhập</button>\n        </form>\n        <div class="demo-login">Tài khoản quản trị ban đầu: <strong>admin</strong> / <strong>Admin@123</strong></div>\n    </div>\n</div>\n{% endblock %}\n', 'templates/error.html': '{% extends "base.html" %}\n{% block title %}{{ code }}{% endblock %}\n{% block content %}\n<div class="empty">\n    <div>🌿</div><h1>{{ code }}</h1><p>{{ message }}</p><a class="btn primary" href="{{ url_for(\'home\') }}">Về trang chủ</a>\n</div>\n{% endblock %}\n', 'templates/new_post.html': '{% extends "base.html" %}\n{% block title %}Chia sẻ trang sách{% endblock %}\n{% block content %}\n<div class="form-page">\n    <div class="section-title">\n        <span class="eyebrow">📸 CHIA SẺ TRANG SÁCH</span>\n        <h1>Điều gì khiến bạn ấn tượng?</h1>\n        <p>Chụp một trang sách, tải tài liệu hoặc chia sẻ video/link và viết điều bạn muốn lan tỏa.</p>\n    </div>\n\n    <form class="post-form" method="post" enctype="multipart/form-data">\n        <div class="form-grid">\n            <div>\n                <label>Tên sách *</label>\n                <input name="book_title" required placeholder="Ví dụ: Đắc Nhân Tâm">\n            </div>\n            <div>\n                <label>Tác giả</label>\n                <input name="author" placeholder="Tên tác giả">\n            </div>\n        </div>\n\n        <label>📸 Ảnh trang sách</label>\n        <input type="file" name="image" accept="image/*">\n\n        <label>💭 Điều tôi ấn tượng *</label>\n        <textarea name="impression" required rows="7" placeholder="Viết điều khiến bạn suy nghĩ, một bài học hoặc câu chuyện muốn chia sẻ..."></textarea>\n\n        <div class="form-grid">\n            <div>\n                <label>🎬 Video</label>\n                <input type="file" name="video" accept="video/*">\n            </div>\n            <div>\n                <label>📎 File tài liệu</label>\n                <input type="file" name="attachment" accept=".pdf,.doc,.docx,.ppt,.pptx,.txt">\n            </div>\n        </div>\n\n        <label>🔗 URL / đường dẫn</label>\n        <input name="external_url" type="url" placeholder="https://...">\n\n        <div class="form-actions">\n            <a class="btn ghost" href="{{ url_for(\'home\') }}">Hủy</a>\n            <button class="btn primary">🌿 Đăng bài chia sẻ</button>\n        </div>\n    </form>\n</div>\n{% endblock %}\n', 'templates/profile.html': '{% extends "base.html" %}\n{% block title %}Hồ sơ{% endblock %}\n{% block content %}\n<div class="profile-head">\n    <div class="avatar huge">{{ user.full_name[0]|upper }}</div>\n    <div><span class="eyebrow">HỒ SƠ THÀNH VIÊN</span><h1>{{ user.full_name }}</h1><p>@{{ user.username }}</p></div>\n</div>\n<h2>Bài chia sẻ của tôi</h2>\n<div class="feed">\n{% for post in posts %}\n<article class="post-card">\n    <div class="book-title">📚 {{ post.book_title }}</div>\n    {% if post.image_filename %}<img class="post-image" src="{{ url_for(\'uploads\', filename=post.image_filename) }}">{% endif %}\n    <div class="impression"><span>💭 Điều tôi ấn tượng</span><p>{{ post.impression }}</p></div>\n    <a class="action-btn" href="{{ url_for(\'post_detail\', post_id=post.id) }}">Xem bài · ❤️ {{ post.like_count }}</a>\n</article>\n{% else %}<div class="empty"><div>🌱</div><p>Bạn chưa có bài chia sẻ nào.</p></div>{% endfor %}\n</div>\n{% endblock %}\n', 'static/css/style.css': ':root{\n--green:#287a3e;--green2:#3f9852;--light:#eff8ee;--mint:#dff0df;--dark:#173c22;\n--text:#243128;--muted:#708074;--white:#fff;--border:#dce8dc;--shadow:0 12px 35px rgba(31,83,42,.10);\n}\n*{box-sizing:border-box}\nhtml{scroll-behavior:smooth}\nbody{margin:0;background:#f7faf6;color:var(--text);font-family:Inter,Segoe UI,Arial,sans-serif;line-height:1.55}\na{text-decoration:none;color:inherit}\nbutton,input,textarea{font:inherit}\n.topbar{height:76px;background:rgba(255,255,255,.96);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0 5%;position:sticky;top:0;z-index:20;backdrop-filter:blur(12px)}\n.brand{display:flex;align-items:center;gap:12px;color:var(--dark)}\n.brand-icon{width:45px;height:45px;border-radius:14px;background:var(--light);display:grid;place-items:center;font-size:25px}\n.brand strong{display:block;letter-spacing:.5px}.brand small{display:block;color:var(--muted);font-size:11px}\nnav{display:flex;gap:7px;align-items:center}nav a{padding:9px 13px;border-radius:12px;font-size:14px}nav a:hover{background:var(--light);color:var(--green)}.nav-login{background:var(--green);color:#fff!important}\n.page{max-width:1120px;margin:auto;padding:30px 20px 50px}\n.hero{min-height:390px;background:linear-gradient(120deg,#e8f5e7,#f8fcf5);border:1px solid var(--border);border-radius:30px;padding:55px 65px;display:flex;align-items:center;justify-content:space-between;overflow:hidden;box-shadow:var(--shadow)}\n.hero-compact{min-height:280px;padding:38px 55px}.hero h1{font-size:50px;line-height:1.05;color:var(--dark);margin:12px 0}.hero h1 em{font-style:normal;color:var(--green2)}.hero p{max-width:560px;color:var(--muted);font-size:16px;margin-bottom:22px}\n.hero-art{width:280px;height:210px;position:relative;display:grid;place-items:center}.open-book{font-size:120px;filter:drop-shadow(0 15px 12px rgba(40,100,55,.15))}.leaf{position:absolute;font-size:60px;right:15px;top:0}.spark{position:absolute;font-size:38px;left:10px;bottom:20px;color:#6cae5d}\n.eyebrow{font-size:12px;font-weight:800;letter-spacing:1.5px;color:var(--green)}\n.btn{display:inline-flex;border:0;border-radius:13px;padding:12px 19px;cursor:pointer;align-items:center;justify-content:center;font-weight:750}.primary{background:var(--green);color:#fff;box-shadow:0 8px 18px rgba(40,122,62,.18)}.primary:hover{background:#216b35}.ghost{background:#edf3ed}.full{width:100%}\n.feed-head{display:flex;justify-content:space-between;align-items:end;margin:28px 0 10px}.feed-head h2{margin:5px 0;font-size:28px;color:var(--dark)}\n.search{display:flex;gap:8px}.search input{width:310px}.search button{border:0;border-radius:12px;background:var(--dark);color:#fff;padding:0 18px}\ninput,textarea{width:100%;border:1px solid var(--border);background:#fff;border-radius:12px;padding:12px 14px;outline:none;color:var(--text)}input:focus,textarea:focus{border-color:var(--green2);box-shadow:0 0 0 3px #dff0df}\n.tiktok-hint{text-align:center;color:var(--muted);font-size:12px;margin:8px 0 12px}\n.tiktok-feed{height:calc(100vh - 215px);min-height:560px;overflow-y:auto;overflow-x:hidden;scroll-snap-type:y mandatory;scroll-behavior:smooth;scrollbar-width:thin;scrollbar-color:var(--green2) transparent;border-radius:22px}\n.tiktok-feed::-webkit-scrollbar{width:7px}.tiktok-feed::-webkit-scrollbar-thumb{background:var(--green2);border-radius:20px}\n.tiktok-post{position:relative;flex:none;width:100%;height:100%;min-height:100%;scroll-snap-align:start;scroll-snap-stop:always;padding:0;border:0;overflow:hidden;border-radius:22px;background:#17231a;box-shadow:0 10px 35px rgba(20,55,28,.16)}\n.tiktok-media{position:relative;width:100%;height:100%;min-height:100%;overflow:hidden;background:#101810}\n.tiktok-image,.tiktok-video{position:absolute;inset:0;width:100%;height:100%;max-height:none;object-fit:contain;background:#101810;margin:0;border-radius:0}\n.tiktok-video{object-fit:cover}\n.media-gradient{position:absolute;inset:0;background:linear-gradient(to top,rgba(0,0,0,.82) 0%,rgba(0,0,0,.36) 30%,rgba(0,0,0,.04) 58%,rgba(0,0,0,.15) 100%);pointer-events:none}\n.tiktok-info{position:absolute;left:28px;right:100px;bottom:25px;color:#fff;z-index:2}.tiktok-info .post-meta{margin-bottom:10px}.tiktok-info .post-meta small{color:#dbe8dc}.tiktok-info .book-title{font-size:25px;color:#fff;text-shadow:0 1px 3px #000}.tiktok-info .author{color:#dce8dc}.tiktok-info .impression{background:rgba(17,45,22,.74);border-left-color:#7bd182;backdrop-filter:blur(6px);max-width:720px}.tiktok-info .impression span{color:#b8efbd}.tiktok-info .impression p{color:#fff;max-height:100px;overflow:auto}\n.tiktok-actions{position:absolute;right:20px;bottom:28px;z-index:3;display:flex;flex-direction:column;gap:12px;align-items:center}.tiktok-actions form{margin:0}\n.round-action{width:52px;height:52px;border:0;border-radius:50%;background:rgba(255,255,255,.92);display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:22px;cursor:pointer;box-shadow:0 5px 16px rgba(0,0,0,.16)}.round-action b{font-size:10px;color:#253a2a;margin-top:1px}.round-action:hover{transform:scale(1.06)}\n.book-placeholder{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#fff;font-size:100px;background:radial-gradient(circle,#2e7240,#0f2715)}.book-placeholder span{font-size:26px;font-weight:800;max-width:70%;text-align:center}\n.empty{text-align:center;background:#fff;border:1px dashed var(--border);border-radius:20px;padding:60px;min-height:100%;display:grid;place-items:center;align-content:center}.empty div{font-size:50px}.empty h3{color:var(--dark)}\n.alert{padding:12px 15px;border-radius:12px;margin-bottom:15px}.alert.success{background:#e6f5e5;color:#226331}.alert.danger{background:#fff0ef;color:#a82b25}.alert.warning{background:#fff7df;color:#805e12}\n.auth-wrap{min-height:650px;display:grid;place-items:center}.auth-card{width:min(450px,100%);background:#fff;border:1px solid var(--border);border-radius:25px;padding:38px;box-shadow:var(--shadow);text-align:center}.auth-logo{font-size:55px;margin-bottom:10px}.auth-card h1{margin:8px 0;color:var(--dark)}.muted{color:var(--muted)}.auth-card form{text-align:left;margin-top:25px}.auth-card label,.post-form label,.admin-card label{display:block;font-weight:700;font-size:13px;margin:14px 0 7px}.demo-login{font-size:11px;background:#f3f8f1;padding:10px;border-radius:10px;margin-top:18px;color:var(--muted)}\n.form-page{max-width:820px;margin:auto}.section-title{margin:20px 0 25px}.section-title h1{font-size:40px;color:var(--dark);margin:8px 0}.post-form{background:#fff;border:1px solid var(--border);border-radius:22px;padding:30px;box-shadow:var(--shadow)}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.form-actions{display:flex;justify-content:flex-end;gap:10px;margin-top:25px}\n.detail{max-width:800px;margin:auto}.back{color:var(--green);font-weight:700;display:inline-block;margin:8px 0 18px}.detail-card{background:#fff;border:1px solid var(--border);border-radius:20px;padding:22px;box-shadow:0 6px 22px rgba(30,70,38,.06)}.detail-card h1{font-size:34px;color:var(--dark)}.comments{margin-top:30px;border-top:1px solid var(--border);padding-top:22px}.comment-form{margin-bottom:22px}.comment-form button{margin-top:10px}.comment{display:flex;gap:10px;padding:14px 0;border-bottom:1px solid var(--border)}.comment p{margin:4px 0}.comment small{color:var(--muted)}\n.profile-head{background:linear-gradient(120deg,#e8f5e7,#fff);padding:30px;border-radius:22px;display:flex;gap:20px;align-items:center;margin-bottom:30px}.profile-head h1{margin:5px 0;color:var(--dark)}.avatar{width:40px;height:40px;border-radius:50%;background:var(--mint);color:var(--green);display:grid;place-items:center;font-weight:800}.avatar.huge{width:80px;height:80px;font-size:28px}\n.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:22px}.stats div{background:#fff;border:1px solid var(--border);border-radius:17px;padding:20px}.stats strong{display:block;font-size:30px;color:var(--green)}.stats span{color:var(--muted);font-size:13px}.admin-grid{display:grid;grid-template-columns:1fr 1.5fr;gap:20px;margin-bottom:20px}.admin-card{background:#fff;border:1px solid var(--border);border-radius:20px;padding:22px;box-shadow:0 6px 22px rgba(30,70,38,.06)}.admin-card h2{font-size:19px;color:var(--dark)}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:11px;border-bottom:1px solid var(--border)}th{color:var(--green)}.danger-btn{border:0;background:#fff0ef;color:#b42d25;border-radius:8px;padding:7px 10px;cursor:pointer}\nfooter{padding:30px 5%;border-top:1px solid var(--border);background:#edf6eb;color:var(--green);display:flex;justify-content:space-between;font-size:13px}\n@media(max-width:800px){\n.topbar{height:auto;padding:10px 14px;gap:8px;align-items:flex-start}.brand small{display:none}nav{flex-wrap:wrap;justify-content:flex-end}nav a{font-size:11px;padding:7px}\n.page{padding:14px 10px 30px}.hero{padding:28px 22px;min-height:auto}.hero h1{font-size:36px}.hero-art{display:none}.feed-head{display:block;margin-top:22px}.search{margin-top:12px}.search input{width:100%}\n.tiktok-feed{height:calc(100vh - 250px);min-height:520px;border-radius:16px}.tiktok-post,.tiktok-media{border-radius:16px}.tiktok-info{left:16px;right:78px;bottom:18px}.tiktok-info .book-title{font-size:20px}.tiktok-info .impression{padding:10px 12px}.tiktok-info .impression p{max-height:78px}.tiktok-actions{right:10px;bottom:18px;gap:9px}.round-action{width:46px;height:46px;font-size:19px}.tiktok-hint{font-size:11px}\n.form-grid,.admin-grid,.stats{grid-template-columns:1fr}footer{display:block}.section-title h1{font-size:31px}.post-form{padding:20px}\n}\n@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.tiktok-feed{scroll-behavior:auto}.round-action:hover{transform:none}}\n\\n.comments-modal{position:fixed;inset:0;z-index:1000;display:none}.comments-modal.open{display:block}.comments-backdrop{position:absolute;inset:0;background:rgba(5,18,9,.58);backdrop-filter:blur(3px)}.comments-panel{position:absolute;right:0;top:0;height:100%;width:min(460px,100%);background:#fff;display:flex;flex-direction:column;box-shadow:-12px 0 35px rgba(0,0,0,.22);animation:commentsIn .22s ease-out}@keyframes commentsIn{from{transform:translateX(100%)}to{transform:translateX(0)}}.comments-header{padding:22px 20px 16px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;gap:15px;background:#f8fcf6}.comments-header h2{margin:5px 0 0;color:var(--dark);font-size:20px;max-width:340px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.comments-close{width:42px;height:42px;border:0;border-radius:50%;background:#eaf3e8;color:var(--dark);font-size:28px;cursor:pointer;line-height:1}.comments-list{flex:1;overflow-y:auto;padding:12px 20px}.comments-loading,.comments-empty,.comments-error{text-align:center;color:var(--muted);padding:45px 15px}.live-comment{display:flex;gap:10px;padding:15px 0;border-bottom:1px solid #edf2ec}.live-comment-body{min-width:0}.live-comment-body strong{color:var(--dark)}.live-comment-body p{margin:3px 0;white-space:pre-wrap;overflow-wrap:anywhere}.live-comment-body small{color:var(--muted);font-size:11px}.comments-compose{padding:14px 18px;border-top:1px solid var(--border);background:#fff;display:flex;gap:9px;align-items:flex-end}.comments-compose textarea{resize:none;min-height:46px;max-height:120px;flex:1}.comments-compose .btn{min-height:46px;padding:10px 14px;white-space:nowrap}.comments-login{padding:18px;border-top:1px solid var(--border);background:#fff;text-align:center;color:var(--muted)}.comments-login a{color:var(--green);font-weight:800}body.comments-open{overflow:hidden}.comment-open{appearance:none;color:inherit}.comment-open:focus-visible,.comments-close:focus-visible{outline:3px solid #9ad39e;outline-offset:2px}@media(max-width:800px){.comments-panel{width:100%;top:auto;bottom:0;height:min(82vh,700px);border-radius:22px 22px 0 0;animation:commentsUp .22s ease-out}@keyframes commentsUp{from{transform:translateY(100%)}to{transform:translateY(0)}}.comments-header{padding:16px}.comments-list{padding:10px 16px}.comments-compose{padding:10px 12px 12px}.comments-compose .btn{padding:9px 12px}}\\n'}
for _rel, _content in _ASSETS.items():
    _p = _BASE / _rel
    _p.parent.mkdir(parents=True, exist_ok=True)
    _p.write_text(_content, encoding="utf-8")
# --- END AUTO-CREATE WEB ASSETS ---

import os
import sqlite3
from functools import wraps
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database.db"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "webp",
    "mp4", "webm", "mov",
    "pdf", "doc", "docx", "ppt", "pptx", "txt"
}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'member',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        book_title TEXT NOT NULL,
        author TEXT DEFAULT '',
        impression TEXT NOT NULL,
        image_filename TEXT DEFAULT '',
        video_filename TEXT DEFAULT '',
        file_filename TEXT DEFAULT '',
        external_url TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    admin = conn.execute("SELECT id FROM users WHERE username = ?", ("admin",)).fetchone()
    if not admin:
        conn.execute(
            "INSERT INTO users(username,password_hash,full_name,role) VALUES(?,?,?,?)",
            ("admin", generate_password_hash("Admin@123"), "Quản trị viên", "admin")
        )
    conn.commit()
    conn.close()

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Vui lòng đăng nhập.", "warning")
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

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload(file, prefix):
    if not file or not file.filename:
        return ""
    if not allowed_file(file.filename):
        raise ValueError("Định dạng file chưa được hỗ trợ.")
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = secure_filename(f"{prefix}_{os.urandom(8).hex()}.{ext}")
    file.save(UPLOAD_DIR / filename)
    return filename

@app.context_processor
def inject_user():
    return {
        "current_user": session.get("full_name"),
        "is_admin": session.get("role") == "admin"
    }

@app.route("/")
def home():
    conn = get_db()
    q = request.args.get("q", "").strip()
    if q:
        posts = conn.execute("""
            SELECT p.*, u.full_name,
            (SELECT COUNT(*) FROM likes l WHERE l.post_id=p.id) AS like_count,
            (SELECT COUNT(*) FROM comments c WHERE c.post_id=p.id) AS comment_count
            FROM posts p JOIN users u ON u.id=p.user_id
            WHERE p.book_title LIKE ? OR p.author LIKE ? OR p.impression LIKE ? OR u.full_name LIKE ?
            ORDER BY p.id DESC
        """, tuple([f"%{q}%"] * 4)).fetchall()
    else:
        posts = conn.execute("""
            SELECT p.*, u.full_name,
            (SELECT COUNT(*) FROM likes l WHERE l.post_id=p.id) AS like_count,
            (SELECT COUNT(*) FROM comments c WHERE c.post_id=p.id) AS comment_count
            FROM posts p JOIN users u ON u.id=p.user_id
            ORDER BY p.id DESC
        """).fetchall()
    conn.close()
    return render_template("home.html", posts=posts, q=q)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]
            return redirect(url_for("home"))
        flash("Tài khoản hoặc mật khẩu không đúng.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/post/new", methods=["GET", "POST"])
@login_required
def new_post():
    if request.method == "POST":
        book_title = request.form.get("book_title", "").strip()
        author = request.form.get("author", "").strip()
        impression = request.form.get("impression", "").strip()
        external_url = request.form.get("external_url", "").strip()

        if not book_title or not impression:
            flash("Vui lòng nhập tên sách và điều bạn ấn tượng.", "danger")
            return render_template("new_post.html")

        try:
            image = save_upload(request.files.get("image"), "image")
            video = save_upload(request.files.get("video"), "video")
            attachment = save_upload(request.files.get("attachment"), "file")
        except ValueError as e:
            flash(str(e), "danger")
            return render_template("new_post.html")

        conn = get_db()
        conn.execute("""
            INSERT INTO posts(user_id,book_title,author,impression,image_filename,video_filename,file_filename,external_url)
            VALUES(?,?,?,?,?,?,?,?)
        """, (session["user_id"], book_title, author, impression, image, video, attachment, external_url))
        conn.commit()
        conn.close()
        flash("Đã chia sẻ trang sách thành công! 🌿", "success")
        return redirect(url_for("home"))
    return render_template("new_post.html")

@app.route("/post/<int:post_id>")
def post_detail(post_id):
    conn = get_db()
    post = conn.execute("""
        SELECT p.*, u.full_name,
        (SELECT COUNT(*) FROM likes l WHERE l.post_id=p.id) AS like_count
        FROM posts p JOIN users u ON u.id=p.user_id WHERE p.id=?
    """, (post_id,)).fetchone()
    if not post:
        abort(404)
    comments = conn.execute("""
        SELECT c.*, u.full_name FROM comments c JOIN users u ON u.id=c.user_id
        WHERE c.post_id=? ORDER BY c.id DESC
    """, (post_id,)).fetchall()
    liked = False
    if session.get("user_id"):
        liked = conn.execute(
            "SELECT 1 FROM likes WHERE post_id=? AND user_id=?",
            (post_id, session["user_id"])
        ).fetchone() is not None
    conn.close()
    return render_template("post_detail.html", post=post, comments=comments, liked=liked)

@app.post("/post/<int:post_id>/like")
@login_required
def like_post(post_id):
    conn = get_db()
    existing = conn.execute("SELECT id FROM likes WHERE post_id=? AND user_id=?", (post_id, session["user_id"])).fetchone()
    if existing:
        conn.execute("DELETE FROM likes WHERE id=?", (existing["id"],))
    else:
        conn.execute("INSERT OR IGNORE INTO likes(post_id,user_id) VALUES(?,?)", (post_id, session["user_id"]))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("home"))

@app.get("/post/<int:post_id>/comments")
def get_comments(post_id):
    conn = get_db()
    comments = conn.execute("""
        SELECT c.id, c.content, c.created_at, u.full_name
        FROM comments c JOIN users u ON u.id=c.user_id
        WHERE c.post_id=? ORDER BY c.id ASC
    """, (post_id,)).fetchall()
    conn.close()
    return {"comments": [dict(c) for c in comments]}

@app.post("/post/<int:post_id>/comment")
@login_required
def comment_post(post_id):
    content = request.form.get("content", "").strip()
    if not content:
        if "application/json" in request.headers.get("Accept", ""):
            return {"error": "Nội dung bình luận trống."}, 400
        return redirect(request.referrer or url_for("home"))
    conn = get_db()
    conn.execute("INSERT INTO comments(post_id,user_id,content) VALUES(?,?,?)", (post_id, session["user_id"], content))
    conn.commit()
    comments = conn.execute("""
        SELECT c.id, c.content, c.created_at, u.full_name
        FROM comments c JOIN users u ON u.id=c.user_id
        WHERE c.post_id=? ORDER BY c.id ASC
    """, (post_id,)).fetchall()
    conn.close()
    if "application/json" in request.headers.get("Accept", ""):
        return {"comments": [dict(c) for c in comments], "count": len(comments)}
    return redirect(request.referrer or url_for("home"))

@app.route("/profile")
@login_required
def profile():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    posts = conn.execute("""
        SELECT p.*, (SELECT COUNT(*) FROM likes l WHERE l.post_id=p.id) AS like_count
        FROM posts p WHERE p.user_id=? ORDER BY p.id DESC
    """, (session["user_id"],)).fetchall()
    conn.close()
    return render_template("profile.html", user=user, posts=posts)

@app.route("/admin")
@login_required
@admin_required
def admin():
    conn = get_db()
    users = conn.execute("SELECT id,username,full_name,role,created_at FROM users ORDER BY id DESC").fetchall()
    posts = conn.execute("""
        SELECT p.*, u.full_name FROM posts p JOIN users u ON u.id=p.user_id
        ORDER BY p.id DESC
    """).fetchall()
    stats = {
        "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "posts": conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0],
        "likes": conn.execute("SELECT COUNT(*) FROM likes").fetchone()[0],
        "comments": conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0],
    }
    conn.close()
    return render_template("admin.html", users=users, posts=posts, stats=stats)

@app.post("/admin/users/create")
@login_required
@admin_required
def create_user():
    username = request.form.get("username", "").strip()
    full_name = request.form.get("full_name", "").strip()
    password = request.form.get("password", "")
    if not username or not full_name or len(password) < 6:
        flash("Nhập đầy đủ thông tin; mật khẩu tối thiểu 6 ký tự.", "danger")
        return redirect(url_for("admin"))
    conn = get_db()
    try:
        conn.execute("INSERT INTO users(username,password_hash,full_name,role) VALUES(?,?,?,?)",
                     (username, generate_password_hash(password), full_name, "member"))
        conn.commit()
        flash("Đã tạo tài khoản thành viên.", "success")
    except sqlite3.IntegrityError:
        flash("Tên tài khoản đã tồn tại.", "danger")
    finally:
        conn.close()
    return redirect(url_for("admin"))

@app.post("/admin/posts/<int:post_id>/delete")
@login_required
@admin_required
def delete_post(post_id):
    conn = get_db()
    row = conn.execute("SELECT image_filename,video_filename,file_filename FROM posts WHERE id=?", (post_id,)).fetchone()
    conn.execute("DELETE FROM posts WHERE id=?", (post_id,))
    conn.commit()
    conn.close()
    if row:
        for name in [row["image_filename"], row["video_filename"], row["file_filename"]]:
            if name:
                try:
                    (UPLOAD_DIR / name).unlink(missing_ok=True)
                except Exception:
                    pass
    flash("Đã xóa bài đăng.", "success")
    return redirect(url_for("admin"))

@app.route("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(UPLOAD_DIR, filename)

@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", code=403, message="Bạn không có quyền truy cập trang này."), 403

@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, message="Không tìm thấy nội dung."), 404

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
