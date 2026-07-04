# Commit Guide

> Open in **Markdown Preview** (VS Code: ⌘K V) to get the click-to-expand rows. In the raw editor the `<details>` tags show as text — that's normal.

## 6/23 — Banglore, India

<details><summary><strong>2:12AM IST</strong> &nbsp;·&nbsp; <code>564263e</code> &nbsp; Fix CSRF + Remove Logo: INITIAL WORKING</summary>

- SESSION_COOKIE_SECURE now only applies in production (was blocking sessions over HTTP on localhost)
- Removed the cloud/pencil SVG logo from the landing panel

</details>

<details><summary><strong>3:31AM IST</strong> &nbsp;·&nbsp; <code>76a8f4b</code> &nbsp; Ticker Fix + "About Section" Redesign</summary>

- Fixed ticker vertical clipping with proper padding
- Redesigned about section: gradient heading, quote block with accent border, avatar footer card with name + signature

</details>

<details><summary><strong>3:38AM IST</strong> &nbsp;·&nbsp; <code>1a57ada</code> &nbsp; Card Pop + Remove Magnetic Button</summary>

- Replaced 3D card tilt with a clean translateY + scale pop on hover
- Amplified card glow on hover; stronger, more visible gradient border
- Removed the magnetic button effect and particle burst from Get Started

</details>

<details><summary><strong>3:46AM IST</strong> &nbsp;·&nbsp; <code>a94d48b</code> &nbsp; Fix Layout: Adjust Spacing, Position Override</summary>

- Removed a broad `body > *` rule that was overriding position:fixed on the sidebar/overlay
- Hid the duplicate header logo/tagline (the fixed logo handles branding)
- Increased spacing between logo, token bar, and upload zone

</details>

<details><summary><strong>3:59AM IST</strong> &nbsp;·&nbsp; <code>a42a656</code> &nbsp; Remove Interstitial Ads</summary>

- Stripped the interstitial ad markup/logic from index.html (−88 lines)

</details>

<details><summary><strong>4:18AM IST</strong> &nbsp;·&nbsp; <code>8363f54</code> &nbsp; Glass Logo, Pencil N SVG, Notecloud Text</summary>

- Reworked the header logo into a glass button with a pencil-N SVG (new static/nc-logo.svg) and "NoteCloud" text

</details>

<details><summary><strong>6:25AM IST</strong> &nbsp;·&nbsp; <code>8dc9c4d</code> &nbsp; New Theme, Expand Globe, Remove Logo Main</summary>

- Globe canvas is now fixed full-screen, covering both panels
- Removed the site-logo element, its CSS, and the scroll-shrink JS from index.html

</details>

<details><summary><strong>6:31AM IST</strong> &nbsp;·&nbsp; <code>7188bdf</code> &nbsp; Add Google OAuth Login Flow</summary>

- New /auth/google and /auth/google/callback routes for authentication
- Auto-creates an account on first Google sign-in; logs in existing accounts matched by email
- Google button redirects to OAuth instead of showing a toast; error params surface on the login page

</details>

## 6/26 — Banglore, India

<details><summary><strong>2:11PM IST</strong> &nbsp;·&nbsp; <code>fac1b17</code> &nbsp; New User Interface</summary>

- Full dark-luxury landing redesign: near-black warm background, gold palette, spring-physics custom cursor, magnetic CTA, globe with mouse-parallax tilt, floating gold particles, animated gradient-border auth card with 3D tilt, shimmer buttons, scroll-pausing ticker, staggered entrances
- Main app: matching custom cursor + trailing ring, radial mouse glow, magnetic transcribe button, enhanced drop zone with double pulse-ring on drag-over, staggered page-load entrance

</details>

<details><summary><strong>2:23PM IST</strong> &nbsp;·&nbsp; <code>ec7da37</code> &nbsp; Pencil Scroll Animation?</summary>

- A gold line draws itself down the left side as you scroll, with a pencil emoji riding the tip (SVG stroke-dashoffset tied to scroll progress)
- Pencil jiggles while scrolling, goes idle when stopped; hides on the auth panel and restores on back

</details>

## 6/27 — Banglore, India

<details><summary><strong>3:54PM IST</strong> &nbsp;·&nbsp; <code>4298c54</code> &nbsp; Polish UI</summary>

- Fixed the dark/light toggle (body:not(.light) variable overrides); passes theme param to the transcription page so it opens in matching mode
- Replaced the pencil animation with a centered irregular sine wave that draws on scroll; added the pastel-yellow background explosion when the wave finishes
- Removed the cursor glow; hide the dot cursor over text inputs; card scale instead of 3D tilt; ticker centering fix
- Per-item delete via a three-dots menu; removed click-to-paste and drag-handle dots; Clear-all colour fix
- Added DELETE /transcriptions/<id> route with notebook cascade

</details>

<details><summary><strong>3:56PM IST</strong> &nbsp;·&nbsp; <code>040dac7</code> &nbsp; Fix Transcription Page Topbar</summary>

- Replaced the hardcoded light topbar background with var(--clear-bg) and added --clear-bg to both dark and light overrides

</details>

<details><summary><strong>4:07PM IST</strong> &nbsp;·&nbsp; <code>aa5593f</code> &nbsp; Explosion Landing, Perf Improvments</summary>

- Singleton Anthropic client (no re-init per request); DB indexes on transcriptions(user_id), users(email), notebooks(user_id)
- Switched body:not(.light) to body.dark to avoid negation-selector recalc
- Pause the globe and particle rAF loops when the tab is hidden
- bg-explode uses a CSS transition so it reverses on scroll up (fast retract, slow expand)

</details>

<details><summary><strong>4:14PM IST</strong> &nbsp;·&nbsp; <code>eb488b0</code> &nbsp; Scroll Driven Explosion</summary>

- Explosion circle grows 0% → 150% as scroll goes 10% → 85%, fully covering the page by the time the about section is in view; shrinks proportionally on scroll up

</details>

## 6/28 — Banglore, India

<details><summary><strong>8:33AM IST</strong> &nbsp;·&nbsp; <code>b63da80</code> &nbsp; Notebook Fixes</summary>

- Name prompt after each transcription (save or skip); rename option in the ⋯ dropdown (inline edit); add-to-notebook in ⋯ with a live picker
- Sidebar resize handle on the right edge (220–560px, persisted to localStorage)
- Inline script applies the dark/light class before paint to prevent a flash
- Notebooks section auto-expands when the sidebar opens; fixed the + New button opening a hidden form

</details>

<details><summary><strong>8:41AM IST</strong> &nbsp;·&nbsp; <code>d7e62f9</code> &nbsp; "Why" Section Wrapped in White Card</summary>

- The about section now has a fixed white background and hardcoded dark text so it stays legible at any point during the explosion transition

</details>

<details><summary><strong>9:10AM IST</strong> &nbsp;·&nbsp; <code>6b25038</code> &nbsp; Sin Wave to Coil</summary>

- Replaced the narrow vertical wiggle with a full-width self-crossing coil (right arcs descend, left loop back up) so it reads as a spring; single continuous path drawn top-to-bottom on scroll

</details>

<details><summary><strong>9:30AM IST</strong> &nbsp;·&nbsp; <code>2435100</code> &nbsp; Lines Connection to Coil</summary>

- Added a 20-unit line above the coil (M200,-10) and a 90-unit line below (L200,370) to connect the scroll hint down to the white about card; adjusted viewBox and container height

</details>

<details><summary><strong>10:00AM IST</strong> &nbsp;·&nbsp; <code>a3c7150</code> &nbsp; Line Flows as One Continuous Liquid</summary>

- One connected gold stroke: top line → coil → bottom line → a rounded-rect frame traced around the about card
- Frame is two symmetric halves that pour down each side and meet at the bottom; path is computed in JS from the card's measured size and rebuilt on resize
- Whole stroke driven by scroll progress (coil 0–82%, frame 82–100%)

</details>

<details><summary><strong>10:14AM IST</strong> &nbsp;·&nbsp; <code>f645475</code> &nbsp; Border for Scroll</summary>

- Wrapped the "scroll" word in a constant gold border and lengthened the coil's top line
- Toggles the text to dark the moment the explosion circle's edge actually reaches the word (radius-vs-distance check) instead of at a fixed threshold

</details>

<details><summary><strong>11:23AM IST</strong> &nbsp;·&nbsp; <code>f15f5e3</code> &nbsp; Magnetic Globe Cursor Effect + Remove Custom Cursor</summary>

- Globe dots get pushed away from the cursor in screen space with a soft squared falloff, snapping back as it leaves
- Removed the custom gold dot cursor (CSS, element, JS loop) and restored native cursors

</details>

<details><summary><strong>11:28AM IST</strong> &nbsp;·&nbsp; <code>f96e716</code> &nbsp; Login Page Small Changes</summary>

- Replaced the "scroll" outline with a solid gold pill (dark bold text, soft glow), centered via translateX with left padding to offset letter-spacing
- Removed the now-redundant .lit darkening logic and unused hint var

</details>

<details><summary><strong>11:54AM IST</strong> &nbsp;·&nbsp; <code>049419f</code> &nbsp; Remove Glow</summary>

- login: ticker no longer stops scrolling when hovered; removed the gold glow box-shadow on the Start transcribing button
- index: removed the custom dot cursor and restored native cursors with pointer on interactive elements; kept the ambient mouse glow

</details>

<details><summary><strong>9:24PM IST</strong> &nbsp;·&nbsp; <code>2bc28d8</code> &nbsp; Google Login Working, PKCE Fix, Python 3.9 Compatibility, Row-Click Navigation</summary>

- Google OAuth login with PKCE; set OAUTHLIB_INSECURE_TRANSPORT for local dev
- Fixed the scrypt error on Python 3.9 by using pbkdf2:sha256; removed a stray `import ref`
- Redirect URIs use 127.0.0.1 to match the Google Cloud config
- Row-click navigation to the transcription page + roast shake on the transcribe button

</details>

## 7/2 — Banglore, India

<details><summary><strong>9:24AM IST</strong> &nbsp;·&nbsp; <code>8b87fc2</code> &nbsp; Major performance pass + Google login, pricing table, settings fixes</summary>

**Performance:**
- gzip all text responses (login 60KB → 15.6KB); 30-day static caching; favicon wired to the logo (kills the /favicon.ico 404)
- SQLite WAL mode + per-connection pragmas (synchronous=NORMAL, temp_store, cache_size, busy_timeout)
- Globe canvas: hoisted trig out of the per-dot loop (14,400 → 6 calls/frame), reused the projection buffer, capped to 30fps
- Particle loop: 30fps cap, no per-frame allocation
- Pause the background orbs while any overlay is open so the backdrop-blur caches → modals open instantly
- Modal blur 18px → 6px with faster transitions; sidebar/dropdown transitions tightened
- Paused onboarding's 6 infinite animations when closed (were running forever off-screen)
- History list render batched into a DocumentFragment (one reflow instead of 50)
- Orb blur 100px → 50px, ambient blob blur 80px → 48px (redundant over radial gradients)
- Magnetic button caches its rect on mouseenter instead of a per-mousemove layout read
- Mouse glow idles out when settled; scroll handlers rAF-throttled; reveals via IntersectionObserver

**Features/fixes:**
- Google OAuth login with PKCE; pbkdf2 hash (Python 3.9 scrypt fix)
- Pricing table on the landing page; tier feature table updated (pages/upload, Sheets, Calendar)
- Fixed the settings modal crash on the free tier (null new-notebook button guard)
- Accent color swatches apply app-wide; removed the text-size setting
- gitignore WAL/SHM files

</details>

<details><summary><strong>11:39AM IST</strong> &nbsp;·&nbsp; <code>8b4b2b2</code> &nbsp; Enforce paid features server-side + security hardening</summary>

**Paywall (client-side hiding is bypassable — the real gate lives on the server):**
- Gated /rewrite and /cleanup with require_paid_tier (were only hidden in the UI, so any free user could POST to them directly)
- Enforce pages-per-upload by tier in /transcribe (free 1 / student 5 / pro unlimited); daily token limit was already enforced
- require_paid_tier now takes a per-feature message
- Frontend surfaces page_limit / upgrade_required with a friendly message + opens the upgrade modal

**Hardening (from an OWASP/Flask audit):**
- Debug mode now off when FLASK_ENV=production (was hardcoded True — the Werkzeug debugger allows RCE)
- Added baseline security headers: X-Content-Type-Options: nosniff, X-Frame-Options: SAMEORIGIN, Referrer-Policy
- Audit confirmed SQL injection, XSS, CSRF, IDOR, file upload, brute-force, and session cookies were already clean

</details>

<details><summary><strong>6:54PM IST</strong> &nbsp;·&nbsp; <code>ece5280</code> &nbsp; Security round 2, legal pages, and deploy config</summary>

**Security (second "vibecoded app" audit pass):**
- Rate-limit /redeem (5/min, 20/hr) — was an unthrottled brute-force path to is_admin/dev (privilege escalation)
- Stop leaking raw exception strings to clients (cleanup + gdocs export now log server-side, return a generic message)
- Confirmed clean: secrets never in client, no mass-assignment on signup (tier hardcoded), no missing auth, no account enumeration

**Legal / verification:**
- Public /privacy and /terms pages (required for Google OAuth verification; privacy includes the Limited Use language)

**Deploy:**
- Fixed the .ebextensions HTTPS redirect loop (only redirect when X-Forwarded-Proto != https)
- Removed a junk .ebextensions file; added DEPLOY.md

</details>

<details><summary><strong>6:55PM IST</strong> &nbsp;·&nbsp; <code>7390a71</code> &nbsp; Branding, logo, and landing/transcription UI polish</summary>

**Logo/branding:**
- Added Note-Cloud logo assets; cropped a square cloud icon for the favicon + Google consent screen
- Fixed the broken favicon across all templates (deleted svg → favicon.png)
- Logo on the login card, a small cloud mark in the app header, and a larger fixed corner logo on the landing page

**Landing:**
- Redesigned the "Connect Google Docs" modal
- Footer with Privacy/Terms links
- Removed the accent-colour picker (fought the gold branding and the perf work) and the text-size setting
- Removed the top-left background glow and the cursor-follow mouse glow

**Transcription page:**
- Cursor-follow grid glow — the grid brightens in a circle around the mouse

Note: a landing pricing table was added then removed in this window because it broke the yellow scroll transition (kept on the main app page).

</details>

<details><summary><strong>6:55PM IST</strong> &nbsp;·&nbsp; <code>75217df</code> &nbsp; Add logo/favicon PNG assets</summary>

- Force-added the logo/favicon PNGs past the *.png gitignore rule (that rule exists for test uploads, but these assets are referenced by the templates and must ship)

</details>

## 7/4 — Banglore, India

<details><summary><strong>1:06PM IST</strong> &nbsp;·&nbsp; <code>7c0a450</code> &nbsp; Crop-before-transcribe modal + landing footer polish</summary>

- New crop modal in index.html: draggable box with four corner handles over a single uploaded image; "Use full photo" skips, ✕ cancels
- Single-file uploads (drag-drop, camera, gallery) now route through `openCropper` before hitting `handleFiles`; multi-file selections bypass the cropper
- Reset `fileInput.value` after change so the same photo can be re-picked
- login.html: tighter landing footer (inline © next to links, smaller top padding), bg explode scroll window shifted to 0.5→1.0 so the yellow lands exactly at the about card
- Add `static/avatars/avatar_1.jpg`

</details>

<details><summary><strong>1:14PM IST</strong> &nbsp;·&nbsp; <code>b5ae984</code> &nbsp; Make crop modal touch-friendly on mobile</summary>

- Handle hit-area expanded to ~44px via a `::before` pseudo (visual size unchanged); larger visual handles on ≤480px viewports and smaller `max-height` so the modal fits phone screens
- `touch-action: none` on the crop box and handles so dragging doesn't scroll the page
- `pointer-events: none` on the crop image so drags always land on the box/handles instead of the image
- `setPointerCapture` on drag start (with `releasePointerCapture` + `pointercancel` cleanup) so the drag survives the finger leaving the element
- Rescale crop box on `resize` / `orientationchange` so it stays inside the image after the layout changes

</details>

<details><summary><strong>1:34PM IST</strong> &nbsp;·&nbsp; <code>10a640f</code> &nbsp; Ease landing scroll animation so fast flicks still play out</summary>

- The wave/coil/bg-explode were tied 1:1 to `scrollTop`, so flicking from top to bottom skipped straight to the final state
- Scroll now writes a `targetP`; a `requestAnimationFrame` loop lerps `currentP` toward it (~0.4s catch-up via `EASE = 0.14`) and paints from `currentP`
- Wrap-visibility gating and the initial paint still fire from `updateLine`, so the wave still hides on button clicks and shows on any real scroll
- Result: a fast flick lands at the bottom and then the yellow washes in visibly instead of snapping — tweak `EASE` lower for a longer play-out

</details>

<details><summary><strong>1:42PM IST</strong> &nbsp;·&nbsp; <code>edbf23f</code> &nbsp; Landing scroll slow-mo zone (Forza jump-cam feel) + slower ease</summary>

- Animation `EASE` lowered 0.14 → 0.09 (~0.7s catch-up), so the wave/coil fill plays out visibly longer even without slow-mo
- New slow-mo zone in `[0.42, 0.90]` of scroll progress: while inside, wheel and touch deltas are dampened to ~30% (`SLOW_FACTOR = 0.30`), then released back to native scroll on either side
- A 0.06-wide ramp on each edge smoothly lerps the dampening in and out so it doesn't feel like the page snagged — outside the ramp we return `1` and native scroll runs unchanged
- Wheel path: `passive: false` + `preventDefault()` + manual `scrollTop += deltaY * mul`; touch path: `touchstart` seeds `touchY`, `touchmove` (non-passive) advances `scrollTop` by dampened delta, `touchend` resets
- Tune knobs at the top of the block: `SLOW_IN` / `SLOW_OUT` (zone), `RAMP` (edge width), `SLOW_FACTOR` (how much slower — lower = slower)

</details>

<details><summary><strong>2:12PM IST</strong> &nbsp;·&nbsp; <code>4a587fb</code> &nbsp; Landing scroll: proper Forza-cutscene takeover (replaces dampening)</summary>

- The previous dampening approach fought native scroll physics — worked in theory, felt sticky in practice, and still let a hard flick blow past the yellow explosion
- New model: **cinematic takeover**. Track per-event scroll velocity (px/ms) with a 50/50 EMA and a `dt` cap of 80ms so a long idle doesn't zero out the reading
- Cutscene trigger: user is armed + `Math.max(v, smoothV) > FLICK_VELOCITY (0.9)` + `SLOW_IN (0.40) ≤ progress < SLOW_OUT (0.92)`
- Cutscene: set `overflow-y: hidden` on `#landing-content` to cancel iOS/Android momentum, then drive `scrollTop` from entry point → `SLOW_OUT * sMax` with `easeInOutCubic` over `CUTSCENE_MS (1500)`ms
- Input lock: `wheel` and `touchmove` are `preventDefault`'d only while `cutsceneActive` — outside the cutscene, native scroll is untouched (slow readers feel nothing)
- Re-arm: when scroll progress goes back below `SLOW_IN - 0.03`
- Deleted the old `EASE` lerp loop and the `slowMul()` dampener — the cutscene guarantees the trajectory, so paint runs directly from `scrollProgress()`
- Also patched two callers that referenced the removed `updateLine()` (the `buildFrame` recalc and the initial paint) to call `paint(scrollProgress())`
- Knobs: `SLOW_IN` / `SLOW_OUT` (zone), `CUTSCENE_MS` (length), `FLICK_VELOCITY` (how easily a scroll counts as a flick — lower = trigger more often)

</details>

<details><summary><strong>2:38PM IST</strong> &nbsp;·&nbsp; <code>715b9dd</code> &nbsp; Cutscene: hit-a-point trigger + slow pan all the way to the bottom</summary>

- Previous velocity-gated version still felt jittery and hard flicks still blew past the yellow explosion
- Trigger is now a plain scroll position, `TRIGGER = 0.32` — any downward scroll crossing it engages the cutscene (no velocity heuristic)
- Cutscene runs from `lc.scrollTop` → the very bottom (`sMax`) over `CUTSCENE_MS = 3200` with `easeOutCubic`, so the yellow explosion fully plays out
- Input lock is now broader: `wheel`, `touchmove`, and keyboard scroll keys (space, PgUp/Dn, arrows, home/end) are all `preventDefault + stopPropagation`'d while `cutsceneActive`; listeners installed on both `lc` and `window`
- Re-arm requires scrolling back above `REARM_BELOW = 0.24` so it doesn't refire immediately
- **Smoothness fix (biggest win):** `will-change: clip-path; transform: translateZ(0)` on `#bg-explode` — promotes the growing yellow circle into its own compositing layer, so the animation no longer forces the whole viewport to repaint each frame
- Knobs: `TRIGGER`, `REARM_BELOW`, `CUTSCENE_MS`, and the ease function inside `startCutscene`

</details>

<details><summary><strong>3:04PM IST</strong> &nbsp;·&nbsp; <code>451c6ec</code> &nbsp; Cutscene: catch really-fast flicks before they overshoot the trigger</summary>

- Prior version reacted from the `scroll` event, which fires *after* the browser has already scrolled. On a hard trackpad flick / hard fling, momentum could blow past the trigger and land near/at the bottom before our check ran, leaving the cutscene with no distance to play
- **Wheel preempt:** in the `wheel` handler, we now compute `scrollTop + deltaY` and if it would cross `TRIGGER * sMax`, we `preventDefault + stopPropagation` and call `startCutscene()` *before* the browser scrolls. Attached to both `lc` and `window` to catch propagation from either side
- **Touchmove preempt:** same logic during finger drag using the delta between successive touch Y-coordinates (post-release momentum still relies on the scroll handler — there's no touchmove during momentum)
- **Snap-back in `startCutscene`:** if we still land past the trigger by more than 4% (touch momentum case), we set `lc.scrollTop = triggerY` so the full 3.2s ease-out has the whole page to work with — otherwise we start from the current position for a natural continuation
- Split the prior single `swallow` handler into a proper `onWheel` that both swallows (during cutscene) and preempts (before it); kept a separate `keydown` swallower for scroll keys and a touchstart/touchend pair to track the finger anchor
- Guard `if (cutsceneActive) return;` at the top of `startCutscene` prevents double-fires from the lc/window listener pair

</details>

<details><summary><strong>3:34PM IST</strong> &nbsp;·&nbsp; <code>99c405d</code> &nbsp; Add /robots.txt and /sitemap.xml for search-engine indexing</summary>

- New `/robots.txt` allows the public landing/privacy/terms pages and disallows the authenticated routes (`/history`, `/notebooks`, `/transcription/`, `/transcriptions/`); points crawlers at the sitemap
- New `/sitemap.xml` lists the public URLs (`/`, `/login`, `/privacy`, `/terms`) using `request.url_root` so it self-hosts on localhost, staging, and prod without config
- Added `Response` to the `flask` import line
- Rebuilt `notecloud.zip` so the EB deploy artifact contains the new routes
- Both are prerequisites for Google Search Console verification (Phase B item)

</details>
