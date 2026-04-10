# Note-Cloud — Product Spec

## What it is
A web app for students to photograph handwritten notes and get back clean, editable text instantly. Built for people who can't use devices in class but want their notes digital afterward.

---

## User tiers

| Tier | Daily token limit | Price |
|------|------------------|-------|
| Free | 500 tokens (~2 pages) | $0 |
| Student | 5,000 tokens (~20 pages) | $3.99/mo or $39.90/yr |
| Pro | Unlimited | $8.99/mo or $89.90/yr |
| Dev | Unlimited | Owner-only (redeemed via secret code) |

One token = one word in the transcription output. Limits reset daily.

**Referral system:** users earn +250 bonus daily tokens for every friend they refer.

---

## Features — shipped

### Core
- Upload a photo (drag-and-drop, file picker, or mobile camera)
- Claude vision API transcribes the handwriting
- Editable text output with word count

### Auth
- Email + password signup/login (no Google/Apple yet)
- Sessions persist across page loads
- Profile photo upload
- Owner code (redeems unlimited Dev tier)

### Library sidebar
- All transcriptions saved to history, accessible from a left sidebar
- **Notebooks** — create named, colour-coded folders; drag history items into them
- Click any item (from history or a notebook) to reload it into the editor

### Sharing & export
- **Share via link** — generates a unique `/s/<token>` URL, public, no login required
- **Download as .txt** — plain UTF-8 text file
- **Download as .docx** — Word document with title and date, built server-side

### UI/UX
- Dark/light mode toggle, persisted in localStorage
- Mobile camera capture (rear camera button, hidden on desktop)
- Onboarding tutorial — 3-step interactive modal shown on first visit
- Token usage bar with upgrade prompt when limit is reached

---

## Features — not yet built

- **Google / Apple login** — needs OAuth setup on Google Cloud Console / Apple Developer
- **Stripe payments** — backend stub exists, needs Stripe keys wired in
- **Export to Google Docs** — needs Google OAuth
- **Export to Notion** — needs Notion API integration token from user

---

## Target user
Students in schools with "no device" policies who take handwritten notes and want them digitised without manually re-typing. Priced to be affordable for students.
