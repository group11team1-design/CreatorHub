import os, sqlite3, secrets, re
from pathlib import Path
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, send_from_directory

BASE = Path(__file__).resolve().parent

# On Vercel the deployment root is read-only; writable storage lives in /tmp.
_IS_VERCEL = os.getenv("VERCEL") == "1"
_TMP = Path("/tmp") if _IS_VERCEL else BASE

FILES = _TMP / "uploads" / "files"
IMAGES = _TMP / "uploads" / "screenshots"
FILES.mkdir(parents=True, exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
# On Vercel, always generate a secret from env or a random fallback (no disk write).
if os.getenv("SECRET_KEY"):
    app.secret_key = os.environ["SECRET_KEY"]
elif _IS_VERCEL:
    app.secret_key = secrets.token_urlsafe(48)  # ephemeral; set SECRET_KEY env var for persistence
else:
    _secret_file = BASE / ".secret_key"
    if not _secret_file.exists():
        _secret_file.write_text(secrets.token_urlsafe(48), encoding="utf-8")
    app.secret_key = _secret_file.read_text(encoding="utf-8").strip()
app.config.update(
    MAX_CONTENT_LENGTH=500 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
CATS = ["Applications", "Extensions", "Wallpapers", "Games", "Websites", "Tools", "Designs", "Other"]
CREATOR_NAME = os.getenv("CREATOR_NAME", "Independent Creator")
CREATOR_TAGLINE = os.getenv("CREATOR_TAGLINE", "Independent creator · Apps, tools and digital experiences")
CREATOR_BIO = os.getenv("CREATOR_BIO", "I build apps, extensions, creative tools and digital experiences.")
CREATOR_LOCATION = os.getenv("CREATOR_LOCATION", "")
DB = _TMP / "creatorhub.db"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

def conn():
    db = sqlite3.connect(DB, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db

with conn() as db:
    db.execute("""CREATE TABLE IF NOT EXISTS items(
        id INTEGER PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL, category TEXT NOT NULL,
        version TEXT, requirements TEXT, filename TEXT NOT NULL, original TEXT NOT NULL, cover TEXT,
        screenshots TEXT, downloads INTEGER DEFAULT 0, published INTEGER DEFAULT 1,
        created TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    existing_columns = {row[1] for row in db.execute("PRAGMA table_info(items)").fetchall()}
    if "ad_banner" not in existing_columns:
        db.execute("ALTER TABLE items ADD COLUMN ad_banner TEXT DEFAULT ''")
    db.execute("""CREATE TABLE IF NOT EXISTS creator_accounts(
        id INTEGER PRIMARY KEY CHECK(id=1), username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
        created TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]

def verify_csrf():
    supplied = request.form.get("csrf", "")
    expected = session.get("csrf", "")
    if not supplied or not expected or not secrets.compare_digest(supplied, expected):
        abort(400, description="Your form expired. Refresh the page and try again.")

def is_setup_needed():
    with conn() as db:
        return db.execute("SELECT COUNT(*) FROM creator_accounts").fetchone()[0] == 0

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapped

def save_image(file_obj):
    if not file_obj or not file_obj.filename:
        return ""
    ext = Path(file_obj.filename).suffix.lower()
    if ext not in IMAGE_EXTS:
        raise ValueError("Images must be PNG, JPG, JPEG, WEBP or GIF.")
    name = secrets.token_hex(16) + ext
    file_obj.save(IMAGES / name)
    return name

def remove_file(folder, name):
    if not name:
        return
    # Only remove a plain filename from the intended upload folder.
    if Path(name).name != name:
        return
    try:
        (folder / name).unlink(missing_ok=True)
    except OSError:
        pass

@app.context_processor
def inject_globals():
    return {
        "categories": CATS, "is_admin": bool(session.get("admin")),
        "creator_name": CREATOR_NAME, "creator_tagline": CREATOR_TAGLINE,
        "creator_bio": CREATOR_BIO, "creator_location": CREATOR_LOCATION,
        "setup_needed": is_setup_needed(), "csrf": csrf_token(),
    }

@app.route("/")
def home():
    category = request.args.get("category", "")
    query = request.args.get("q", "").strip()[:100]
    sql = "SELECT * FROM items WHERE published=1"
    args = []
    if category in CATS:
        sql += " AND category=?"
        args.append(category)
    if query:
        sql += " AND (title LIKE ? OR description LIKE ?)"
        args.extend([f"%{query}%", f"%{query}%"])
    sql += " ORDER BY created DESC"
    with conn() as db:
        items = db.execute(sql, args).fetchall()
        popular = db.execute("SELECT * FROM items WHERE published=1 ORDER BY downloads DESC, created DESC LIMIT 8").fetchall()
        advertised = db.execute("SELECT * FROM items WHERE published=1 AND COALESCE(ad_banner,'')<>'' ORDER BY created DESC LIMIT 6").fetchall()
    return render_template("home.html", items=items, popular=popular, advertised=advertised, cat=category, q=query)

@app.route("/downloads")
def downloads():
    query = request.args.get("q", "").strip()[:100]
    sql = "SELECT * FROM items WHERE published=1"
    args = []
    if query:
        sql += " AND (title LIKE ? OR description LIKE ?)"
        args.extend([f"%{query}%", f"%{query}%"])
    sql += " ORDER BY downloads DESC, created DESC"
    with conn() as db:
        items = db.execute(sql, args).fetchall()
    return render_template("downloads.html", items=items, q=query)

@app.route("/item/<int:item_id>")
def detail(item_id):
    with conn() as db:
        item = db.execute("SELECT * FROM items WHERE id=? AND published=1", (item_id,)).fetchone()
    if not item:
        abort(404)
    shots = [name for name in (item["screenshots"] or "").split(",") if name]
    with conn() as db:
        discover = db.execute("SELECT * FROM items WHERE published=1 AND id<>? ORDER BY downloads DESC, created DESC LIMIT 5", (item_id,)).fetchall()
    file_path = FILES / item["filename"]
    item_size_mb = round(file_path.stat().st_size / (1024 * 1024), 1) if file_path.is_file() else 0
    return render_template("detail.html", item=item, shots=shots, discover=discover, item_size_mb=item_size_mb)

@app.route("/download/<int:item_id>")
def download(item_id):
    with conn() as db:
        item = db.execute("SELECT * FROM items WHERE id=? AND published=1", (item_id,)).fetchone()
        if not item:
            abort(404)
        file_path = FILES / item["filename"]
        if not file_path.is_file():
            abort(404, description="This download is temporarily unavailable.")
        db.execute("UPDATE items SET downloads=downloads+1 WHERE id=?", (item_id,))
    return send_from_directory(FILES, item["filename"], as_attachment=True, download_name=item["original"])

@app.route("/image/<name>")
def image(name):
    if Path(name).name != name:
        abort(404)
    return send_from_directory(IMAGES, name)

@app.route("/admin/setup", methods=["GET", "POST"])
def setup():
    if not is_setup_needed():
        return redirect(url_for("login"))
    if request.method == "POST":
        verify_csrf()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", username):
            flash("Username must be 3–32 characters: letters, numbers, dot, dash or underscore.", "error")
        elif len(password) < 10:
            flash("Use a password with at least 10 characters.", "error")
        elif password != confirm:
            flash("The passwords do not match.", "error")
        else:
            try:
                with conn() as db:
                    db.execute("INSERT INTO creator_accounts(id,username,password_hash) VALUES(1,?,?)",
                               (username, generate_password_hash(password)))
                session.clear()
                session["admin"] = True
                session["username"] = username
                session["csrf"] = secrets.token_urlsafe(32)
                flash("Your private creator account is ready. Welcome!", "success")
                return redirect(url_for("dashboard"))
            except sqlite3.IntegrityError:
                flash("That username is already in use.", "error")
    return render_template("setup.html", token=csrf_token())

@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if is_setup_needed():
        return redirect(url_for("setup"))
    if session.get("admin"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        verify_csrf()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with conn() as db:
            account = db.execute("SELECT * FROM creator_accounts WHERE id=1").fetchone()
        if account and secrets.compare_digest(username, account["username"]) and check_password_hash(account["password_hash"], password):
            session.clear()
            session["admin"] = True
            session["username"] = account["username"]
            session["csrf"] = secrets.token_urlsafe(32)
            next_url = request.args.get("next", "")
            if not next_url.startswith("/") or next_url.startswith("//"):
                next_url = url_for("dashboard")
            return redirect(next_url)
        flash("That username or password doesn't match. Please try again.", "error")
    return render_template("login.html", token=csrf_token())

@app.route("/admin/logout", methods=["POST"])
@admin_required
def logout():
    verify_csrf()
    session.clear()
    flash("You have signed out securely.", "success")
    return redirect(url_for("home"))

@app.route("/admin")
@admin_required
def dashboard():
    with conn() as db:
        items = db.execute("SELECT * FROM items ORDER BY created DESC").fetchall()
        count = db.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        published = db.execute("SELECT COUNT(*) FROM items WHERE published=1").fetchone()[0]
        downloads = db.execute("SELECT COALESCE(SUM(downloads),0) FROM items").fetchone()[0]
    return render_template("admin.html", items=items, count=count, published=published, downloads=downloads, token=csrf_token())

@app.route("/admin/add", methods=["GET", "POST"])
@admin_required
def add():
    if request.method == "POST":
        verify_csrf()
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "")
        upload = request.files.get("file")
        if not title or not description or category not in CATS or not upload or not upload.filename:
            flash("Add a title, description, category and the file you want to publish.", "error")
            return render_template("add.html", token=csrf_token())
        if len(title) > 100 or len(description) > 5000:
            flash("Keep the title under 100 characters and description under 5,000 characters.", "error")
            return render_template("add.html", token=csrf_token())
        stored = secrets.token_hex(20) + Path(secure_filename(upload.filename)).suffix.lower()
        original = secure_filename(upload.filename) or "download"
        created_images = []
        try:
            upload.save(FILES / stored)
            cover = save_image(request.files.get("cover"))
            if cover:
                created_images.append(cover)
            ad_banner = save_image(request.files.get("ad_banner"))
            if ad_banner:
                created_images.append(ad_banner)
            shots = []
            for image_file in request.files.getlist("screenshots"):
                if image_file and image_file.filename:
                    saved = save_image(image_file)
                    created_images.append(saved)
                    shots.append(saved)
            with conn() as db:
                db.execute("""INSERT INTO items(title,description,category,version,requirements,filename,original,cover,screenshots,ad_banner)
                    VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (title, description, category, request.form.get("version", "").strip()[:30],
                     request.form.get("requirements", "").strip()[:500], stored, original, cover, ",".join(shots), ad_banner))
        except (ValueError, OSError) as exc:
            remove_file(FILES, stored)
            for name in created_images:
                remove_file(IMAGES, name)
            flash(str(exc) or "The upload failed. Please try again.", "error")
            return render_template("add.html", token=csrf_token())
        flash("Published successfully! Your creation is now in the store.", "success")
        return redirect(url_for("dashboard"))
    return render_template("add.html", token=csrf_token())

@app.route("/admin/edit/<int:item_id>", methods=["GET", "POST"])
@admin_required
def edit(item_id):
    with conn() as db:
        item = db.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if not item:
        abort(404)
    if request.method == "POST":
        verify_csrf()
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "")
        if not title or not description or category not in CATS:
            flash("Title, description and a valid category are required.", "error")
            return render_template("edit.html", item=item, token=csrf_token())
        cover = item["cover"]
        ad_banner = item["ad_banner"] if "ad_banner" in item.keys() else ""
        new_images = []
        try:
            if request.files.get("cover") and request.files["cover"].filename:
                cover = save_image(request.files["cover"])
                new_images.append(cover)
            if request.files.get("ad_banner") and request.files["ad_banner"].filename:
                ad_banner = save_image(request.files["ad_banner"])
                new_images.append(ad_banner)
            shots = [s for s in (item["screenshots"] or "").split(",") if s]
            for image_file in request.files.getlist("screenshots"):
                if image_file and image_file.filename:
                    saved = save_image(image_file)
                    new_images.append(saved)
                    shots.append(saved)
            with conn() as db:
                db.execute("""UPDATE items SET title=?,description=?,category=?,version=?,requirements=?,cover=?,screenshots=?,published=?,ad_banner=? WHERE id=?""",
                    (title, description, category, request.form.get("version", "").strip()[:30],
                     request.form.get("requirements", "").strip()[:500], cover, ",".join(shots),
                     int(request.form.get("published") == "on"), ad_banner, item_id))
        except (ValueError, OSError) as exc:
            for name in new_images:
                remove_file(IMAGES, name)
            flash(str(exc) or "The update failed. Please try again.", "error")
            return render_template("edit.html", item=item, token=csrf_token())
        flash("Your changes have been saved.", "success")
        return redirect(url_for("dashboard"))
    return render_template("edit.html", item=item, token=csrf_token())

@app.route("/admin/delete/<int:item_id>", methods=["POST"])
@admin_required
def delete(item_id):
    verify_csrf()
    with conn() as db:
        item = db.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
        if item:
            db.execute("DELETE FROM items WHERE id=?", (item_id,))
    if item:
        remove_file(FILES, item["filename"])
        remove_file(IMAGES, item["cover"])
        remove_file(IMAGES, item["ad_banner"] if "ad_banner" in item.keys() else "")
        for name in (item["screenshots"] or "").split(","):
            remove_file(IMAGES, name)
    flash("Creation deleted.", "success")
    return redirect(url_for("dashboard"))

@app.errorhandler(413)
def too_large(error):
    flash("That upload is too large. The maximum combined request size is 500 MB.", "error")
    return redirect(url_for("add") if session.get("admin") else url_for("home"))

@app.errorhandler(400)
def bad_request(error):
    return render_template("error.html", code=400, message=getattr(error, "description", "Bad request.")), 400

@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", code=404, message=getattr(error, "description", "Page not found.")), 404

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", 5000)), debug=False)
