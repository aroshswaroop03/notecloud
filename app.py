"""
app.py — Scrib-d Flask Backend
Receives an uploaded image, sends it to Claude via the Anthropic API,
and returns the transcribed handwriting as plain text.

Now also includes a full user authentication system using SQLite (a file-based
database built right into Python — no separate server needed) and Flask sessions
(a way to remember who is logged in across multiple page requests).
"""

import base64
import io
import os
import re
import secrets
import sqlite3
from datetime import date, datetime
from functools import wraps

import anthropic
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
try:
    from PIL import Image as PilImage
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
try:
    from google_auth_oauthlib.flow import Flow
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request as GoogleRequest
    from googleapiclient.discovery import build as google_build
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False
from docx import Document
from docx.shared import Pt
from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

# Load environment variables from the .env file so ANTHROPIC_API_KEY is available
load_dotenv()

# Create the Flask application. Flask looks for templates in a "templates/" folder
# and static files (CSS, JS, images) in a "static/" folder by default.
app = Flask(__name__)

# ── Secret key ────────────────────────────────────────────────────────────────
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = os.getenv("FLASK_ENV") != "development"

# ── Security extensions ───────────────────────────────────────────────────────
csrf    = CSRFProtect(app)
limiter = Limiter(get_remote_address, app=app, default_limits=[])

# ── Database path ──────────────────────────────────────────────────────────────
# __file__ is the path to this script. os.path.dirname gets the folder it lives
# in. We store the database in the same folder as app.py.
DB_PATH = os.path.join(os.path.dirname(__file__), "scrib_d.db")

# ── Token limits per tier ─────────────────────────────────────────────────────
# One "token" = one word in the transcription output.
# ~200-250 words per handwritten page, so:
#   Free    (500)  ≈ 2 pages/day
#   Student (5000) ≈ 20 pages/day
#   Pro     (None) = unlimited
TIER_LIMITS = {
    "free":    500,
    "student": 5000,
    "pro":     None,   # None = unlimited
}

# How many bonus tokens a referrer earns per person they bring in (daily)
REFERRAL_BONUS_TOKENS = 250  # roughly 1 extra page per referral

# The secret owner code — loaded from .env so it's never in the source code.
# Whoever redeems this code gets is_admin=1 and is never limited.
OWNER_CODE = os.getenv("OWNER_CODE", "")

# Google OAuth 2.0 credentials — set these in .env
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5000/google/callback")
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]

# The maximum upload size Flask will accept — 10 MB should be plenty for a photo
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB

# File types we're willing to accept. We reject anything else before it hits the AI.
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

# Map file extensions to the MIME types Claude expects
MIME_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
}


# ── Database helpers ───────────────────────────────────────────────────────────

def get_db():
    """
    Open a connection to the SQLite database and return it.

    sqlite3.connect() creates the file automatically if it doesn't exist yet.
    row_factory = sqlite3.Row makes rows behave like dictionaries so we can
    access columns by name (e.g. row["email"]) instead of by index (row[1]).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Create the database tables if they don't already exist.

    This is called once when the app starts. The CREATE TABLE IF NOT EXISTS
    statement is safe to run every time — it only creates the table when it's
    missing, so existing data is never deleted.

    Table: users
      id              — auto-incrementing integer, the primary key
      email           — must be unique so two people can't share an email
      password_hash   — we NEVER store plain-text passwords; only the hash
      created_at      — ISO 8601 timestamp of when the account was made
      uploads_today   — how many transcriptions the user has done today
      last_upload_date— the date (YYYY-MM-DD) of the most recent upload,
                        used to know when to reset uploads_today back to 0
    """
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            email            TEXT UNIQUE NOT NULL,
            password_hash    TEXT NOT NULL,
            first_name       TEXT,
            last_name        TEXT,
            avatar           TEXT,
            created_at       TEXT,
            tier             TEXT DEFAULT 'free',  -- 'free', 'student', or 'pro'
            tokens_today     INTEGER DEFAULT 0,    -- words transcribed today
            last_token_date  TEXT,                 -- date of last transcription (YYYY-MM-DD)
            bonus_tokens     INTEGER DEFAULT 0,    -- extra daily tokens from referrals
            referral_code    TEXT UNIQUE,
            referred_by      INTEGER,
            is_admin         INTEGER DEFAULT 0     -- owner override: never limited
        )
    """)
    conn.commit()
    # Transcription history table — one row per transcription
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transcriptions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            text        TEXT NOT NULL,
            word_count  INTEGER DEFAULT 0,
            created_at  TEXT NOT NULL
        )
    """)
    conn.commit()

    # Migrate any columns missing from older database versions
    migrations = [
        "first_name TEXT", "last_name TEXT", "avatar TEXT",
        "tier TEXT DEFAULT 'free'",
        "tokens_today INTEGER DEFAULT 0",
        "last_token_date TEXT",
        "bonus_tokens INTEGER DEFAULT 0",
        "referral_code TEXT", "referred_by INTEGER",
        "is_admin INTEGER DEFAULT 0",
    ]
    for col_def in migrations:
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col_def}")
            conn.commit()
        except Exception:
            pass

    # Add share_token to transcriptions if it doesn't exist yet
    try:
        conn.execute("ALTER TABLE transcriptions ADD COLUMN share_token TEXT")
        conn.commit()
    except Exception:
        pass

    # Fix any users whose tier column is NULL (inserted before migration added the column)
    conn.execute("UPDATE users SET tier = 'free' WHERE tier IS NULL")
    conn.commit()

    # Add title column so users can rename transcriptions
    try:
        conn.execute("ALTER TABLE transcriptions ADD COLUMN title TEXT")
        conn.commit()
    except Exception:
        pass

    # Add Google OAuth token columns
    for col in ["google_access_token TEXT", "google_refresh_token TEXT", "google_token_expiry TEXT"]:
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col}")
            conn.commit()
        except Exception:
            pass

    # Notebooks — user-created folders to organise transcriptions
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notebooks (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            name       TEXT NOT NULL,
            color      TEXT DEFAULT '#c9a96e',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()

    # Many-to-many: which transcriptions belong to which notebook
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notebook_transcriptions (
            notebook_id      INTEGER NOT NULL,
            transcription_id INTEGER NOT NULL,
            PRIMARY KEY (notebook_id, transcription_id)
        )
    """)
    conn.commit()
    conn.close()


# Run init_db() immediately when the module loads so the table always exists
# before any request can come in.
init_db()


# ── Auth decorator ─────────────────────────────────────────────────────────────

def login_required(f):
    """
    A decorator that protects a route so only logged-in users can access it.

    A decorator is a function that wraps another function to add behaviour.
    Here, before the real route function runs, we check whether "user_id" is
    stored in the session cookie. If it isn't, the user isn't logged in, so
    we send them to the login page instead.

    Usage:
        @app.route("/some-protected-page")
        @login_required          ← add this line right before the function
        def some_page():
            ...
    """
    @wraps(f)  # preserves the original function's name and docstring
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            # POST requests are always fetch/API calls in this app, so return
            # JSON — otherwise the browser gets an HTML redirect it can't parse.
            if request.method != "GET":
                return jsonify({"error": "Not logged in."}), 401
            return redirect(url_for("landing"))
        return f(*args, **kwargs)
    return decorated


def allowed_file(filename: str) -> bool:
    """Return True if the filename has an extension we accept."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Routes ─────────────────────────────────────────────────────────────────────

# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route("/login")
def landing():
    """
    GET /login  (also the landing page for non-logged-in users)
    Shows the landing + login/signup page (login.html has both panels).
    """
    if session.get("user_id"):
        return redirect(url_for("index"))
    return render_template("login.html")

# Keep /login as an alias so old links still work


@app.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def login_post():
    """
    POST /login
    Expects a JSON body: { "email": "...", "password": "..." }

    We look the email up in the database. If found, we use Werkzeug's
    check_password_hash() to verify the password against the stored hash.
    On success we store the user's id and email in the session and tell
    the browser to redirect to the home page.

    Returns JSON so the front-end fetch() call can read the result:
      { "ok": true }          — success
      { "error": "..." }      — failure with a human-readable reason
    """
    data = request.get_json(silent=True)  # silent=True returns None on parse error

    # Make sure we actually received JSON with the fields we need
    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password are required."}), 400

    email    = data["email"].strip().lower()  # normalise so "User@Example.com" == "user@example.com"
    password = data["password"]

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    # check_password_hash() returns False if the hash doesn't match, or if user is None
    if not user or not check_password_hash(user["password_hash"], password):
        # We give the same vague error for both "no account" and "wrong password"
        # so an attacker can't tell which emails are registered.
        return jsonify({"error": "Incorrect email or password."}), 401

    # Store identifying info in the session. Flask encrypts this into a cookie
    # sent to the browser; it comes back with every future request.
    session["user_id"]    = user["id"]
    session["user_email"] = user["email"]

    return jsonify({"ok": True})


@app.route("/signup", methods=["POST"])
@limiter.limit("5 per minute")
def signup_post():
    """
    POST /signup
    Expects a JSON body: { "email": "...", "password": "...", "confirm": "..." }

    We validate the inputs, hash the password with Werkzeug, insert a new row
    into the users table, then auto-login the user exactly like /login does.

    Returns:
      { "ok": true }     — account created and logged in
      { "error": "..." } — validation or DB error
    """
    data = request.get_json(silent=True)

    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password are required."}), 400

    email      = data["email"].strip().lower()
    password   = data["password"]
    confirm    = data.get("confirm", "")
    first_name   = data.get("first_name", "").strip()
    last_name    = data.get("last_name", "").strip()
    referral_in  = data.get("referral_code", "").strip().upper()  # code they were given

    if not first_name or not last_name:
        return jsonify({"error": "Please enter your first and last name."}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    if password != confirm:
        return jsonify({"error": "Passwords do not match."}), 400

    password_hash = generate_password_hash(password, method="pbkdf2:sha256")
    created_at    = datetime.utcnow().isoformat()

    # Generate a unique 8-character referral code for this new user.
    # secrets.token_urlsafe gives a random URL-safe string; we take 6 chars and uppercase it.
    new_ref_code = secrets.token_urlsafe(6).upper()[:8]

    # Look up who referred this new user (if anyone)
    conn = get_db()
    referrer_id = None
    if referral_in:
        referrer = conn.execute(
            "SELECT id FROM users WHERE referral_code = ?", (referral_in,)
        ).fetchone()
        if referrer:
            referrer_id = referrer["id"]

    try:
        cursor = conn.execute(
            """INSERT INTO users
               (email, password_hash, first_name, last_name, created_at, referral_code, referred_by, tier)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'free')""",
            (email, password_hash, first_name, last_name, created_at, new_ref_code, referrer_id),
        )
        conn.commit()
        new_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "An account with that email already exists."}), 409

    # Reward the referrer with extra daily tokens for each person they bring in
    if referrer_id:
        conn.execute(
            "UPDATE users SET bonus_tokens = bonus_tokens + ? WHERE id = ?",
            (REFERRAL_BONUS_TOKENS, referrer_id),
        )
        conn.commit()

    conn.close()

    session["user_id"]    = new_id
    session["user_email"] = email

    return jsonify({"ok": True})


@app.route("/logout")
def logout():
    """
    GET /logout
    Wipe the session (which removes user_id and user_email) and send the
    user back to the login page.
    """
    session.clear()
    return redirect(url_for("landing"))


# ── App routes ─────────────────────────────────────────────────────────────────

def get_token_status(user):
    """
    Given a user row, return a dict with their token usage info for today.
    This is used by both the index route and the transcribe route.

      limit       — total daily token budget (None = unlimited)
      used        — tokens used today
      remaining   — tokens left today (None = unlimited)
    """
    today = date.today().isoformat()
    tier  = user["tier"] or "free"
    base_limit = TIER_LIMITS.get(tier)  # None for pro, undefined for dev

    if user["is_admin"] or tier == "dev" or base_limit is None:
        return {"limit": None, "used": 0, "remaining": None, "tier": tier}

    daily_limit = base_limit + (user["bonus_tokens"] or 0)
    used = user["tokens_today"] if user["last_token_date"] == today else 0
    return {
        "limit": daily_limit,
        "used": used,
        "remaining": max(0, daily_limit - used),
        "tier": tier,
    }


@app.route("/")
@login_required
def index():
    """Serve the main page, passing the logged-in user's info to the template."""
    conn = get_db()
    user = conn.execute(
        """SELECT first_name, last_name, email, avatar, referral_code,
                  bonus_tokens, tokens_today, last_token_date, tier, is_admin
           FROM users WHERE id = ?""",
        (session["user_id"],)
    ).fetchone()
    conn.close()

    # If the user row is gone (e.g. DB was reset), clear the session and redirect
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    status = get_token_status(user)

    return render_template(
        "index.html",
        user=user,
        tokens_remaining=status["remaining"],   # None = unlimited
        tokens_limit=status["limit"],
        tokens_used=status["used"],
        tier=status["tier"],
        referral_bonus_tokens=REFERRAL_BONUS_TOKENS,
        tier_limits=TIER_LIMITS,
    )


@app.route("/redeem", methods=["POST"])
@login_required
def redeem_code():
    """
    POST /redeem  { "code": "..." }
    Checks the submitted code against the OWNER_CODE in .env.
    If it matches, grants is_admin = 1 (unlimited uploads forever).
    """
    data = request.get_json(silent=True)
    code = (data or {}).get("code", "").strip()

    if not code:
        return jsonify({"error": "Please enter a code."}), 400

    if OWNER_CODE and code.upper() == OWNER_CODE.upper():
        conn = get_db()
        conn.execute("UPDATE users SET is_admin = 1, tier = 'dev' WHERE id = ?", (session["user_id"],))
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "message": "Unlimited uploads unlocked!"})

    return jsonify({"error": "That code isn't valid."}), 400


@app.route("/upgrade", methods=["POST"])
@login_required
def upgrade():
    """
    POST /upgrade  { "tier": "student" | "pro" }
    Placeholder for Stripe. When Stripe keys are in .env, create a Checkout
    Session here and return its URL. For now returns a coming-soon message.

    Each tier will need its own Stripe Price ID in .env:
      STRIPE_PRICE_STUDENT=price_...
      STRIPE_PRICE_PRO=price_...
    """
    data = request.get_json(silent=True) or {}
    tier = data.get("tier", "pro")
    if tier not in ("student", "pro"):
        return jsonify({"error": "Invalid tier."}), 400

    # TODO: uncomment when Stripe is set up:
    # import stripe
    # stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    # price_id = os.getenv(f"STRIPE_PRICE_{tier.upper()}")
    # checkout = stripe.checkout.Session.create(
    #     payment_method_types=["card"],
    #     line_items=[{"price": price_id, "quantity": 1}],
    #     mode="subscription",
    #     success_url=request.host_url + f"?upgraded={tier}",
    #     cancel_url=request.host_url,
    # )
    # return jsonify({"url": checkout.url})

    return jsonify({"error": "coming_soon", "message": "Payments coming soon — stay tuned!"}), 501


@app.route("/history")
@login_required
def history():
    """
    GET /history
    Returns the last 50 transcriptions for the logged-in user as JSON,
    newest first. Also returns which notebook(s) each item belongs to.
    The sidebar calls this with fetch() to populate itself.
    """
    conn = get_db()
    rows = conn.execute(
        """SELECT id, text, word_count, created_at, title
           FROM transcriptions WHERE user_id = ?
           ORDER BY id DESC LIMIT 50""",
        (session["user_id"],)
    ).fetchall()
    items = [dict(r) for r in rows]

    # Attach notebook membership so the frontend can show a badge
    if items:
        trans_ids = [i["id"] for i in items]
        placeholders = ",".join("?" * len(trans_ids))
        nb_rows = conn.execute(
            f"SELECT notebook_id, transcription_id FROM notebook_transcriptions"
            f" WHERE transcription_id IN ({placeholders})",
            trans_ids
        ).fetchall()
        nb_map = {}
        for nr in nb_rows:
            nb_map.setdefault(nr["transcription_id"], []).append(nr["notebook_id"])
        for item in items:
            item["notebook_ids"] = nb_map.get(item["id"], [])

    conn.close()
    return jsonify({"items": items})


def require_paid_tier():
    """Return a JSON error response if the user is on the free tier, else None."""
    conn = get_db()
    user = conn.execute("SELECT tier, is_admin FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    conn.close()
    if user and (user["is_admin"] or user["tier"] not in ("free", None)):
        return None
    return jsonify({"error": "upgrade_required", "message": "Notebooks are available on Student and Pro plans."}), 403


@app.route("/notebooks", methods=["GET"])
@login_required
def list_notebooks():
    err = require_paid_tier()
    if err: return err
    conn = get_db()
    rows = conn.execute(
        """SELECT n.id, n.name, n.color, n.created_at,
                  COUNT(nt.transcription_id) AS item_count
           FROM notebooks n
           LEFT JOIN notebook_transcriptions nt ON nt.notebook_id = n.id
           WHERE n.user_id = ?
           GROUP BY n.id
           ORDER BY n.id DESC""",
        (session["user_id"],)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/notebooks", methods=["POST"])
@login_required
def create_notebook():
    err = require_paid_tier()
    if err: return err
    data = request.get_json(silent=True) or {}
    name  = data.get("name", "").strip()
    color = data.get("color", "#c9a96e").strip()
    if not re.match(r'^#[0-9a-fA-F]{6}$', color):
        color = "#c9a96e"
    if not name:
        return jsonify({"error": "Notebook name is required."}), 400
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO notebooks (user_id, name, color, created_at) VALUES (?, ?, ?, ?)",
        (session["user_id"], name, color, datetime.utcnow().isoformat())
    )
    conn.commit()
    nb_id = cursor.lastrowid
    conn.close()
    return jsonify({"ok": True, "id": nb_id, "name": name, "color": color, "item_count": 0})


@app.route("/notebooks/<int:nb_id>", methods=["DELETE"])
@login_required
def delete_notebook(nb_id):
    """
    DELETE /notebooks/<id>
    Deletes the notebook and removes all its transcription assignments.
    The transcriptions themselves are NOT deleted.
    """
    conn = get_db()
    nb = conn.execute(
        "SELECT id FROM notebooks WHERE id = ? AND user_id = ?",
        (nb_id, session["user_id"])
    ).fetchone()
    if not nb:
        conn.close()
        return jsonify({"error": "Not found."}), 404
    conn.execute("DELETE FROM notebook_transcriptions WHERE notebook_id = ?", (nb_id,))
    conn.execute("DELETE FROM notebooks WHERE id = ?", (nb_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/notebooks/<int:nb_id>/items", methods=["GET"])
@login_required
def notebook_items(nb_id):
    """
    GET /notebooks/<id>/items
    Returns the transcriptions inside a notebook, newest first.
    """
    conn = get_db()
    nb = conn.execute(
        "SELECT id FROM notebooks WHERE id = ? AND user_id = ?",
        (nb_id, session["user_id"])
    ).fetchone()
    if not nb:
        conn.close()
        return jsonify({"error": "Not found."}), 404
    rows = conn.execute(
        """SELECT t.id, t.text, t.word_count, t.created_at
           FROM transcriptions t
           JOIN notebook_transcriptions nt ON nt.transcription_id = t.id
           WHERE nt.notebook_id = ?
           ORDER BY t.id DESC""",
        (nb_id,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/notebooks/<int:nb_id>/items", methods=["POST"])
@login_required
def add_to_notebook(nb_id):
    """
    POST /notebooks/<id>/items  { "transcription_id": 123 }
    Adds a transcription to a notebook. Safe to call twice (idempotent).
    """
    data = request.get_json(silent=True) or {}
    trans_id = data.get("transcription_id")
    if not trans_id:
        return jsonify({"error": "transcription_id required."}), 400
    conn = get_db()
    nb = conn.execute(
        "SELECT id FROM notebooks WHERE id = ? AND user_id = ?",
        (nb_id, session["user_id"])
    ).fetchone()
    if not nb:
        conn.close()
        return jsonify({"error": "Notebook not found."}), 404
    trans = conn.execute(
        "SELECT id FROM transcriptions WHERE id = ? AND user_id = ?",
        (trans_id, session["user_id"])
    ).fetchone()
    if not trans:
        conn.close()
        return jsonify({"error": "Transcription not found."}), 404
    try:
        conn.execute(
            "INSERT INTO notebook_transcriptions (notebook_id, transcription_id) VALUES (?, ?)",
            (nb_id, trans_id)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # already in notebook — that's fine
    conn.close()
    return jsonify({"ok": True})


@app.route("/notebooks/<int:nb_id>/items/<int:trans_id>", methods=["DELETE"])
@login_required
def remove_from_notebook(nb_id, trans_id):
    """
    DELETE /notebooks/<nb_id>/items/<trans_id>
    Removes a transcription from a notebook (doesn't delete the transcription itself).
    """
    conn = get_db()
    nb = conn.execute(
        "SELECT id FROM notebooks WHERE id = ? AND user_id = ?",
        (nb_id, session["user_id"])
    ).fetchone()
    if not nb:
        conn.close()
        return jsonify({"error": "Not found."}), 404
    conn.execute(
        "DELETE FROM notebook_transcriptions WHERE notebook_id = ? AND transcription_id = ?",
        (nb_id, trans_id)
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/transcriptions/<int:trans_id>/share", methods=["POST"])
@login_required
def share_transcription(trans_id):
    """
    POST /transcriptions/<id>/share
    Generates (or returns the existing) share token for a transcription.
    Only the owner of the transcription can call this.
    Returns { "url": "https://..." } with the public share link.
    """
    conn = get_db()
    row = conn.execute(
        "SELECT id, share_token FROM transcriptions WHERE id = ? AND user_id = ?",
        (trans_id, session["user_id"])
    ).fetchone()

    if not row:
        conn.close()
        return jsonify({"error": "Not found."}), 404

    token = row["share_token"]
    if not token:
        token = secrets.token_urlsafe(12)  # 16-char URL-safe string
        conn.execute(
            "UPDATE transcriptions SET share_token = ? WHERE id = ?",
            (token, trans_id)
        )
        conn.commit()
    conn.close()

    share_url = request.host_url.rstrip("/") + f"/s/{token}"
    return jsonify({"ok": True, "url": share_url})


@app.route("/s/<token>")
def view_shared(token):
    """
    GET /s/<token>
    Public page — no login required. Displays the shared transcription.
    """
    conn = get_db()
    row = conn.execute(
        """SELECT t.text, t.word_count, t.created_at,
                  u.first_name, u.last_name
           FROM transcriptions t
           JOIN users u ON u.id = t.user_id
           WHERE t.share_token = ?""",
        (token,)
    ).fetchone()
    conn.close()

    if not row:
        return "This link is invalid or has been removed.", 404

    return render_template("share.html", item=dict(row))


@app.route("/cancel-subscription", methods=["POST"])
@login_required
def cancel_subscription():
    """
    POST /cancel-subscription
    Downgrades the user to the free tier.
    When Stripe is set up, also cancel the Stripe subscription here so
    they aren't charged again after the current billing period ends.
    """
    user_id = session["user_id"]
    conn = get_db()
    user = conn.execute("SELECT tier FROM users WHERE id = ?", (user_id,)).fetchone()

    if user["tier"] == "free":
        conn.close()
        return jsonify({"error": "You're already on the free plan."}), 400

    # TODO: stripe.Subscription.delete(user["stripe_subscription_id"])
    conn.execute("UPDATE users SET tier = 'free' WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

    return jsonify({"ok": True, "message": "Subscription cancelled. You've been moved to the free plan."})


@app.route("/profile/upload", methods=["POST"])
@login_required
def upload_avatar():
    """
    POST /profile/upload
    Accepts a profile picture upload, saves it to static/avatars/,
    and stores the filename in the database.
    """
    if "avatar" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files["avatar"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file."}), 400

    if PIL_AVAILABLE:
        try:
            img = PilImage.open(file.stream)
            img.verify()
            file.stream.seek(0)
        except Exception:
            return jsonify({"error": "Invalid or corrupted image."}), 415

    # Save into static/avatars/ using the user's id as the filename
    # so each upload overwrites the previous one cleanly.
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"avatar_{session['user_id']}.{ext}"
    avatars_dir = os.path.join(os.path.dirname(__file__), "static", "avatars")
    os.makedirs(avatars_dir, exist_ok=True)
    file.save(os.path.join(avatars_dir, filename))

    conn = get_db()
    conn.execute("UPDATE users SET avatar = ? WHERE id = ?", (filename, session["user_id"]))
    conn.commit()
    conn.close()

    return jsonify({"ok": True, "avatar": filename})


@app.route("/transcribe", methods=["POST"])
@login_required  # ← only logged-in users can transcribe
def transcribe():
    """
    POST /transcribe
    Expects a multipart form upload with a field named "image".
    Returns JSON: { "transcription": "..." } on success
                  { "error": "..." }          on failure

    After a successful transcription we update the user's upload count for
    today. If their last upload was on a previous day we reset the counter
    to 1 (this fresh day's first upload). This tracking is the groundwork
    for enforcing FREE_DAILY_LIMIT in a future version.
    """

    # ── 0. Check the user's daily token limit ──────────────────────────────
    user_id   = session["user_id"]
    today_str = date.today().isoformat()

    conn = get_db()
    user = conn.execute(
        "SELECT tokens_today, last_token_date, bonus_tokens, tier, is_admin FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()

    status = get_token_status(user)
    if status["remaining"] is not None and status["remaining"] <= 0:
        return jsonify({
            "error": "limit_reached",
            "message": f"You've used all {status['limit']} tokens for today. Upgrade for more, or share your referral code to earn bonus tokens."
        }), 429

    # ── 1. Validate the upload(s) ───────────────────────────────────────────
    # Accept either a list of files (multi-page: images[]) or a single file (image)

    files = request.files.getlist("images[]")
    if not files or files[0].filename == "":
        # Fall back to legacy single-image field
        single = request.files.get("image")
        if not single or single.filename == "":
            return jsonify({"error": "No image field in the request."}), 400
        files = [single]

    for f in files:
        if not allowed_file(f.filename):
            return jsonify({"error": f"Unsupported file type: {f.filename}. Use PNG, JPG, WEBP, or GIF."}), 415
        if PIL_AVAILABLE:
            try:
                img = PilImage.open(f.stream)
                img.verify()
                f.stream.seek(0)
            except Exception:
                return jsonify({"error": f"Invalid or corrupted image: {f.filename}"}), 415

    # ── 2. Read every image and convert to base64 ───────────────────────────

    image_blocks = []
    for f in files:
        extension = f.filename.rsplit(".", 1)[1].lower()
        mime_type = MIME_TYPES[extension]
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")
        image_blocks.append({
            "type": "image",
            "source": {"type": "base64", "media_type": mime_type, "data": image_data},
        })

    # ── 3. Call the Anthropic API ───────────────────────────────────────────

    page_note = f" There are {len(files)} pages — transcribe them in order, separating pages with '---'." if len(files) > 1 else ""
    prompt_text = (
        "Please transcribe all of the handwritten text in this image."
        + page_note
        + " Output only the transcribed text — no explanations, no formatting labels, "
        "no extra commentary. If you cannot read a word clearly, indicate it with [illegible]."
    )

    client = anthropic.Anthropic()

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": image_blocks + [{"type": "text", "text": prompt_text}],
                }
            ],
        )
    except anthropic.AuthenticationError:
        return jsonify({"error": "Invalid API key — check your ANTHROPIC_API_KEY in .env"}), 500
    except anthropic.APIError as e:
        return jsonify({"error": f"Claude API error: {e}"}), 500

    # The response is a list of content blocks; we want the first text block.
    transcription = message.content[0].text

    # ── 4. Count words and update the user's token balance ─────────────────
    # Each word in the transcription costs one token.
    word_count = len(transcription.split())

    # Use BEGIN IMMEDIATE to hold a write lock while we re-check the limit
    # and apply the update atomically, preventing race conditions.
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("BEGIN IMMEDIATE")
    user = conn.execute(
        "SELECT tokens_today, last_token_date, bonus_tokens, tier, is_admin FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()

    fresh_status = get_token_status(user)
    if fresh_status["remaining"] is not None and fresh_status["remaining"] < word_count:
        conn.rollback()
        conn.close()
        return jsonify({
            "error": "limit_reached",
            "message": f"You've used all {fresh_status['limit']} tokens for today. Upgrade for more, or share your referral code to earn bonus tokens."
        }), 429

    if user["last_token_date"] == today_str:
        new_total = user["tokens_today"] + word_count
    else:
        new_total = word_count  # new day — reset

    conn.execute(
        "UPDATE users SET tokens_today = ?, last_token_date = ? WHERE id = ?",
        (new_total, today_str, user_id),
    )
    # Save to history
    cursor = conn.execute(
        "INSERT INTO transcriptions (user_id, text, word_count, created_at) VALUES (?, ?, ?, ?)",
        (user_id, transcription, word_count, datetime.utcnow().isoformat()),
    )
    transcription_id = cursor.lastrowid
    conn.commit()

    # Recalculate remaining for the frontend counter
    updated_user = conn.execute(
        "SELECT tokens_today, last_token_date, bonus_tokens, tier, is_admin FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()

    new_status = get_token_status(updated_user)

    return jsonify({
        "transcription": transcription,
        "transcription_id": transcription_id,
        "tokens_used": word_count,
        "tokens_remaining": new_status["remaining"],  # None = unlimited
        "tokens_limit": new_status["limit"],
    })


@app.route("/cleanup", methods=["POST"])
@login_required
def cleanup_text():
    """
    POST /cleanup  { "text": "..." }
    Sends the transcribed text back to Claude to fix grammar, spelling,
    punctuation and formatting while keeping the meaning identical.
    """
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided."}), 400

    client = anthropic.Anthropic()
    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": (
                    "Clean up the following transcribed handwriting. Fix grammar, spelling, "
                    "punctuation and spacing. Keep the exact same meaning and content — "
                    "just make it polished and readable. Output only the cleaned text.\n\n"
                    + text
                ),
            }],
        )
    except anthropic.APIError as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"text": message.content[0].text})


@app.route("/transcriptions/<int:trans_id>/rename", methods=["POST"])
@login_required
def rename_transcription(trans_id):
    """
    POST /transcriptions/<id>/rename  { "title": "My custom name" }
    Sets a display title on a transcription (shown in the history sidebar).
    """
    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Title required."}), 400
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM transcriptions WHERE id = ? AND user_id = ?",
        (trans_id, session["user_id"])
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Not found."}), 404
    conn.execute("UPDATE transcriptions SET title = ? WHERE id = ?", (title, trans_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# ── Download routes ───────────────────────────────────────────────────────────

@app.route("/transcriptions/<int:trans_id>/download/txt")
@login_required
def download_txt(trans_id):
    """
    GET /transcriptions/<id>/download/txt
    Sends the transcription as a plain-text file download.
    send_file() tells the browser to download rather than display the content.
    """
    conn = get_db()
    row = conn.execute(
        "SELECT text, created_at FROM transcriptions WHERE id = ? AND user_id = ?",
        (trans_id, session["user_id"])
    ).fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Not found."}), 404

    # Wrap the text in a BytesIO buffer so we don't need to write a temp file
    buf = io.BytesIO(row["text"].encode("utf-8"))
    buf.seek(0)

    # Build a filename from the date, e.g. "note-cloud-2024-03-15.txt"
    date_part = (row["created_at"] or "")[:10]  # grab YYYY-MM-DD
    filename = f"note-cloud-{date_part}.txt"

    return send_file(buf, mimetype="text/plain", as_attachment=True, download_name=filename)


@app.route("/transcriptions/<int:trans_id>/download/docx")
@login_required
def download_docx(trans_id):
    """
    GET /transcriptions/<id>/download/docx
    Builds a .docx file in memory using python-docx and sends it as a download.
    python-docx lets us create Word documents without needing Microsoft Word installed.
    """
    conn = get_db()
    row = conn.execute(
        "SELECT text, created_at FROM transcriptions WHERE id = ? AND user_id = ?",
        (trans_id, session["user_id"])
    ).fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Not found."}), 404

    # Build the Word document
    doc = Document()

    # Title
    title = doc.add_heading("Transcription", level=1)
    title.runs[0].font.size = Pt(16)

    # Date subtitle
    date_part = (row["created_at"] or "")[:10]
    doc.add_paragraph(f"Date: {date_part}").runs[0].italic = True

    doc.add_paragraph("")  # blank line spacer

    # The transcription text — split into paragraphs on blank lines
    for para in row["text"].split("\n\n"):
        p = para.strip()
        if p:
            doc.add_paragraph(p)

    # Save the document to an in-memory buffer
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    date_part = (row["created_at"] or "")[:10]
    filename = f"note-cloud-{date_part}.docx"

    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=filename,
    )


# ── Account stats & export ────────────────────────────────────────────────────

@app.route("/account/stats")
@login_required
def account_stats():
    """GET /account/stats — total transcription count and word count for the user."""
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) AS count, COALESCE(SUM(word_count), 0) AS words FROM transcriptions WHERE user_id = ?",
        (session["user_id"],)
    ).fetchone()
    user = conn.execute(
        "SELECT created_at FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()
    conn.close()
    return jsonify({
        "transcriptions": row["count"],
        "words": row["words"],
        "member_since": (user["created_at"] or "")[:10],
    })


@app.route("/account/export")
@login_required
def account_export():
    """GET /account/export — download all transcriptions as a JSON file."""
    import json as _json
    conn = get_db()
    rows = conn.execute(
        "SELECT id, title, text, word_count, created_at FROM transcriptions WHERE user_id = ? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()
    conn.close()
    data = {"exported_at": datetime.utcnow().isoformat(), "transcriptions": [dict(r) for r in rows]}
    buf = io.BytesIO(_json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"))
    buf.seek(0)
    return send_file(buf, mimetype="application/json", as_attachment=True,
                     download_name="note-cloud-export.json")


# ── Settings routes ───────────────────────────────────────────────────────────

@app.route("/profile/update", methods=["POST"])
@login_required
def profile_update():
    """
    POST /profile/update  { "first_name": "...", "last_name": "...", "email": "..." }
    Updates the user's display name and email address.
    """
    data = request.get_json(silent=True) or {}
    first_name = data.get("first_name", "").strip()
    last_name  = data.get("last_name",  "").strip()
    email      = data.get("email",      "").strip().lower()

    if not first_name or not last_name:
        return jsonify({"error": "First and last name are required."}), 400
    if not email or "@" not in email:
        return jsonify({"error": "A valid email address is required."}), 400

    conn = get_db()
    # Check if the new email is already taken by a different account
    existing = conn.execute(
        "SELECT id FROM users WHERE email = ? AND id != ?",
        (email, session["user_id"])
    ).fetchone()
    if existing:
        conn.close()
        return jsonify({"error": "That email is already in use by another account."}), 409

    conn.execute(
        "UPDATE users SET first_name = ?, last_name = ?, email = ? WHERE id = ?",
        (first_name, last_name, email, session["user_id"])
    )
    conn.commit()
    conn.close()

    session["user_email"] = email
    return jsonify({"ok": True, "first_name": first_name, "last_name": last_name, "email": email})


@app.route("/profile/password", methods=["POST"])
@login_required
def profile_password():
    """
    POST /profile/password  { "current": "...", "new_password": "...", "confirm": "..." }
    Changes the user's password after verifying their current one.
    """
    data = request.get_json(silent=True) or {}
    current      = data.get("current",      "")
    new_password = data.get("new_password", "")
    confirm      = data.get("confirm",      "")

    if not current or not new_password:
        return jsonify({"error": "Current and new password are required."}), 400
    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters."}), 400
    if new_password != confirm:
        return jsonify({"error": "New passwords do not match."}), 400

    conn = get_db()
    user = conn.execute("SELECT password_hash FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    if not user or not check_password_hash(user["password_hash"], current):
        conn.close()
        return jsonify({"error": "Current password is incorrect."}), 401

    new_hash = generate_password_hash(new_password, method="pbkdf2:sha256")
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, session["user_id"]))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/account/delete", methods=["POST"])
@login_required
def account_delete():
    """
    POST /account/delete  { "password": "..." }
    Permanently deletes the account and all associated data after password confirmation.
    """
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")

    if not password:
        return jsonify({"error": "Password confirmation is required."}), 400

    conn = get_db()
    user = conn.execute("SELECT password_hash FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    if not user or not check_password_hash(user["password_hash"], password):
        conn.close()
        return jsonify({"error": "Incorrect password."}), 401

    uid = session["user_id"]
    # Delete all transcriptions, notebook memberships, and notebooks first
    trans_ids = [r["id"] for r in conn.execute("SELECT id FROM transcriptions WHERE user_id = ?", (uid,)).fetchall()]
    if trans_ids:
        placeholders = ",".join("?" * len(trans_ids))
        conn.execute(f"DELETE FROM notebook_transcriptions WHERE transcription_id IN ({placeholders})", trans_ids)
    conn.execute("DELETE FROM transcriptions WHERE user_id = ?", (uid,))
    conn.execute("DELETE FROM notebook_transcriptions WHERE notebook_id IN (SELECT id FROM notebooks WHERE user_id = ?)", (uid,))
    conn.execute("DELETE FROM notebooks WHERE user_id = ?", (uid,))
    conn.execute("DELETE FROM users WHERE id = ?", (uid,))
    conn.commit()
    conn.close()

    session.clear()
    return jsonify({"ok": True})


# ── Google Docs integration ───────────────────────────────────────────────────

def _google_flow():
    """Build a google_auth_oauthlib Flow from env config."""
    return Flow.from_client_config(
        {"web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [GOOGLE_REDIRECT_URI],
        }},
        scopes=GOOGLE_SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )


@app.route("/google/auth")
@login_required
def google_auth():
    """Redirect the user to Google's OAuth consent screen."""
    if not GOOGLE_LIBS_AVAILABLE or not GOOGLE_CLIENT_ID:
        return "Google integration not configured — add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env", 503
    flow = _google_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    session["google_oauth_state"] = state
    return redirect(auth_url)


@app.route("/google/callback")
@login_required
def google_callback():
    """Handle the OAuth callback, store tokens, and redirect back to the app."""
    if not GOOGLE_LIBS_AVAILABLE or not GOOGLE_CLIENT_ID:
        return redirect("/?google_error=not_configured")

    state = session.pop("google_oauth_state", None)
    if not state or request.args.get("state") != state:
        return redirect("/?google_error=invalid_state")

    if "error" in request.args:
        return redirect("/?google_error=access_denied")

    flow = _google_flow()
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials

    conn = get_db()
    conn.execute(
        "UPDATE users SET google_access_token=?, google_refresh_token=?, google_token_expiry=? WHERE id=?",
        (
            creds.token,
            creds.refresh_token,
            creds.expiry.isoformat() if creds.expiry else None,
            session["user_id"],
        ),
    )
    conn.commit()
    conn.close()
    return redirect("/?google_connected=1")


@app.route("/google/status")
@login_required
def google_status():
    """Return whether the user has connected their Google account."""
    conn = get_db()
    user = conn.execute(
        "SELECT google_access_token FROM users WHERE id=?", (session["user_id"],)
    ).fetchone()
    conn.close()
    return jsonify({"connected": bool(user and user["google_access_token"])})


@app.route("/google/disconnect", methods=["POST"])
@login_required
def google_disconnect():
    """Remove stored Google tokens for the user."""
    conn = get_db()
    conn.execute(
        "UPDATE users SET google_access_token=NULL, google_refresh_token=NULL, google_token_expiry=NULL WHERE id=?",
        (session["user_id"],),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/transcriptions/<int:trans_id>/export/gdocs", methods=["POST"])
@login_required
def export_to_gdocs(trans_id):
    """Create a new Google Doc containing the transcription text."""
    if not GOOGLE_LIBS_AVAILABLE or not GOOGLE_CLIENT_ID:
        return jsonify({"error": "Google integration not configured."}), 503

    conn = get_db()
    row = conn.execute(
        "SELECT text, title, created_at FROM transcriptions WHERE id=? AND user_id=?",
        (trans_id, session["user_id"]),
    ).fetchone()
    user = conn.execute(
        "SELECT google_access_token, google_refresh_token, google_token_expiry FROM users WHERE id=?",
        (session["user_id"],),
    ).fetchone()

    if not row:
        conn.close()
        return jsonify({"error": "Not found."}), 404

    if not user or not user["google_access_token"]:
        conn.close()
        return jsonify({"error": "google_not_connected"}), 401

    # Build credentials object
    expiry = None
    if user["google_token_expiry"]:
        try:
            expiry = datetime.fromisoformat(user["google_token_expiry"])
        except Exception:
            pass

    creds = Credentials(
        token=user["google_access_token"],
        refresh_token=user["google_refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=GOOGLE_SCOPES,
        expiry=expiry,
    )

    # Refresh token if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(GoogleRequest())
            conn.execute(
                "UPDATE users SET google_access_token=?, google_token_expiry=? WHERE id=?",
                (creds.token, creds.expiry.isoformat() if creds.expiry else None, session["user_id"]),
            )
            conn.commit()
        except Exception:
            conn.close()
            return jsonify({"error": "google_not_connected"}), 401

    conn.close()

    try:
        docs = google_build("docs", "v1", credentials=creds)
        doc_title = row["title"] or f"Transcription — {(row['created_at'] or '')[:10]}"
        doc = docs.documents().create(body={"title": doc_title}).execute()
        doc_id = doc["documentId"]

        text = (row["text"] or "").strip()
        if text:
            docs.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": [{"insertText": {"location": {"index": 1}, "text": text}}]},
            ).execute()

        return jsonify({"ok": True, "url": f"https://docs.google.com/document/d/{doc_id}/edit"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # debug=True gives helpful error pages and auto-reloads when you edit the code.
    # Never use debug=True in a real production deployment.
    app.run(debug=True, port=5000)
