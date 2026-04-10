# Note-Cloud — Architecture

## Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend | Python / Flask | Simple, minimal boilerplate |
| Database | SQLite (file-based) | No separate server needed; fine for this scale |
| AI | Anthropic API (`claude-sonnet-4-5`) | Best-in-class handwriting/vision understanding |
| Frontend | Vanilla HTML + CSS + JS (no framework) | No build step, easy to read and modify |
| Password hashing | Werkzeug `pbkdf2:sha256` | Built into Flask's dependency, secure default |
| Word documents | `python-docx` | Server-side .docx generation without MS Word |

---

## File structure

```
scrib-d/
├── app.py                  # All backend logic (Flask routes, DB, API calls)
├── templates/
│   ├── index.html          # Main app (all CSS and JS inline, single file)
│   ├── login.html          # Landing / login / signup page
│   └── share.html          # Public shared transcription view (no login)
├── static/
│   └── avatars/            # User profile photos (named avatar_<user_id>.<ext>)
├── scrib_d.db              # SQLite database (auto-created on first run)
├── .env                    # Secret keys — never committed to git
├── requirements.txt        # Python dependencies
└── venv/                   # Virtual environment
```

---

## Database schema

### `users`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| email | TEXT UNIQUE | Lowercased on write |
| password_hash | TEXT | pbkdf2:sha256, never plain text |
| first_name, last_name | TEXT | |
| avatar | TEXT | Filename in static/avatars/ |
| tier | TEXT | `free`, `student`, `pro`, `dev` |
| tokens_today | INTEGER | Resets when date changes |
| last_token_date | TEXT | YYYY-MM-DD, used to detect new day |
| bonus_tokens | INTEGER | Earned via referrals (+250 per referral) |
| referral_code | TEXT UNIQUE | 8-char uppercase code |
| referred_by | INTEGER | FK → users.id |
| is_admin | INTEGER | 1 = unlimited, set by owner code |

### `transcriptions`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| user_id | INTEGER | FK → users.id |
| text | TEXT | Full transcription output |
| word_count | INTEGER | Cached on write |
| created_at | TEXT | ISO 8601 UTC timestamp |
| share_token | TEXT | Unique token for public share link; null if not shared |

### `notebooks`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| user_id | INTEGER | FK → users.id |
| name | TEXT | User-defined |
| color | TEXT | Hex color (6 presets in UI) |
| created_at | TEXT | ISO 8601 UTC timestamp |

### `notebook_transcriptions`
| Column | Type | Notes |
|--------|------|-------|
| notebook_id | INTEGER | FK → notebooks.id, composite PK |
| transcription_id | INTEGER | FK → transcriptions.id, composite PK |

Many-to-many: a transcription can be in multiple notebooks.

---

## Key backend decisions

**Token counting** — tokens = words in the output (not Anthropic API tokens). Simpler to explain to users and cheap to compute with `len(text.split())`.

**Daily reset** — instead of a cron job, we compare `last_token_date` to `date.today()` on every request. If the date changed, we treat `tokens_today` as 0. Zero infrastructure overhead.

**Image handling** — images are base64-encoded in memory and sent directly to the Anthropic API. They are never written to disk, keeping storage requirements near zero.

**Downloads** — `.txt` and `.docx` files are built in-memory (`io.BytesIO`) and streamed to the browser with `send_file()`. No temp files on disk.

**Share links** — `secrets.token_urlsafe(12)` generates a 16-char URL-safe token stored in the DB. The `/s/<token>` route is public (no `@login_required`).

**DB migrations** — handled with a try/except `ALTER TABLE ADD COLUMN` loop in `init_db()`. Runs on every startup; safe to run repeatedly since SQLite raises an error (caught and ignored) if the column already exists.

---

## Key frontend decisions

**Single-file templates** — all CSS and JS live inline in `index.html`. Avoids needing a build system; easy to work with at this project size.

**No framework** — plain `fetch()` calls and DOM manipulation. Every line is readable without knowing React/Vue/etc.

**Drag and drop** — uses the HTML5 native drag API (`draggable`, `dragstart`, `dragover`, `drop`). When a drag starts, the notebooks section auto-opens so drop targets are visible.

**Theme** — dark by default, toggled with a single `body.light` class. CSS custom properties (`--bg`, `--text`, `--accent`, etc.) handle all the color switching.

**Token bar** — rendered server-side by Jinja on page load, then updated client-side by JS after each transcription (so the count stays live without a page refresh).
